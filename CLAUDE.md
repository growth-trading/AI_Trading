# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tổng quan dự án

Ứng dụng web Django hỗ trợ giao dịch bằng AI, tích hợp nạp tiền USDT qua MetaMask, xác thực email bằng OTP, và quản lý bot giao dịch AI. Người dùng chuyển USDT đến **ví Admin cố định** — backend tự động quét ví đó qua BscScan API và cộng xu vào tài khoản, hoặc người dùng có thể tự nhập TxHash.

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
- **Frontend**: Django Templates + Bootstrap 5, Bootstrap Icons 1.11, Font Awesome 6.7.2, Web3.js (MetaMask)
- **Tác vụ nền**: `django-apscheduler` — scheduler khởi động trong `DepositsConfig.ready()`, không dùng Celery
- **Email**: Django SMTP (Gmail)
- **Blockchain**: BscScan API (BSC/BEP-20 USDT)

## Cấu trúc project

```
aitrading/       # settings.py, urls.py, wsgi.py
accounts/        # CustomUser, đăng ký, OTP email
deposits/        # DepositTransaction, WalletScanState, tasks, views
trading/         # landing page, trang trading
profiles/        # hồ sơ, avatar, cài đặt (settings)
templates/       # HTML phân theo app (landing/, accounts/, deposits/, profiles/, emails/)
static/          # CSS, JS, web3.js, hình ảnh
```

## Kiến trúc & Luồng xử lý chính

### Model người dùng (`accounts/models.py::CustomUser`)
Kế thừa `AbstractUser`, thêm:
- `coins` (DecimalField 18,2) — số dư nội bộ
- `is_email_verified` (BooleanField) — gate cho nạp tiền và tính năng AI
- `otp_code`, `otp_created_at` — OTP lưu trực tiếp trên user, hết hạn sau 10 phút
- `memo_code` (property) — trả về `f"UID-{self.pk:04d}"`
- `phone` (CharField max 20, blank=True), `address` (CharField max 255, blank=True)

### OTP Email Flow
1. Đăng ký → `user.generate_otp()` → gửi SMTP (`_send_otp_email` trả `True`/`False`, lỗi hiện ra user) → lưu `user.pk` vào session `pending_verify_user_id`
2. `/accounts/verify/` → `user.is_otp_valid(code)` (dùng `secrets.compare_digest()` — tránh timing attack) → set `is_email_verified=True`, clear `otp_code`/`otp_created_at` → login
3. `login_view`: sau `authenticate()` thành công, kiểm tra `is_email_verified` — nếu False → redirect `verify_otp`
4. `login()` gọi trực tiếp (không qua `authenticate()`) phải truyền `backend='django.contrib.auth.backends.ModelBackend'`

### Luồng nạp tiền (`deposits/`)

**Models:**
- `DepositTransaction`: `user` (FK nullable), `tx_hash` (unique), `amount_usdt`, `coins_credited`, `status` (PENDING/COMPLETED/FAILED), `memo`, `network`, `confirmed_at`
- `WalletScanState`: lưu `last_scanned_block` theo `network` trong DB (không phải `.env`)

**Hai cách nạp tiền:**

1. **Tự động (background scan)** — `deposits/tasks.py::scan_admin_wallet()` chạy mỗi `WALLET_SCAN_INTERVAL_SECONDS` giây:
   - Gọi BscScan API `tokentx` từ `last_scanned_block + 1`
   - Decode memo từ `input` hex (`UID-XXXX`) → map sang user qua `CustomUser.objects.get(pk=uid)`
   - Cộng coins: `F('coins') + coins_credited` (atomic DB expression, tránh race condition)
   - Cập nhật `WalletScanState.last_scanned_block`

2. **Thủ công (submit TxHash)** — `deposits/views.py::submit_txhash_view()`:
   - Kiểm tra `is_email_verified` trước (ngăn bypass qua direct POST)
   - Validate TxHash bằng regex `^0x[0-9a-fA-F]{64}$`
   - `verify_txhash()` tra BscScan → trả `{tx_hash, amount_usdt, memo, ...}`
   - **Kiểm tra memo**: nếu memo != `request.user.memo_code` → từ chối (ngăn TxHash theft)
   - Cộng coins bằng `F('coins') + coins_credited`

