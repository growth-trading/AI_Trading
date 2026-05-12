---
description: Kiến trúc tổng thể, URL structure, model CustomUser, OTP flow, quyền truy cập và lưu ý DOM order cho base.html
alwaysApply: true
---

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

## URL Structure

```
/                           → trading.landing
/accounts/register|login|logout|verify|resend-otp/
/dashboard/                 → accounts.dashboard_view
/deposit/                   → deposits.deposit_view, submit_txhash_view, check_deposit_status
/trading/                   → trading.trading_view
/profile/                   → profiles.profile_view
<bất kỳ URL nào khác>       → catch-all re_path → page_not_found → templates/404.html
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

## OTP Email Flow

1. Đăng ký → `user.generate_otp()` → gửi SMTP → lưu `user.pk` vào session `pending_verify_user_id`
2. `/accounts/verify/` → `user.is_otp_valid(code)` → set `is_email_verified=True`, clear `otp_code` + `otp_created_at` → login
3. Đăng nhập (`login_view`): sau `authenticate()`, nếu `is_email_verified=False` → redirect `verify_otp` (không login thẳng)

## Quyền truy cập

- `trading_view` (`trading/views.py`) — redirect về `register` nếu chưa đăng nhập
- `deposit_view` kiểm tra `request.user.is_email_verified` trước khi hiển thị trang nạp tiền
- `login_view` kiểm tra `is_email_verified` — nếu chưa verify → redirect `verify_otp`
- Các view nội bộ dùng `@login_required`
- Các view yêu cầu trả phí phải kiểm tra `is_email_verified` **và** đủ `coins`

## Cấu trúc base.html — lưu ý DOM order

`templates/base.html` có phần **Floating Controls** (nút theme/ngôn ngữ) phải được đặt **trước** các thẻ `<script>` ở cuối body. Nếu đặt sau script, `document.getElementById()` trả về `null` khi script chạy → event listener không được gắn → nút không hoạt động.

```html
<!-- Đúng thứ tự -->
<div class="floating-controls"> ... </div>   ← trước script
<script src="bootstrap.bundle.min.js"></script>
<script src="main.js"></script>
```
