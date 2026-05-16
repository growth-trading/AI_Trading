---
description: Kiến trúc tổng thể, URL structure, model CustomUser, OTP flow, quyền truy cập và lưu ý DOM order cho base.html
alwaysApply: true
---

## Cấu trúc project

```
aitrading/       # settings.py, urls.py, wsgi.py
accounts/        # CustomUser, đăng ký, OTP email
deposits/        # DepositTransaction, WalletScanState, tasks, views
trading/         # landing page, trang trading chính, AI chart analysis
profiles/        # hồ sơ, avatar, cài đặt (settings)
templates/       # HTML phân theo app (landing/, accounts/, deposits/, profiles/, trading/, emails/)
static/          # CSS, JS, web3.js, lightweight-charts, hình ảnh
```

## URL Structure

```
/                               → trading.landing (nếu đã login → redirect trading)
/accounts/register|login|logout|verify|resend-otp/
/deposit/                       → deposits.deposit_view, submit_txhash_view, check_deposit_status
/trading/                       → trading.trading_view (yêu cầu đăng nhập)
/trading/subscribe/             → trading.subscribe_ai_trading_view (POST, JSON)
/trading/analyze/               → trading.analyze_chart_view (POST, JSON)
/trading/chart-data/            → trading.chart_data_view (GET, ?symbol=&interval=&since=&before=)
/trading/tick/                  → trading.tick_view (GET, ?symbol=&interval=)
/trading/tradingview/           → trading.tradingview_view (yêu cầu đăng nhập + email verified)
/trading/tradingview/subscribe/ → trading.subscribe_tradingview_view (POST, JSON)
/profile/                       → profiles.profile_view
/profile/settings/              → profiles.settings_view
<bất kỳ URL nào khác>           → catch-all re_path → page_not_found → templates/404.html
```

**Catch-all 404** (`aitrading/urls.py`): `re_path(r'^.*$', lambda r, **kw: page_not_found(r, None))` đặt cuối `urlpatterns`. Đảm bảo mọi URL không khớp đều hiện trang 404 tùy chỉnh, kể cả khi `DEBUG=True`. Media files được prepend trước catch-all khi `DEBUG=True`.

## Trang 404 (`templates/404.html`)

- Kế thừa `base.html` (có navbar, theme, i18n)
- Hiển thị `{{ request_path }}` — Django truyền qua context của `page_not_found`
- CSS `.error-page .animate-on-scroll` override `opacity: 0` → `opacity: 1` (nội dung hiện ngay, không cần scroll)
- Tất cả text dùng `data-i18n="err404.*"`, nút tái dùng `nav.*`

## Model CustomUser (`accounts/models.py`)

Kế thừa `AbstractUser`, thêm:
- `coins` (DecimalField 18,2) — số dư nội bộ
- `is_email_verified` (BooleanField) — gate cho nạp tiền và tính năng AI
- `otp_code`, `otp_created_at` — OTP lưu trực tiếp trên user, hết hạn sau 10 phút
- `memo_code` (property) — trả về `f"UID-{self.pk:04d}"`
- `phone` (CharField max 20, blank=True) — số điện thoại
- `address` (CharField max 255, blank=True) — địa chỉ
- `ai_trading_expires_at` (DateTimeField, null/blank) — thời điểm hết hạn gói AI Trading
- `has_ai_trading_access` (property) — trả `True` nếu `ai_trading_expires_at > timezone.now()`

## OTP Email Flow

1. Đăng ký → `user.generate_otp()` → gửi SMTP (`_send_otp_email` trả `True`/`False`) → lưu `user.pk` vào session `pending_verify_user_id`
2. `/accounts/verify/` → **rate-limit 5 lần thử / 15 phút** (atomic `cache.incr` key `otp:verify:{pk}`) → `user.is_otp_valid(code)` (`secrets.compare_digest()` — constant-time) → set `is_email_verified=True`, clear OTP → login
3. Đăng nhập (`login_view`): sau `authenticate()`, nếu `is_email_verified=False` → redirect `verify_otp`
4. `resend_otp_view`: **rate-limit 1 req / 60s** (atomic `cache.add` key `otp:resend:{user_id}`) — fails nếu key tồn tại → chặn spam SMTP
5. Trang verify OTP có **countdown 10 phút** — disable nút submit khi hết giờ

## Email Verification Middleware (`accounts/middleware.py`)

Chặn mọi URL (trừ `/accounts/`, `/admin/`, `/static/`, `/media/`, `/`, `/favicon.ico`) khi user login nhưng chưa verify email:
- **POST / AJAX** (`Accept: application/json` hoặc `X-Requested-With: XMLHttpRequest`) → `JsonResponse({'error': ...}, status=403)` — tránh mất dữ liệu form
- **GET** → lưu `pending_verify_user_id` vào session + redirect `verify_otp`

## Điều hướng sau đăng nhập

- `LOGIN_REDIRECT_URL = '/trading/'` trong `settings.py`
- `login_view`: redirect `next` param sau login thành công — dùng `url_has_allowed_host_and_scheme()` để chặn open redirect; fallback về `trading`
- `login()` phải truyền `backend='django.contrib.auth.backends.ModelBackend'` khi gọi trực tiếp (không qua `authenticate()`)
- `landing`: nếu user đã đăng nhập → redirect `trading`

## Quyền truy cập

- `landing`, `trading_view` — `@require_GET`
- `subscribe_*`, `analyze_chart_view` — `@require_POST`
- `trading_view` — redirect `login` nếu chưa đăng nhập
- `deposit_view` — kiểm tra `is_email_verified`
- `chart_data_view`, `tick_view` — yêu cầu `is_authenticated` + `is_email_verified`
- `tradingview_view` — yêu cầu `is_authenticated` + `is_email_verified`
- `subscribe_ai_trading_view` — yêu cầu `is_authenticated` + `is_email_verified` + đủ `coins`
- `analyze_chart_view` — yêu cầu `is_authenticated` + `is_email_verified` + `has_ai_trading_access`

**CRITICAL — cộng/trừ coins:** dùng `filter(pk=user.pk, coins__gte=cost).update(coins=F('coins')-cost)` — WHERE clause kiểm tra đủ tiền atomically. `updated == 0` → trả 402. Không dùng `user.coins - cost` (race condition).

## Navbar (base.html)

- Chưa đăng nhập: chỉ hiện "Đăng nhập" + "Bắt đầu miễn phí", không có nav links
- Đã đăng nhập: hiện "AI Trading" nav link; user dropdown có Hồ sơ + Đăng xuất
- Brand link: đã login → `{% url 'trading' %}`, chưa login → `{% url 'landing' %}`
- Floating Controls (nút theme/lang ở góc phải) đã bị **xóa** khỏi base.html
- Theme/Language toggle chuyển vào trang `/profile/settings/`

## Trang Settings (`profiles/settings.html`)

- Sidebar: Nạp tiền, Hồ sơ, Cài đặt (active)
- Card Giao diện: nút Dark / Light gọi `applyTheme()` (global, từ main.js)
- Card Ngôn ngữ: nút Tiếng Việt / English gọi `applyLang()` (global, từ main.js)
- JS dùng `addEventListener` — không override global functions bằng inline onclick
- `syncSettingsUI()`: đọc `localStorage` để highlight option đang active
