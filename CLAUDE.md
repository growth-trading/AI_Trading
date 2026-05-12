# CLAUDE.md

File này cung cấp hướng dẫn cho Claude Code (claude.ai/code) khi làm việc với mã nguồn trong repository này.

## Tổng quan dự án

Ứng dụng web Django hỗ trợ giao dịch bằng AI, tích hợp nạp tiền USDT qua MetaMask, xác thực email bằng OTP, và quản lý bot giao dịch AI. Người dùng chuyển USDT đến **ví Admin cố định** — hệ thống backend tự động theo dõi ví đó qua API BscScan/Etherscan và cộng xu vào tài khoản khi phát hiện giao dịch hợp lệ, không cần người dùng nhập TxHash.

## Công nghệ sử dụng

- **Backend**: Django 4.x, Python 3.11+
- **Database**: SQLite (development)
- **Frontend**: Django Templates + Bootstrap 5, Web3.js cho tích hợp MetaMask
- **Email**: Django SMTP backend (Gmail hoặc SendGrid)
- **Xác minh blockchain**: BscScan API / Etherscan API — polling định kỳ theo dõi ví Admin
- **Tác vụ nền**: Celery + Redis (polling blockchain) hoặc `django-apscheduler` (đơn giản hơn)
- **Cấu hình môi trường**: `python-decouple` hoặc `django-environ` qua `.env`

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
python manage.py test                              # chạy toàn bộ test
python manage.py test accounts                     # test một app
python manage.py test accounts.tests.TestDeposit  # test một class cụ thể

# File tĩnh (production)
python manage.py collectstatic
```

## Cấu trúc dự án

```
aitrading/          # Cấu hình Django project (settings.py, urls.py, wsgi.py)
accounts/           # Xác thực người dùng: model CustomUser, đăng ký, xác thực email OTP
deposits/           # Luồng nạp tiền: model DepositTransaction, task theo dõi ví Admin, tự động cộng xu
trading/            # Trang giới thiệu AI trading: thuật toán, kết quả backtest, commission farming
profiles/           # Hồ sơ người dùng: upload avatar, lịch sử xu, quyền sử dụng dịch vụ
templates/          # HTML templates, phân theo app
static/             # CSS, JS (bao gồm web3.js), hình ảnh
.env                # Khóa bí mật và API credentials (không được commit)
```

## Kiến trúc & Luồng xử lý chính

### Model người dùng (`accounts/models.py`)
Kế thừa `AbstractUser` với các trường bổ sung:
- `avatar` (ImageField)
- `coins` (DecimalField) — số dư nội bộ được cộng sau khi nạp tiền thành công
- `is_email_verified` (BooleanField) — kiểm soát quyền truy cập tính năng nạp tiền và AI

### Đăng ký với OTP qua Email (`accounts/`)
1. Người dùng đăng ký → tài khoản tạo với `is_active=True`, `is_email_verified=False`
2. OTP được tạo và gửi qua SMTP
3. Người dùng nhập OTP tại `/verify/` → `is_email_verified=True`

### Luồng nạp tiền (`deposits/`)

**Model `DepositTransaction`**: `user` (FK, nullable — xem bên dưới), `tx_hash` (unique), `amount_usdt`, `coins_credited`, `status` (PENDING/COMPLETED/FAILED), `created_at`, `memo` (mã định danh người dùng).

**Quy trình phía người dùng:**
1. Người dùng vào tab "Nạp tiền" → hệ thống hiển thị **địa chỉ ví Admin cố định** và một **mã memo** duy nhất (vd: `UID-0042`).
2. Người dùng mở MetaMask, chuyển USDT đến địa chỉ ví Admin, ghi memo vào trường `data` hoặc dùng tính năng "tag/memo" nếu mạng hỗ trợ.
3. Trang hiển thị trạng thái chờ xác nhận theo thời gian thực (polling AJAX hoặc WebSocket).

**Quy trình phía backend (tác vụ nền — chạy mỗi 30–60 giây):**
```
deposits/tasks.py :: scan_admin_wallet()
  1. Gọi BscScan API: GET /api?module=account&action=tokentx
     &address=ADMIN_WALLET_ADDRESS&contractaddress=USDT_CONTRACT
  2. Lọc các tx mới (blockNumber > last_scanned_block).
  3. Với mỗi tx:
     a. Bỏ qua nếu tx_hash đã tồn tại trong DB (chống replay).
     b. Đọc memo từ input data → ánh xạ sang user.
     c. Tạo DepositTransaction(status=COMPLETED).
     d. Cộng coins vào user.coins (atomic transaction).
  4. Lưu last_scanned_block vào DB/cache.
