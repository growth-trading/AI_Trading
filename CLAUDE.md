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
- **Tác vụ nền**: `django-apscheduler` — scheduler trong `DepositsConfig.ready()`, không dùng Celery
- **Email**: Django SMTP (Gmail)
- **Blockchain**: BscScan API (BSC/BEP-20 USDT); `deposits/tasks.py` dùng `requests`, còn `trading/views.py` chỉ dùng stdlib `urllib.request`
- **AI Analysis**: `google-generativeai` (Gemini 2.5 Flash Vision) — phân tích ảnh biểu đồ
- **Chỉ báo kỹ thuật**: `pandas>=2.0` + `pandas-ta>=0.3.14b` — tính RSI/MACD/EMA/Supertrend cục bộ
- **Dữ liệu thị trường**: MetaTrader5 (primary), fallback Binance public API; symbol có prefix `BINANCE:` đi thẳng vào Binance path
- **Cache**: `django-redis` + Redis (self-hosted), fallback `LocMemCache`; Redis key prefix = `'ait'`

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
Chặn **mọi URL** (trừ prefix `/accounts/`, `/admin/`, `/static/`, `/media/` và exact path `/`, `/favicon.ico`) nếu user đã login nhưng chưa verify email → redirect `verify_otp`. Gate này bổ sung cho các check cụ thể trong từng view.

### OTP Email Flow
1. Đăng ký → `user.generate_otp()` → gửi SMTP → lưu `user.pk` vào session
2. `/accounts/verify/` → `user.is_otp_valid(code)` (`secrets.compare_digest` — constant-time) → login
3. `login_view`: sau `authenticate()`, nếu `is_email_verified=False` → redirect `verify_otp`

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

**Tự động** — `deposits/tasks.py::scan_admin_wallet()` chạy mỗi `WALLET_SCAN_INTERVAL_SECONDS` giây: BscScan API → decode memo `UID-XXXX` → cộng coins bằng `F('coins') + amount`. Tx không decode được memo → `STATUS_PENDING`, chờ admin xử lý thủ công.

**Thủ công** — `deposits/views.py::submit_txhash_view()`:
- Rate-limit 5 req/phút/user (atomic `cache.incr`)
- Validate regex `^0x[0-9a-f]{64}$` (sau khi lowercase)
- Cache kết quả `verify_txhash` 60s (30s nếu None) — tránh gọi BscScan lặp
- 2-step BscScan lookup: proxy lấy block number → tokentx trong block đó
- Kiểm tra memo == `request.user.memo_code` → reject nếu không khớp (kể cả memo rỗng)

**CRITICAL:** Luôn dùng `F('coins') + amount` / `F('coins') - cost` khi cộng/trừ coins — tránh race condition.

### Module AI Trading (`trading/`)

**Model `ChartAnalysisLog`**: lưu mỗi lần phân tích — `user`, `symbol`, `interval`, `signal` (BUY/SELL/HOLD), `confidence`, `entry`, `sl`, `tp`, `reasoning`.

**Mua gói** — `subscribe_ai_trading_view`: atomic `select_for_update()` → trừ coins → set `ai_trading_expires_at`. Gia hạn cộng dồn nếu còn hạn.

**Phân tích** — `analyze_chart_view`:
1. Check `is_authenticated` + `is_email_verified` + `has_ai_trading_access`
2. Rate-limit 5 req/phút/user (atomic `cache.incr`); rate counter được **hoàn trả** (`cache.decr`) nếu xử lý thất bại do lỗi hệ thống
3. Validate: symbol regex, interval whitelist, candles ≤ 500, chart_image ≤ 2MB + PNG magic bytes
4. `compute_indicators_local(candles)` — tính RSI/MACD/EMA20/EMA50/Supertrend bằng pandas-ta (không API)
5. `analyze_with_gemini(image_bytes, indicators, ...)` — Gemini 2.5 Flash Vision
6. Lưu `ChartAnalysisLog`, trả JSON

**Dữ liệu nến** — `chart_data_view` / `tick_view`:
- Symbol prefix `BINANCE:` → đi thẳng vào Binance API path; các symbol khác đi vào MT5 path
- MT5 với `_mt5_lock` đảm bảo thread-safe; symbol resolution thử các suffix `('', 'm', '.', 'pro', 'c', 'n')` và cache kết quả
- Cache theo TTL của từng interval; historical data (`before_ts`) cache 600s
- `chart_data_view` rate-limit 30 req/phút/user; `tick_view` rate-limit 60 req/phút/user

**MT5 Collector** — `trading/management/commands/run_mt5_collector.py`: process độc lập kết nối MT5 một lần, liên tục làm mới cache. Dùng trong production thay vì để Django worker gọi MT5 trực tiếp.

**`trading/services.py`**: chỉ import `pandas`, `pandas_ta`, `google.generativeai` — **không** dùng `requests`. Demo mode: nếu `GEMINI_API_KEY` rỗng hoặc là `'your_gemini_api_key'` → `_mock_analysis()` với `[DEMO]` label.

### Module TradingView (`trading/`)

Bán quyền truy cập vào các chart TradingView premium được nhúng qua iframe.

**Models** (`trading/models.py`):
- `TradingViewProduct` — sản phẩm chart: `slug` (unique), `name`, `chart_id` (TradingView chart ID từ URL), `symbol`, `interval`, `week_cost`/`month_cost`/`year_cost`, `is_active`, `sort_order`
- `UserTVSubscription` — đăng ký của user: FK `user` + FK `product` (unique_together), `expires_at`

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

REDIS_URL=                       # vd: redis://127.0.0.1:6379/0 (để trống → dùng LocMemCache)
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
