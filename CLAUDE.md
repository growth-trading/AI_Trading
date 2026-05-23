# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tổng quan dự án

Ứng dụng web Django hỗ trợ giao dịch bằng AI, tích hợp nạp tiền USDT qua MetaMask, xác thực email bằng OTP, và phân tích biểu đồ bằng Gemini Vision. Người dùng chuyển USDT đến **ví Admin cố định** — backend tự động quét ví đó qua BscScan API và cộng xu vào tài khoản. Xu được dùng để mua gói AI Trading (phân tích biểu đồ Gemini) hoặc gói TradingView (nhúng chart TradingView premium).

## Các lệnh thường dùng

```bash
# Cài đặt
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Database
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Chạy server phát triển
python manage.py runserver

# Kiểm thử (hiện chưa có test files)
python manage.py test
python manage.py test accounts
python manage.py test accounts.tests.TestClass

# MT5 data collector (production — pre-fetch candles vào Redis cache)
python manage.py run_mt5_collector
python manage.py run_mt5_collector --symbols OANDA:XAUUSD,OANDA:EURUSD --intervals 60,240

# File tĩnh (production)
python manage.py collectstatic
```

## Công nghệ sử dụng

- **Backend**: Django 4.2, Python 3.11+, `python-decouple` (`.env`)
- **Database**: SQLite (dev), `psycopg2-binary` có sẵn cho PostgreSQL
- **Frontend**: Django Templates + Bootstrap 5, Bootstrap Icons 1.11, Font Awesome 6.7.2, Web3.js (MetaMask), Lightweight Charts (biểu đồ nến)
- **Tác vụ nền**: không dùng Celery hay django-apscheduler (đã xóa); tác vụ định kỳ chạy thủ công hoặc qua OS scheduler
- **Email**: Django SMTP (Gmail)
- **Blockchain**: BSC public RPC (`deposits/tasks.py` dùng `requests`); `trading/views.py` dùng stdlib `urllib.request`
- **AI Analysis**: `google-generativeai` (Gemini 2.5 Flash Vision) — phân tích ảnh biểu đồ
- **Chỉ báo kỹ thuật**: `pandas>=2.0` + `ta==0.11.0` (package `ta`, import `import ta as ta_lib`) — tính RSI/MACD/EMA/Supertrend cục bộ
- **Dữ liệu thị trường**: MetaTrader5 (primary), fallback Binance public API; symbol có prefix `BINANCE:` đi thẳng vào Binance path
- **Cache**: `django-redis` + Redis (**bắt buộc** — thiếu `REDIS_URL` thì raise `ImproperlyConfigured`); Redis key prefix = `'ait'`
- **Static files**: `whitenoise` (`WhiteNoiseMiddleware` + `CompressedManifestStaticFilesStorage`) — serve static trực tiếp từ Django không cần Nginx

## Cấu trúc project

```
aitrading/       # settings.py, urls.py, wsgi.py
accounts/        # CustomUser, đăng ký, OTP email, EmailVerifiedMiddleware
deposits/        # DepositTransaction, WalletScanState, tasks, views
trading/         # landing, trang trading, subscribe, AI chart analysis, MT5/Binance data, TradingView products
profiles/        # hồ sơ, avatar, cài đặt
templates/       # HTML phân theo app
static/          # CSS, JS, hình ảnh
```

## Kiến trúc & Luồng xử lý chính

### Model người dùng (`accounts/models.py::CustomUser`)
Kế thừa `AbstractUser`, thêm:
- `coins` (DecimalField 18,2) — số dư nội bộ
- `is_email_verified` (BooleanField) — gate cho nạp tiền và AI
- `otp_code`, `otp_created_at` — OTP trực tiếp trên user, hết hạn 10 phút
- `memo_code` (property) — `f"UID-{self.pk:04d}"`
- `phone`, `address`, `avatar` — thông tin hồ sơ; avatar upload tới `avatars/`, validate qua PIL (max 5MB, JPEG/PNG/GIF/WebP)
- `ai_trading_expires_at` (DateTimeField, null) — thời điểm hết hạn gói AI
- `has_ai_trading_access` (property) — `ai_trading_expires_at > timezone.now()`