```

**Nếu memo không đọc được (mạng BSC không hỗ trợ memo dạng text):**
- Dùng phương án dự phòng: mỗi user được cấp một **địa chỉ phụ** (sub-wallet) dẫn tiền về ví Admin, hoặc người dùng tự nhập TxHash để hệ thống tra cứu và khớp với tài khoản.

**Bảo mật:** `tx_hash` unique ngăn double-credit. Toàn bộ logic cộng tiền dùng `select_for_update()` để tránh race condition. Địa chỉ ví Admin và USDT contract address lưu trong `.env`.

### View yêu cầu quyền trả phí
Các view cần trả phí (ví dụ: tạo file `.md`) phải kiểm tra `request.user.is_email_verified` và đủ `coins` trước khi xử lý.

## Thiết kế & UI/UX

### Phong cách tổng thể
Dark-theme SaaS hiện đại — tham khảo file `Design.jpg`. Giao diện tối màu, typography lớn, bố cục thoáng, cảm giác cao cấp và trẻ trung. Ưu tiên whitespace, tránh rối mắt.

### Bảng màu
```
Nền chính:        #0D0D0D hoặc #0F1117   (gần đen, không phải đen tuyệt đối)
Nền card/section: #1A1A2E hoặc #16213E
Accent chính:     #3B82F6  (xanh dương — dùng cho CTA, highlight, border active)
Accent phụ:       #6366F1  (tím indigo — gradient với accent chính)
Text chính:       #F1F5F9
Text phụ:         #94A3B8
Border/divider:   #1E293B
Thành công:       #10B981  (màu cộng tiền, trạng thái COMPLETED)
Cảnh báo/Chờ:    #F59E0B  (trạng thái PENDING)
Lỗi:             #EF4444  (trạng thái FAILED)
```

### Typography
- Font: `Inter` (Google Fonts) — sans-serif, đọc tốt trên nền tối
- Headline hero: `font-size: 3.5rem`, `font-weight: 800`, line-height chặt
- Subheadline section: `2rem`, `font-weight: 700`
- Body text: `1rem`, `font-weight: 400`, màu text phụ
- Label/badge: `0.75rem`, `font-weight: 600`, uppercase + letter-spacing

### Cấu trúc trang chính (Landing Page)

```
1. Navbar         — logo trái, nav links giữa, CTA button phải (sticky, blur backdrop)
2. Hero           — headline lớn 2 dòng + subtitle + 2 nút CTA + dashboard screenshot bên dưới
3. Features Grid  — 3 cột icon + tiêu đề + mô tả ngắn (alternating dark/light sections)
4. How It Works   — 3 bước nạp tiền với số thứ tự lớn + mô tả
5. AI Trading     — showcase backtest results dạng card/chart + highlight lợi nhuận
6. Testimonials   — quote cards với avatar (nếu có)
7. CTA Banner     — nền gradient xanh dương, headline + nút đăng ký lớn
8. Footer         — links, logo, copyright
```

### Components tái sử dụng
- **Card**: `background: #1A1A2E`, `border: 1px solid #1E293B`, `border-radius: 12px`, `padding: 24px`, hover lift với `box-shadow` xanh nhạt
- **Button primary**: gradient `#3B82F6 → #6366F1`, `border-radius: 8px`, `padding: 12px 28px`, hover sáng lên
- **Button secondary**: transparent + `border: 1px solid #3B82F6`, text xanh
- **Badge/Status**: pill shape, màu theo trạng thái (xanh lá/vàng/đỏ)
- **Input field**: `background: #1E293B`, `border: 1px solid #334155`, focus ring màu accent
- **Table**: nền `#111827`, header `#1F2937`, row hover `#1E2A3A`, text màu phụ cho meta-data

### Dashboard & Trang nội bộ (sau đăng nhập)
- Sidebar trái: dark `#111827`, icons + labels, active item highlight xanh
- Main content: nền `#0D0D0D`, padding rộng
- Số liệu (coins, số giao dịch): hiển thị dạng **Stat Card** — số lớn + trend indicator
- Bảng lịch sử giao dịch: sortable, có badge status, TxHash rút gọn + copy button

### Animation & Hiệu ứng
- Transition mặc định: `transition: all 0.2s ease`
- Card hover: `transform: translateY(-4px)` + shadow
- Số liệu tăng: count-up animation khi vào viewport
- Loading state: skeleton screen (không dùng spinner đơn thuần)
- Fade-in section khi scroll: `IntersectionObserver` + CSS class `animate-fadeInUp`

### Responsive
- Mobile-first, breakpoints: `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`
- Navbar mobile: hamburger menu, slide-in drawer
- Grid features: 3 cột → 1 cột trên mobile
- Dashboard sidebar: collapse thành bottom nav trên mobile

## Biến môi trường (`.env`)

```
SECRET_KEY=
DEBUG=True
DATABASE_URL=
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
ADMIN_WALLET_ADDRESS=0x...          # Ví MetaMask của Admin nhận USDT
USDT_CONTRACT_BSC=0x55d398326f99059fF775485246999027B3197955  # USDT BEP-20
BSCSCAN_API_KEY=
ETHERSCAN_API_KEY=
WALLET_SCAN_INTERVAL_SECONDS=60   # Tần suất polling ví Admin
LAST_SCANNED_BLOCK_BSC=0          # Hoặc lưu vào DB thay vì .env
```
