---
description: Tổng quan dự án, công nghệ sử dụng và biến môi trường — áp dụng cho mọi tác vụ trong repo này
alwaysApply: true
---

## Tổng quan dự án

Ứng dụng web Django hỗ trợ giao dịch bằng AI, tích hợp nạp tiền USDT qua MetaMask, xác thực email bằng OTP. Người dùng chuyển USDT đến **ví Admin cố định** — backend tự động quét ví đó qua BscScan API và cộng xu vào tài khoản, hoặc người dùng có thể tự nhập TxHash.

## Công nghệ sử dụng

- **Backend**: Django 4.2, Python 3.11+, `python-decouple` (`.env`)
- **Database**: SQLite (dev), `psycopg2-binary` có sẵn cho PostgreSQL
- **Frontend**: Django Templates + Bootstrap 5, Bootstrap Icons 1.11, Font Awesome 6.7.2, Web3.js (MetaMask)
- **Tác vụ nền**: `django-apscheduler` — scheduler khởi động trong `DepositsConfig.ready()`, không dùng Celery
- **Email**: Django SMTP (Gmail)
- **Blockchain**: BscScan API (BSC/BEP-20 USDT)

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