### Email Verification Middleware (`accounts/middleware.py::EmailVerifiedMiddleware`)
Chặn **mọi URL** (trừ prefix `/accounts/`, `/admin/`, `/static/`, `/media/` và exact path `/`, `/favicon.ico`) nếu user đã login nhưng chưa verify email:
- **POST hoặc AJAX** (detect qua `Accept: application/json` hoặc `X-Requested-With: XMLHttpRequest`) → trả `JsonResponse({'error': '...'}, status=403)` để tránh mất dữ liệu form
- **GET thông thường** → lưu `pending_verify_user_id` vào session + `messages.warning` + redirect `verify_otp`

Gate này bổ sung cho các check cụ thể trong từng view.

### OTP Email Flow
1. Đăng ký → `user.generate_otp()` → gửi SMTP → lưu `user.pk` vào session
2. `/accounts/verify/` → rate-limit 5 lần thử / 15 phút / user (atomic `cache.incr` key `otp:verify:{pk}`) → `user.is_otp_valid(code)` (`secrets.compare_digest` — constant-time) → login
3. `login_view`: sau `authenticate()`, nếu `is_email_verified=False` → redirect `verify_otp`
4. `resend_otp_view`: rate-limit 1 req / 60s / user (atomic `cache.add` key `otp:resend:{user_id}` — fails if exists) → chặn spam SMTP

### URL Structure
```
/                               → landing (đã login → redirect trading)
/accounts/register|login|logout|verify|resend-otp/
/deposit/                       → deposit_view, submit_txhash_view, check_deposit_status/<id>/
/trading/                       → trading_view (yêu cầu đăng nhập)
/trading/subscribe/             → subscribe_ai_trading_view (POST JSON)
/trading/analyze/               → analyze_chart_view (POST JSON)
/trading/chart-data/            → chart_data_view (GET, ?symbol=&interval=&since=&before=)
/trading/tick/                  → tick_view (GET, ?symbol=&interval=)
/trading/tradingview/           → tradingview_view (yêu cầu đăng nhập + email verified)
/trading/tradingview/subscribe/ → subscribe_tradingview_view (POST JSON)
/profile/                       → profile_view
/profile/settings/              → settings_view
<bất kỳ URL khác>               → catch-all → page_not_found → 404.html
```

**Điều hướng sau đăng nhập**: custom `login_view` redirect thẳng tới `'trading'` (không qua `LOGIN_REDIRECT_URL`). `LOGIN_REDIRECT_URL = '/trading/'` vẫn set trong settings làm fallback cho Django auth.

### Luồng nạp tiền (`deposits/`)

**Models:**
- `DepositTransaction`: `tx_hash` (unique, lowercase normalized) — ngăn double-credit; `user` (FK nullable, SET_NULL)
- `WalletScanState`: lưu `last_scanned_block` trong DB theo `network`

**Tự động** — `deposits/tasks.py::scan_admin_wallet()` chạy mỗi `WALLET_SCAN_INTERVAL_SECONDS` giây:
- BscScan API → batch-fetch existing hashes (`filter(tx_hash__in=all_hashes)`) để tránh N+1 query
- Decode memo `UID-XXXX` (regex `^(UID-\d{1,10})` — giới hạn 10 chữ số tránh OverflowError)
- `F('coins') + amount` — atomic. Tx không decode được memo → `STATUS_PENDING`, chờ admin thủ công
- `max_block` chỉ advance **trong** try/except IntegrityError — tx lỗi khác không advance, sẽ retry ở scan sau

**Thủ công** — `deposits/views.py::submit_txhash_view()`:
- Rate-limit 5 req/phút/user (atomic `cache.incr`)
- Validate regex `^0x[0-9a-f]{64}$` (sau khi lowercase)
- Cache kết quả `verify_txhash` 60s (30s nếu None) — tránh gọi BscScan lặp
- 2-step BscScan lookup: proxy lấy block number → tokentx trong block đó
- Kiểm tra memo == `request.user.memo_code` → reject nếu không khớp (kể cả memo rỗng)