**CRITICAL — cộng coins:** luôn dùng `F('coins') + amount`, không dùng `user.coins + amount` (race condition).

**Scheduler:** `DepositsConfig.ready()` chỉ chạy khi `RUN_MAIN=true` (dev `runserver`) hoặc `DJANGO_RUN_SCHEDULER=1` (production). Không chạy khi `migrate`, `test`, v.v.

**Tỷ lệ quy đổi:** `USDT_TO_COINS_RATE` (int, mặc định 1) — `coins_credited = amount_usdt * USDT_TO_COINS_RATE`

### URL Structure
```
/                           → trading.landing (đã login → redirect trading)
/accounts/register|login|logout|verify|resend-otp/
/deposit/                   → deposits.deposit_view, submit_txhash_view, check_deposit_status
/trading/                   → trading.trading_view (yêu cầu đăng nhập)
/profile/                   → profiles.profile_view
/profile/settings/          → profiles.settings_view
<bất kỳ URL nào khác>       → catch-all → page_not_found → templates/404.html
```

**Catch-all 404**: `re_path(r'^.*$', lambda r, **kw: page_not_found(r, None))` đặt cuối `urlpatterns` trong `aitrading/urls.py`. Hoạt động kể cả khi `DEBUG=True`. Media files prepend trước khi `DEBUG=True` để không bị chặn bởi catch-all.

### Điều hướng sau đăng nhập
- `LOGIN_REDIRECT_URL = '/profile/'` trong `settings.py`
- Sau login thành công: redirect `next` param — validate bằng `url_has_allowed_host_and_scheme()` (chặn open redirect); fallback `profile`
- Dashboard đã bị xóa — mọi redirect trước đây về `dashboard` nay về `profile`

### Quyền truy cập
- `trading_view` — redirect về `login` nếu chưa đăng nhập
- `deposit_view` kiểm tra `request.user.is_email_verified` trước khi hiển thị
- `login_view` chặn user chưa verify email — redirect `verify_otp`
- Các view nội bộ dùng `@login_required`

## Biến môi trường (`.env`)

```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=*                         # production: yourdomain.com,www.yourdomain.com
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
ADMIN_WALLET_ADDRESS=0x...
USDT_CONTRACT_BSC=0x55d398326f99059fF775485246999027B3197955
BSCSCAN_API_KEY=
USDT_TO_COINS_RATE=1
WALLET_SCAN_INTERVAL_SECONDS=60
DJANGO_RUN_SCHEDULER=0                  # set 1 in production to start wallet scanner
```

## Theme & i18n System

### Dark / Light Theme
- CSS custom properties trên `:root`; override bằng `[data-theme="light"]` trên `<html>`
- **Anti-flash**: inline script trong `<head>` đọc `localStorage('ait-theme')` và set `data-theme` trước khi CSS render
- `applyTheme(theme)` trong `static/js/main.js` — chỉ cập nhật `data-theme` và localStorage (không còn cập nhật icon/label vì floating controls đã xóa)

### Đa ngôn ngữ VI / EN (client-side)
- Không dùng Django i18n. Text đánh dấu bằng `data-i18n="key"` trên element HTML
- Placeholder input: `data-i18n-placeholder="key"` — `applyLang` gán `el.setAttribute('placeholder', ...)`
- `const i18n = { vi: {...}, en: {...} }` trong `static/js/main.js` — ~120+ keys, nhóm theo prefix:
  - `nav.*`, `footer.*` — navbar/footer (base.html)
  - `hero.*`, `stat.*`, `feat*`, `how.*`, `cta.*` — landing page
  - `auth.login.*`, `auth.register.*`, `auth.label.*`, `auth.otp.*`, `auth.btn.*` — auth forms
  - `dep.*` — trang nạp tiền; `prof.*` — hồ sơ; `trad.*` — trang AI Trading; `settings.*` — trang cài đặt
  - `com.th.*`, `com.coins_unit`, `com.no_tx` — dùng chung (table headers, đơn vị)
  - `err404.*` — trang 404
