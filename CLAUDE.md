# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tổng quan dự án

Ứng dụng web Django hỗ trợ giao dịch bằng AI, tích hợp nạp tiền USDT qua MetaMask, xác thực email bằng OTP, và phân tích biểu đồ bằng Gemini Vision. Người dùng chuyển USDT đến **ví Admin cố định** — backend tự động quét ví đó qua BscScan API và cộng xu vào tài khoản. Xu được dùng để mua gói AI Trading để truy cập tính năng phân tích biểu đồ.

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

# Kiểm thử
python manage.py test                    # toàn bộ
python manage.py test accounts           # một app
python manage.py test accounts.tests.TestClass  # một class

# File tĩnh (production)
python manage.py collectstatic
```

## Công nghệ sử dụng

- **Backend**: Django 4.2, Python 3.11+, `python-decouple` (`.env`)
- **Database**: SQLite (dev), `psycopg2-binary` có sẵn cho PostgreSQL
- **Frontend**: Django Templates + Bootstrap 5, Bootstrap Icons 1.11, Font Awesome 6.7.2, Web3.js (MetaMask), Lightweight Charts (biểu đồ nến)
- **Tác vụ nền**: `django-apscheduler` — scheduler trong `DepositsConfig.ready()`, không dùng Celery
- **Email**: Django SMTP (Gmail)
- **Blockchain**: BscScan API (BSC/BEP-20 USDT)
- **AI Analysis**: `google-generativeai` (Gemini 2.5 Flash Vision) — phân tích ảnh biểu đồ
- **Chỉ báo kỹ thuật**: `pandas>=2.0` + `pandas-ta>=0.3.14b` — tính RSI/MACD/EMA/Supertrend cục bộ
- **Dữ liệu thị trường**: MetaTrader5 (primary), fallback Binance public API
- **Cache**: `django-redis` + Redis (self-hosted), fallback `LocMemCache`

## Cấu trúc project

```
aitrading/       # settings.py, urls.py, wsgi.py
accounts/        # CustomUser, đăng ký, OTP email
deposits/        # DepositTransaction, WalletScanState, tasks, views
trading/         # landing, trang trading, subscribe, AI chart analysis
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
- `phone`, `address` — thông tin hồ sơ
- `ai_trading_expires_at` (DateTimeField, null) — thời điểm hết hạn gói AI
- `has_ai_trading_access` (property) — `ai_trading_expires_at > timezone.now()`

### OTP Email Flow
1. Đăng ký → `user.generate_otp()` → gửi SMTP → lưu `user.pk` vào session
2. `/accounts/verify/` → `user.is_otp_valid(code)` (`secrets.compare_digest` — constant-time) → login
3. `login_view`: sau `authenticate()`, nếu `is_email_verified=False` → redirect `verify_otp`

### URL Structure
```
/                           → landing (đã login → redirect trading)
/accounts/register|login|logout|verify|resend-otp/
/deposit/                   → deposit_view, submit_txhash_view, check_deposit_status
/trading/                   → trading_view (yêu cầu đăng nhập)
/trading/subscribe/         → subscribe_ai_trading_view (POST JSON)
/trading/analyze/           → analyze_chart_view (POST JSON)
/profile/                   → profile_view
/profile/settings/          → settings_view
<bất kỳ URL khác>           → catch-all → page_not_found → 404.html
```

### Luồng nạp tiền (`deposits/`)

**Models:**
- `DepositTransaction`: `tx_hash` (unique) — ngăn double-credit; `user` (FK nullable)
- `WalletScanState`: lưu `last_scanned_block` trong DB theo `network`

**Tự động** — `deposits/tasks.py::scan_admin_wallet()` chạy mỗi `WALLET_SCAN_INTERVAL_SECONDS` giây: BscScan API → decode memo `UID-XXXX` → cộng coins bằng `F('coins') + amount`.

**Thủ công** — `deposits/views.py::submit_txhash_view()`: validate regex tx_hash → BscScan lookup → kiểm tra memo == `request.user.memo_code` → cộng coins.

**CRITICAL:** Luôn dùng `F('coins') + amount` khi cộng/trừ coins — tránh race condition.

### Module AI Trading (`trading/`)

**Model `ChartAnalysisLog`**: lưu mỗi lần phân tích — `user`, `symbol`, `interval`, `signal` (BUY/SELL/HOLD), `confidence`, `entry`, `sl`, `tp`, `reasoning`.

**Mua gói** — `subscribe_ai_trading_view`: atomic `select_for_update()` → trừ coins → set `ai_trading_expires_at`. Gia hạn cộng dồn nếu còn hạn.

**Phân tích** — `analyze_chart_view`:
1. Check `is_authenticated` + `is_email_verified` + `has_ai_trading_access`
2. Rate-limit 5 req/phút/user (atomic `cache.incr`)
3. Validate: symbol regex, interval whitelist, candles ≤ 500, chart_image ≤ 2MB + PNG magic bytes
4. `compute_indicators_local(candles)` — tính RSI/MACD/EMA20/EMA50/Supertrend bằng pandas-ta (không API)
5. `analyze_with_gemini(image_bytes, indicators, ...)` — Gemini 2.5 Flash Vision
6. Lưu `ChartAnalysisLog`, trả JSON

**Canvas capture** (`captureChartImage()` trong template): composite tất cả `<canvas>` của Lightweight Charts → `toDataURL('image/png')` → base64 POST. Bọc trong `try/catch` tránh `SecurityError`. Nếu thất bại → view dùng `_PNG_FALLBACK` (1×1 transparent PNG).

**`trading/services.py`**: chỉ import `pandas`, `pandas_ta`, `google.generativeai` — **không** dùng `requests` (đã xóa TAAPI + Chart-IMG). Demo mode: nếu `GEMINI_API_KEY` rỗng → `_mock_analysis()` với `[DEMO]` label.

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
DJANGO_RUN_SCHEDULER=0

MT5_ACCOUNT=
MT5_PASSWORD=
MT5_SERVER=

GEMINI_API_KEY=

AI_PLAN_WEEK_COST=20
AI_PLAN_MONTH_COST=50
AI_PLAN_YEAR_COST=400

REDIS_URL=                    # vd: redis://127.0.0.1:6379/0 (để trống → dùng LocMemCache)
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
- **Không còn** Floating Controls ở góc phải (đã xóa khỏi base.html)
- Toggle nằm tại `/profile/settings/` — card Giao diện + card Ngôn ngữ

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