**CRITICAL:** Luôn dùng `F('coins') + amount` / `F('coins') - cost` khi cộng/trừ coins — tránh race condition.

**Production security** (khi `DEBUG=False`): `settings.py` tự bật `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_PROXY_SSL_HEADER`. Yêu cầu HTTPS.

### Module AI Trading (`trading/`)

**Model `ChartAnalysisLog`**: lưu mỗi lần phân tích — `user`, `symbol`, `interval`, `signal` (BUY/SELL/HOLD), `confidence`, `entry`, `sl`, `tp`, `reasoning`.

**Mua gói** — `subscribe_ai_trading_view` / `subscribe_tradingview_view`: `select_for_update()` lấy row lock → tính `new_expiry` → `filter(pk=user.pk, coins__gte=cost).update(coins=F('coins')-cost, ...)` — WHERE clause đảm bảo atomic check+update trên cả SQLite lẫn PostgreSQL. Nếu `updated == 0` → 402. Gia hạn cộng dồn nếu còn hạn.

**Phân tích** — `analyze_chart_view` (`@require_POST`):
1. Check `is_authenticated` + `is_email_verified` + `has_ai_trading_access`
2. Validate image (trước rate-limit — tránh tiêu slot cho lỗi client): PNG base64 ≤ 2MB, magic bytes `\x89PNG`
3. PIL compress: resize về 640px wide → JPEG 80% → giảm token Gemini; nếu PIL fail thì giữ PNG gốc
4. Rate-limit: `cache.add(key, 1, 60)` → nếu exists thì `cache.incr(key)`; counter được **hoàn trả** (`cache.decr`) nếu xử lý thất bại do lỗi hệ thống
5. `compute_indicators_local(candles)` — tính RSI/MACD/EMA20/EMA50/Supertrend bằng pandas-ta; thiếu nến / lỗi → `{}`, Gemini nhận "(Không có dữ liệu indicator)"
6. `analyze_with_gemini(image_bytes, indicators, ..., lang='vi'|'en', image_mime)` — Gemini 2.5 Flash; `lang` param điều khiển ngôn ngữ reasoning; `ResourceExhausted`/quota → 429; non-JSON → 500 + hoàn rate slot
7. Lưu `ChartAnalysisLog` với `Decimal`; serialize JSON: `Decimal → float` chỉ khi trả response

**Dữ liệu nến** — `chart_data_view` / `tick_view` (yêu cầu `is_email_verified`):
- Symbol prefix `BINANCE:` → đi thẳng vào Binance API path; các symbol khác đi vào MT5 path
- MT5 với `_mt5_lock` đảm bảo thread-safe; `_mt5_resolve_symbol` dùng plain dict cache (clear khi > 200 entries) — thử các suffix `('', 'm', '.', 'pro', 'c', 'n')`
- Cache theo TTL của từng interval; historical data (`before_ts`) cache 600s
- `chart_data_view` rate-limit 30 req/phút/user; `tick_view` rate-limit 60 req/phút/user

**MT5 Collector** — `trading/management/commands/run_mt5_collector.py`: process độc lập kết nối MT5 một lần, liên tục làm mới cache. Dùng trong production thay vì để Django worker gọi MT5 trực tiếp.

**`trading/services.py`**: chỉ import `pandas`, `pandas_ta`, `google.generativeai` — **không** dùng `requests`. Không có demo/mock mode — nếu `GEMINI_API_KEY` thiếu hoặc sai, API call sẽ thất bại với lỗi xác thực.

### Module TradingView (`trading/`)

Bán quyền truy cập vào các chart TradingView premium được nhúng qua iframe.

**Models** (`trading/models.py`):
- `TradingViewProduct` — sản phẩm chart: `slug` (unique), `name`, `name_en` (optional), `description`, `description_en` (optional), `chart_id` (TradingView chart ID từ URL), `symbol`, `interval`, `week_cost`/`month_cost`/`year_cost`, `is_active`, `sort_order`
- `UserTVSubscription` — đăng ký của user: FK `user` + FK `product` (unique_together), `expires_at`; property `is_active`

