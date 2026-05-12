---
description: Kiến trúc tổng thể, URL structure, model CustomUser, OTP flow và quyền truy cập
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
```

## Model CustomUser (`accounts/models.py`)

Kế thừa `AbstractUser`, thêm:
- `coins` (DecimalField 18,2) — số dư nội bộ
- `is_email_verified` (BooleanField) — gate cho nạp tiền và tính năng AI
- `otp_code`, `otp_created_at` — OTP lưu trực tiếp trên user, hết hạn sau 10 phút
- `memo_code` (property) — trả về `f"UID-{self.pk:04d}"`

## OTP Email Flow

1. Đăng ký → `user.generate_otp()` → gửi SMTP → lưu `user.pk` vào session `pending_verify_user_id`
2. `/accounts/verify/` → `user.is_otp_valid(code)` → set `is_email_verified=True` → login

## Quyền truy cập

- `deposit_view` kiểm tra `request.user.is_email_verified` trước khi hiển thị trang nạp tiền
- Các view nội bộ dùng `@login_required`
- Các view yêu cầu trả phí phải kiểm tra `is_email_verified` **và** đủ `coins`
