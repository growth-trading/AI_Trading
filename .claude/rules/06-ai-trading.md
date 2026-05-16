---
description: Module AI Trading — subscription plan, phân tích biểu đồ Gemini, tính indicator cục bộ, canvas capture — áp dụng khi làm việc với trading/
globs:
  - trading/**
  - templates/trading/**
---

## Tổng quan module

`trading/` chứa toàn bộ tính năng AI Trading và TradingView:
- Hiển thị biểu đồ nến real-time (Lightweight Charts + MT5/Binance)
- Mua gói AI Trading (xu → thời hạn phân tích Gemini)
- Phân tích biểu đồ bằng Gemini Vision + chỉ báo kỹ thuật cục bộ
- Mua gói TradingView (xu → nhúng chart TradingView premium qua iframe)

## Model `ChartAnalysisLog` (`trading/models.py`)

Lưu lịch sử mỗi lần phân tích:
- `user` (FK → CustomUser, nullable, SET_NULL) — nullable để không mất log khi xóa user
- `symbol` (CharField max 50) — ví dụ `OANDA:XAUUSD`
- `interval` (CharField max 10) — ví dụ `60` (H1)
- `signal` (BUY / SELL / HOLD)
- `confidence` (IntegerField 0–100)
- `entry`, `sl`, `tp` (Decimal 18,6, null/blank) — null khi signal = HOLD
- `reasoning` (TextField) — giải thích ngắn từ Gemini
- `created_at` (auto)

## Models TradingView (`trading/models.py`)

**`TradingViewProduct`**
- `slug` (unique), `name`, `name_en` (optional), `description`, `description_en` (optional)
- `chart_id` (TradingView chart ID từ URL), `symbol`, `interval`
- `week_cost`, `month_cost`, `year_cost` (PositiveIntegerField)
- `is_active` (BooleanField), `sort_order` (PositiveSmallIntegerField)
- Ordering: `['sort_order', 'pk']`

**`UserTVSubscription`**
- FK `user` + FK `product` (unique_together)
- `expires_at` (DateTimeField)
- Property `is_active`: `expires_at > timezone.now()`

## Gói đăng ký AI Trading

### Luồng mua gói (`trading/views.py::subscribe_ai_trading_view`, `subscribe_tradingview_view`)

Cả hai view đều dùng pattern atomic check+update:

```
POST /trading/subscribe/ (AI) hoặc /trading/tradingview/subscribe/ (TV)
Body: { "plan": "week" | "month" | "year" } (+ "product_slug" cho TV)

1. Kiểm tra is_authenticated + is_email_verified
2. Parse plan, lấy cost
3. transaction.atomic() + select_for_update():
   a. Lấy user với row lock
   b. Tính new_expiry (cộng dồn nếu còn hạn, tính từ now nếu hết hạn)
   c. filter(pk=user.pk, coins__gte=cost).update(coins=F('coins') - cost, ...)
      → WHERE coins >= cost đảm bảo atomic check+update trên cả SQLite lẫn PostgreSQL
   d. Nếu updated == 0: trả 402 (không đủ xu)
4. Trả về { success, expires_at (ISO), coins_remaining }
```

### Chi phí gói (đơn vị: xu, cấu hình trong `.env`)

| Gói | Env var | Mặc định |
|-----|---------|---------|
| Tuần (7 ngày) | `AI_PLAN_WEEK_COST` | 20 xu |
| Tháng (30 ngày) | `AI_PLAN_MONTH_COST` | 50 xu |
| Năm (365 ngày) | `AI_PLAN_YEAR_COST` | 400 xu |

## Luồng phân tích biểu đồ

### `trading/views.py::analyze_chart_view`

```
POST /trading/analyze/
Body (JSON):
  symbol        — ví dụ "OANDA:XAUUSD" (auto uppercase ở view)
  interval      — "1"|"5"|"15"|"30"|"60"|"120"|"240"|"D"|"W"
  current_price — giá đóng cửa nến cuối
  chart_image   — base64 PNG từ canvas capture (tối đa ~1.5 MB)
  candles       — mảng [{open,high,low,close,...}, ...] tối đa 500 phần tử

Validation (trả 400/429 nếu sai):
  1. is_authenticated + is_email_verified + has_ai_trading_access
  2. Rate-limit: 5 req/phút/user — dùng cache.incr() atomic (tránh race condition)
  3. symbol khớp regex ^[A-Z0-9_:.]{1,50}$
  4. interval thuộc whitelist hợp lệ
  5. chart_image > 2 MB → discard (fallback PNG)
  6. candles > 500 phần tử → 400
  7. candles thiếu key open/high/low/close → set candles = None

Processing:
  A. Chart image (bắt buộc có ảnh thật):
     - chart_image_b64 rỗng → decr rate counter + trả 400
     - Decode base64 → validate PNG magic bytes \x89PNG\r\n\x1a\n
     - Nếu fail → decr rate counter + trả 400
     - Không có PNG fallback/mock — nếu không có ảnh thì báo lỗi rõ ràng
  B. Indicators: compute_indicators_local(candles) — candles=None hoặc <60 → _mock_indicators()
  C. analyze_with_gemini(image_bytes, indicators, symbol, interval, current_price)
  D. Sanitize output: signal ∈ {BUY,SELL,HOLD}, confidence clamp 0–100
     _clamp_price(v): trả Decimal (không phải float) — giữ precision cho DB
  E. ChartAnalysisLog.objects.create(...) với Decimal values
  F. Serialize JSON: Decimal → float chỉ khi trả response (không ảnh hưởng DB)
  G. Trả về { success: true, data: { signal, confidence, entry, sl, tp, reasoning } }
```

## `trading/services.py` — không gọi API ngoài trừ Gemini

### `compute_indicators_local(candles: list) -> dict`

Tính 5 chỉ báo từ OHLCV cục bộ bằng pandas-ta. Không cần internet.

```python
# Yêu cầu: candles >= 60 phần tử, mỗi phần tử có key open/high/low/close
# Nếu < 60 → trả _mock_indicators() + log warning
df = pd.DataFrame(candles)[['open','high','low','close']].astype(float)
df.ta.rsi(length=14, append=True)          # → RSI_14
df.ta.macd(fast=12, slow=26, signal=9)     # → MACD_12_26_9, MACDs_*, MACDh_*
df.ta.ema(length=20, append=True)          # → EMA_20
df.ta.ema(length=50, append=True)          # → EMA_50
df.ta.supertrend(length=10, multiplier=3.0)# → SUPERT_10_3.0, SUPERTd_10_3.0
```

**Tên cột Supertrend**: detect động bằng regex `^SUPERT_\d` và `^SUPERTd_\d` — không hardcode tên cột vì có thể khác giữa phiên bản pandas-ta.

**Direction**: `(st_dir or 0) > 0` → `'long'`, ngược lại → `'short'`.

**Fallback**: Nếu tất cả indicator đều None sau tính toán → log warning + trả `_mock_indicators()`.

### `analyze_with_gemini(image_bytes, indicators, symbol, interval, current_price) -> dict`

- Nếu `GEMINI_API_KEY` rỗng hoặc là demo key → trả `_mock_analysis()` (không gọi API)
- Model: `gemini-2.5-flash`
- Gửi: prompt text (symbol, interval, indicator values) + ảnh PNG
- Parse JSON response; strip markdown fence `` ```json `` nếu có bằng `re.sub`
- Trả về: `{ signal, confidence, entry, sl, tp, reasoning }`

**Free tier**: Gemini 2.5 Flash = 1.500 req/ngày. 100 user × 5 req/phút max = ~250 req/ngày tối đa → không bao giờ vượt giới hạn free.

### Demo / Production mode

`_DEMO_KEYS = {'your_gemini_api_key', ''}` — nếu `GEMINI_API_KEY` nằm trong set này:
- `analyze_with_gemini` → gọi `_mock_analysis()` (trả dữ liệu giả có `[DEMO]` trong reasoning)
- `compute_indicators_local` → vẫn tính thật, chỉ Gemini bị mock

## Canvas Chart Capture (JavaScript)

**`captureChartImage()` trong `templates/trading/index.html`:**

```javascript
function captureChartImage() {
  try {
    var container = document.getElementById('lwChart');
    var canvases  = Array.from(container.querySelectorAll('canvas'));
    if (!canvases.length) return null;          // không có canvas → fallback PNG
    var tmp = document.createElement('canvas');
    tmp.width = container.clientWidth; tmp.height = 600;
    var ctx = tmp.getContext('2d');
    canvases.forEach(function(c) { ctx.drawImage(c, 0, 0); });  // composite tất cả layer
    return tmp.toDataURL('image/png').split(',')[1];             // trả base64 (không có prefix)
  } catch (e) {
    return null;   // SecurityError (CORS tainted canvas) → fallback PNG
  }
}
```

`runAnalysis()` gửi POST với `chart_image: captureChartImage()` và `candles: chartCandles` (array 150 nến đang hiển thị). Nếu `captureChartImage()` trả `null`, view dùng `_PNG_FALLBACK` thay thế.

## Rate Limiting (`analyze_chart_view`)

```python
rate_key = f'ai:analyze:rate:{request.user.pk}'
try:
    rate_count = cache.incr(rate_key)       # atomic — tránh race condition
except ValueError:
    cache.add(rate_key, 0, 60)              # key chưa tồn tại → tạo với TTL 60s
    rate_count = cache.incr(rate_key)
if rate_count > 5:
    return JsonResponse({...}, status=429)  # 5 req/phút/user
```

**Tại sao dùng `incr` thay vì `get/set`**: `cache.get` + `cache.set` có race condition khi 2 request đến đồng thời cùng đọc count = 4, cả 2 đều pass, cả 2 đều set = 5 → thực tế 6 request được phép. `incr` là atomic ở cả Redis lẫn Memcache.

## Dữ liệu nến (`trading/views.py`)

**`chart_data_view` / `tick_view`**: yêu cầu `is_authenticated` + `is_email_verified` + rate-limit (30/60 req/phút)

- **Ưu tiên**: MT5 (nếu `MetaTrader5` import thành công)
- **Fallback**: Binance public REST API (không cần API key); symbol `BINANCE:*` → đi thẳng Binance
- **MT5 thread-safety**: `_mt5_lock` (threading.Lock) đảm bảo chỉ 1 thread dùng MT5 cùng lúc; double-check sau khi acquire lock
- **Symbol resolution**: `@lru_cache(maxsize=100)` — thử suffix `('', 'm', '.', 'pro', 'c', 'n')`, cache kết quả vào memory, tránh gọi `symbol_info` lặp
- **Cache TTL**: 1m=15s, 5m=45s, 15m=90s, 30m=120s, 1h=180s, 2h=360s, 4h=600s, D=1800s, W=3600s
- Historical data (`before_ts`): cache 600s
- Candles format: `[{time, open, high, low, close}, ...]` — `time` là Unix timestamp (giây)