**Quản lý sản phẩm**: qua Django Admin (`trading/admin.py`). `TradingViewProductAdmin` hỗ trợ `list_editable` để chỉnh giá/trạng thái nhanh.

**Mua gói** — `subscribe_tradingview_view`: nhận `{plan, product_slug}` → lấy `product` theo slug → `select_for_update()` → trừ coins → upsert `UserTVSubscription.expires_at`. Gia hạn cộng dồn nếu còn hạn.

**Hiển thị** — `tradingview_view`: yêu cầu `is_authenticated` + `is_email_verified`. Query `TradingViewProduct.objects.filter(is_active=True)` + truy vấn tất cả `UserTVSubscription` còn hạn của user → render list với flag `has_access` per product.

## Biến môi trường (`.env`)

```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=*

EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

ADMIN_WALLET_ADDRESS=0x...
USDT_CONTRACT_BSC=0x55d398326f99059fF775485246999027B3197955
BSCSCAN_API_KEY=
USDT_TO_COINS_RATE=1
WALLET_SCAN_INTERVAL_SECONDS=60
DJANGO_RUN_SCHEDULER=0          # set 1 in production

MT5_ACCOUNT=
MT5_PASSWORD=
MT5_SERVER=

GEMINI_API_KEY=

AI_PLAN_WEEK_COST=20
AI_PLAN_MONTH_COST=50
AI_PLAN_YEAR_COST=400

TV_PLAN_WEEK_COST=10
TV_PLAN_MONTH_COST=30
TV_PLAN_YEAR_COST=200

REDIS_URL=redis://127.0.0.1:6379/0  # BẮT BUỘC — để trống → ImproperlyConfigured khi khởi động
```

## Theme & i18n System

### Dark / Light Theme
- CSS custom properties trên `:root`; override bằng `[data-theme="light"]` trên `<html>`
- **Anti-flash**: inline script trong `<head>` đọc `localStorage('ait-theme')` và set `data-theme` trước CSS render
- `applyTheme(theme)` trong `static/js/main.js` — cập nhật `data-theme` và `localStorage`

### Đa ngôn ngữ VI / EN (client-side)
- Không dùng Django i18n. Text đánh dấu bằng `data-i18n="key"` trên HTML
- `const i18n = { vi: {...}, en: {...} }` trong `static/js/main.js` — ~120+ keys theo prefix:
  - `nav.*`, `footer.*` — base.html
  - `hero.*`, `stat.*`, `feat*`, `how.*`, `cta.*` — landing page
  - `auth.*` — auth forms; `dep.*` — nạp tiền; `prof.*` — hồ sơ
  - `trad.*` — AI Trading; `settings.*` — cài đặt; `err404.*` — 404
  - `com.*` — dùng chung
- `applyLang(lang)` — set `textContent` cho `[data-i18n]`, `placeholder` cho `[data-i18n-placeholder]`
- **Button có icon**: đặt `data-i18n` trên `<span>` bên trong, không trực tiếp lên `<button>`
- Khi thêm text mới: thêm key vào cả `i18n.vi` và `i18n.en`

### Toggle Theme/Language
- Toggle nằm tại `/profile/settings/` — card Giao diện + card Ngôn ngữ (không còn Floating Controls)

## Thiết kế & UI/UX

Dark-theme SaaS hiện đại.

### Bảng màu
```
Nền chính:     #0D0D0D / #0F1117      Accent chính: #3B82F6
Nền card:      #1A1A2E / #16213E      Accent phụ:   #6366F1
Text chính:    #F1F5F9                 Border:       #1E293B
Text phụ:      #94A3B8                Thành công:   #10B981
                                       Cảnh báo:     #F59E0B
                                       Lỗi:          #EF4444
```

### Scroll fade-in
Class `animate-on-scroll` + `IntersectionObserver`. CSS dùng `@keyframes scrollFadeUp` (không dùng `transition`) để animation restart được. Exception: `.error-page .animate-on-scroll { opacity: 1; }`.

### Responsive
Mobile-first, breakpoints: `sm:640px md:768px lg:1024px xl:1280px`. Navbar mobile: hamburger + slide-in drawer.
