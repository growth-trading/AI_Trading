---
description: Tổng quan dự án, công nghệ sử dụng và biến môi trường — áp dụng cho mọi tác vụ trong repo này
alwaysApply: true
---

## Tổng quan dự án

Ứng dụng web Django hỗ trợ giao dịch bằng AI, tích hợp nạp tiền USDT qua MetaMask, xác thực email bằng OTP. Người dùng chuyển USDT đến **ví Admin cố định** — backend tự động quét ví đó qua BscScan API và cộng xu vào tài khoản, hoặc người dùng có thể tự nhập TxHash. Xu dùng để mua:
- **Gói AI Trading** — phân tích biểu đồ bằng Gemini Vision + chỉ báo kỹ thuật cục bộ
- **Gói TradingView** — nhúng chart TradingView premium qua iframe

## Công nghệ sử dụng

- **Backend**: Django 4.2, Python 3.11+, `python-decouple` (`.env`)
- **Database**: SQLite (dev), `psycopg2-binary` có sẵn cho PostgreSQL
- **Frontend**: Django Templates + Bootstrap 5, Bootstrap Icons 1.11, Font Awesome 6.7.2, Web3.js (MetaMask), Lightweight Charts (biểu đồ nến)
- **Tác vụ nền**: không dùng Celery hay django-apscheduler (đã xóa); nạp tiền thủ công (user nhập TxHash)
- **Email**: Django SMTP (Gmail)
- **Blockchain**: BSC public RPC — `deposits/tasks.py` dùng `requests`
- **AI Analysis**: `google-generativeai` (Gemini 2.5 Flash Vision) — phân tích biểu đồ và đưa ra tín hiệu
- **Chỉ báo kỹ thuật**: `pandas>=2.0` + `ta==0.11.0` (package `ta`, `import ta as ta_lib`) — tính RSI/MACD/EMA/Supertrend cục bộ từ dữ liệu nến, không dùng API ngoài
- **Dữ liệu thị trường**: MetaTrader5 (MT5) — lấy nến OHLCV real-time; fallback Binance public API nếu MT5 không có sẵn
- **Cache**: `django-redis` + Redis (**bắt buộc** — thiếu `REDIS_URL` thì raise `ImproperlyConfigured`)

## Biến môi trường (`.env`)

```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=*                         # production: yourdomain.com,www.yourdomain.com

# Email SMTP
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Blockchain / Nạp tiền
ADMIN_WALLET_ADDRESS=0x...
USDT_CONTRACT_BSC=0x55d398326f99059fF775485246999027B3197955
BSCSCAN_API_KEY=
USDT_TO_COINS_RATE=1
WALLET_SCAN_INTERVAL_SECONDS=60
DJANGO_RUN_SCHEDULER=0                  # set 1 in production to start wallet scanner

# MetaTrader5 — nguồn dữ liệu nến real-time
MT5_ACCOUNT=
MT5_PASSWORD=
MT5_SERVER=

# Gemini AI — phân tích biểu đồ (free tier: 1500 req/day, đủ cho ~100 user)
GEMINI_API_KEY=

# Gói AI Trading (đơn vị: xu)
AI_PLAN_WEEK_COST=20
AI_PLAN_MONTH_COST=50
AI_PLAN_YEAR_COST=400

# Gói TradingView (đơn vị: xu — mặc định per-product, có thể override trong DB)
TV_PLAN_WEEK_COST=10
TV_PLAN_MONTH_COST=30
TV_PLAN_YEAR_COST=200

# Redis cache — để trống nếu dùng LocMemCache (dev single-process)
REDIS_URL=                              # vd: redis://127.0.0.1:6379/0
```
