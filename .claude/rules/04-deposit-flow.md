---
description: Luồng nạp tiền USDT — models, background scan, manual TxHash, scheduler — áp dụng khi làm việc với deposits/
globs:
  - deposits/**
  - accounts/models.py
---

## Models (`deposits/models.py`)

**`DepositTransaction`**
- `user` (FK nullable) — nullable vì memo có thể không decode được
- `tx_hash` (unique, db_index) — ngăn double-credit
- `amount_usdt` (Decimal 18,6), `coins_credited` (Decimal 18,2)
- `status`: PENDING / COMPLETED / FAILED
- `memo` (max 50 chars), `network` (default 'BSC'), `confirmed_at`

**`WalletScanState`**
- Lưu `last_scanned_block` theo `network` trong DB — **không** dùng `.env`
- `get_or_create(network='BSC')` để khởi tạo lần đầu

## Hai cách nạp tiền

### 1. Auto-scan (`deposits/tasks.py::scan_admin_wallet`)

Chạy mỗi `WALLET_SCAN_INTERVAL_SECONDS` giây qua `django-apscheduler`:

```
1. BscScan API tokentx (startblock = last_scanned_block + 1)
2. Lọc tx có to_addr == admin_wallet
3. Bỏ qua nếu tx_hash đã tồn tại trong DB
4. _decode_memo(tx['input']) → "UID-XXXX"
5. _resolve_user_from_memo(memo) → CustomUser.objects.get(pk=uid)
6. transaction.atomic():
   - DepositTransaction.objects.create(status=COMPLETED)
   - filter().update(coins=F('coins') + coins_credited)   ← atomic F() expression
7. Cập nhật WalletScanState.last_scanned_block
```

### 2. Manual TxHash (`deposits/views.py::submit_txhash_view`)

```
0. Kiểm tra request.user.is_email_verified — redirect verify_otp nếu chưa xác thực
1. Validate tx_hash bằng regex ^0x[0-9a-fA-F]{64}$ (thay vì chỉ kiểm tra len)
2. Kiểm tra tx_hash chưa tồn tại trong DB
3. verify_txhash(tx_hash) → BscScan lookup → dict{tx_hash, amount_usdt, memo, ...} hoặc None
4. Nếu memo có giá trị: kiểm tra memo == request.user.memo_code → reject nếu không khớp
5. transaction.atomic():
   - DepositTransaction.objects.create(user=request.user, status=COMPLETED)
   - filter().update(coins=F('coins') + coins_credited)   ← atomic F() expression
```

**Quan trọng:**
- **Luôn dùng `F('coins') + amount`** khi cộng coins — không dùng `user.coins + amount` (race condition)
- `verify_txhash` trả về `memo` được decode từ `input` hex của tx → dùng để xác thực ownership

## Scheduler (`deposits/apps.py`)

`DepositsConfig.ready()` chỉ khởi động scheduler khi:
- **Dev**: `RUN_MAIN=true` (Django autoreloader child process khi `runserver`)
- **Production**: `DJANGO_RUN_SCHEDULER=1` (set trong env)

Guard `_scheduler_started` (module-level bool) ngăn khởi động nhiều lần trong cùng process.  
Scheduler dùng `DjangoJobStore` — jobs được lưu vào DB qua `django-apscheduler`.

**Không chạy** khi: `migrate`, `test`, `shell`, `collectstatic`, v.v.

## Tỷ lệ quy đổi

`USDT_TO_COINS_RATE` (int, mặc định 1):
```python
coins_credited = amount_usdt * settings.USDT_TO_COINS_RATE
```

## Memo format

- Người dùng ghi `UID-0042` vào trường `data` của tx MetaMask
- Backend decode: `bytes.fromhex(input_hex).decode('utf-8')`, lấy prefix `UID-`
- Parse: `int(memo.split('-')[1])` → PK của CustomUser