- `applyLang(lang)` query `[data-i18n]` → `textContent`; query `[data-i18n-placeholder]` → `placeholder`
- **Button có icon**: đặt `data-i18n` trên `<span>` bên trong, không đặt trực tiếp lên `<button>` (textContent xóa mất icon `<i>`)
- Khi thêm text mới: thêm key vào cả `i18n.vi` và `i18n.en`, gán attribute vào HTML

### Theme & Language Toggle
- Floating Controls (nút góc phải) **đã bị xóa** khỏi `base.html`
- Toggle chuyển vào trang `/profile/settings/` — hai card: Giao diện (Dark/Light) + Ngôn ngữ (VI/EN)
- JS dùng `addEventListener`, gọi global `applyTheme()` / `applyLang()` — không override bằng inline onclick
- `applyTheme(theme)`: chỉ cập nhật `data-theme` và localStorage (không còn cập nhật icon/label)
- `syncSettingsUI()`: đọc localStorage để highlight card option đang active

## Thiết kế & UI/UX

Dark-theme SaaS hiện đại — tham khảo `Design.jpg`.

### Bảng màu
```
Nền chính:        #0D0D0D / #0F1117
Nền card/section: #1A1A2E / #16213E
Accent chính:     #3B82F6  (CTA, highlight, border active)
Accent phụ:       #6366F1  (gradient với accent chính)
Text chính:       #F1F5F9
Text phụ:         #94A3B8
Border/divider:   #1E293B
Thành công:       #10B981  (COMPLETED)
Cảnh báo/Chờ:    #F59E0B  (PENDING)
Lỗi:             #EF4444  (FAILED)
```

### Typography
- Font: `Inter` (Google Fonts)
- Hero headline: `3.5rem / weight 800`
- Section headline: `2rem / weight 700`
- Body: `1rem / weight 400`, màu text phụ
- Badge/label: `0.75rem / weight 600`, uppercase + letter-spacing

### Components tái sử dụng
- **Card**: bg `#1A1A2E`, border `#1E293B`, radius `12px`, padding `24px`, hover `translateY(-4px)` + shadow xanh
- **Button primary**: gradient `#3B82F6 → #6366F1`, radius `8px`, padding `12px 28px`
- **Button secondary**: transparent + border `#3B82F6`
- **Badge/Status**: pill shape, màu theo trạng thái
- **Input**: bg `#1E293B`, border `#334155`, focus ring accent
- **Table**: bg `#111827`, header `#1F2937`, row hover `#1E2A3A`

### Dashboard (sau đăng nhập)
- Sidebar trái: `#111827`, active highlight xanh
- Stat Card: số lớn + trend indicator cho coins/số giao dịch
- Bảng lịch sử: badge status, TxHash rút gọn + copy button

### Animation
- Default transition: `all 0.2s ease`
- **Scroll fade-in**: class `animate-on-scroll` + `IntersectionObserver`
  - CSS: `@keyframes scrollFadeUp` (không dùng `transition`) — animation có thể restart
  - JS: `classList.remove('visible')` → `void el.offsetWidth` (force reflow) → `classList.add('visible')` mỗi lần scroll vào; remove khi scroll ra
  - Exception: `.error-page .animate-on-scroll { opacity: 1; }` — trang 404 không cần scroll
- `.btn-ghost-sm` hover: viền accent xuất hiện (`border: 1px solid transparent` → `border-color: var(--accent)`)
- Loading: skeleton screen

### Responsive
- Mobile-first, breakpoints: `sm:640px md:768px lg:1024px xl:1280px`
- Navbar mobile: hamburger + slide-in drawer
- Dashboard sidebar: collapse thành bottom nav trên mobile
