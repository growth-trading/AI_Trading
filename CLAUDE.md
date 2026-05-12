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
- **Frontend**: Django Templates + Bootstrap 5, Web3.js (MetaMask)
- **Tác vụ nền**: `django-apscheduler` — scheduler khởi động trong `DepositsConfig.ready()`, không dùng Celery
- **Email**: Django SMTP (Gmail)
- **Blockchain**: BscScan API (BSC/BEP-20 USDT)

## Cấu trúc project

```
aitrading/       # settings.py, urls.py, wsgi.py
accounts/        # CustomUser, đăng ký, OTP email, dashboard
deposits/        # DepositTransaction, WalletScanState, tasks, views
trading/         # landing page, trang trading
profiles/        # hồ sơ, avatar, lịch sử giao dịch
templates/       # HTML phân theo app (landing/, accounts/, dashboard/, deposits/, profiles/, emails/)
static/          # CSS, JS, web3.js, hình ảnh
```

## Kiến trúc & Luồng xử lý chính

### Model người dùng (`accounts/models.py::CustomUser`)
Kế thừa `AbstractUser`, thêm:
- `coins` (DecimalField 18,2) — số dư nội bộ
- `is_email_verified` (BooleanField) — gate cho nạp tiền và tính năng AI
- `otp_code`, `otp_created_at` — OTP lưu trực tiếp trên user, hết hạn sau 10 phút
- `memo_code` (property) — trả về `f"UID-{self.pk:04d}"`

### OTP Email Flow
1. Đăng ký → `user.generate_otp()` → gửi SMTP → lưu `user.pk` vào session `pending_verify_user_id`
2. `/accounts/verify/` → `user.is_otp_valid(code)` → set `is_email_verified=True` → login

### Luồng nạp tiền (`deposits/`)

**Models:**
- `DepositTransaction`: `user` (FK nullable), `tx_hash` (unique), `amount_usdt`, `coins_credited`, `status` (PENDING/COMPLETED/FAILED), `memo`, `network`, `confirmed_at`
- `WalletScanState`: lưu `last_scanned_block` theo `network` trong DB (không phải `.env`)

**Hai cách nạp tiền:**

1. **Tự động (background scan)** — `deposits/tasks.py::scan_admin_wallet()` chạy mỗi `WALLET_SCAN_INTERVAL_SECONDS` giây:
   - Gọi BscScan API `tokentx` từ `last_scanned_block + 1`
   - Decode memo từ `input` hex (`UID-XXXX`) → map sang user qua `CustomUser.objects.get(pk=uid)`
   - Cộng coins: dùng `filter().update()` (atomic, tránh race condition)
   - Cập nhật `WalletScanState.last_scanned_block`

2. **Thủ công (submit TxHash)** — `deposits/views.py::submit_txhash_view()`:
   - User nhập TxHash → `verify_txhash()` tra BscScan → tạo `DepositTransaction` + cộng coins

**Scheduler khởi động:** `deposits/apps.py::DepositsConfig.ready()` gọi `tasks.start_scheduler()` một lần duy nhất khi Django khởi động. Guard `_scheduler_started` ngăn khởi động nhiều lần.

**Tỷ lệ quy đổi:** `USDT_TO_COINS_RATE` (int, mặc định 1) — `coins_credited = amount_usdt * USDT_TO_COINS_RATE`

### URL Structure
```
/                           → trading.landing
/accounts/register|login|logout|verify|resend-otp/
/dashboard/                 → accounts.dashboard_view
/deposit/                   → deposits.deposit_view, submit_txhash_view, check_deposit_status
/trading/                   → trading.trading_view
/profile/                   → profiles.profile_view
```

### Quyền truy cập
`deposit_view` kiểm tra `request.user.is_email_verified` trước khi hiển thị. Các view nội bộ dùng `@login_required`.

## Biến môi trường (`.env`)

```
SECRET_KEY=
DEBUG=True
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
ADMIN_WALLET_ADDRESS=0x...
USDT_CONTRACT_BSC=0x55d398326f99059fF775485246999027B3197955
BSCSCAN_API_KEY=
USDT_TO_COINS_RATE=1
WALLET_SCAN_INTERVAL_SECONDS=60
```

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
- Scroll fade-in: `IntersectionObserver` + class `animate-fadeInUp`
- Loading: skeleton screen

### Responsive
- Mobile-first, breakpoints: `sm:640px md:768px lg:1024px xl:1280px`
- Navbar mobile: hamburger + slide-in drawer
- Dashboard sidebar: collapse thành bottom nav trên mobile
