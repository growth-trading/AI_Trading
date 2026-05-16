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
2. Batch-fetch existing hashes: filter(tx_hash__in=all_hashes) → set — tránh N+1 queries
3. Lọc: to_addr != admin_wallet → skip (advance max_block); tx_hash in existing_hashes → skip
4. _decode_memo(tx['input']) → "UID-XXXX" (regex ^(UID-\d{1,10}) — giới hạn 10 chữ số)
5. _resolve_user_from_memo(memo) → CustomUser.objects.get(pk=uid)
6. transaction.atomic():
   - DepositTransaction.objects.create(status=COMPLETED)
   - filter().update(coins=F('coins') + coins_credited)   ← atomic F() expression
   - Nếu thành công hoặc IntegrityError → advance max_block
   - Nếu Exception khác → KHÔNG advance max_block (tx sẽ retry ở scan sau)
7. Cập nhật WalletScanState.last_scanned_block nếu max_block > current
```

### 2. Manual TxHash (`deposits/views.py::submit_txhash_view`)

```
0. Kiểm tra request.user.is_email_verified — redirect verify_otp nếu chưa xác thực
1. Normalize tx_hash: lowercase trước mọi thao tác
2. Validate regex ^0x[0-9a-f]{64}$ (sau khi lowercase)
3. Rate-limit 5 req/phút/user (atomic cache.incr key dep:rate:{pk})
4. Kiểm tra sớm: tx_hash đã tồn tại trong DB → reject ngay (tránh lãng phí API quota)
5. Cache kết quả verify_txhash 60s (30s nếu None) — key dep:verify:{tx_hash}
6. verify_txhash(tx_hash) → 2-step BscScan: proxy lấy blockNumber → tokentx trong block đó
7. Kiểm tra memo == request.user.memo_code → reject nếu không khớp (kể cả memo rỗng)
8. transaction.atomic():
   - DepositTransaction.objects.create(user=request.user, status=COMPLETED)
   - filter().update(coins=F('coins') + coins_credited)   ← atomic F() expression
```

**Quan trọng:**
- **Luôn dùng `F('coins') + amount`** khi cộng coins — không dùng `user.coins + amount` (race condition)
- `verify_txhash` trả về `memo` decode từ `input` hex → dùng xác thực ownership
- Tỷ lệ: `coins_credited = amount_usdt * Decimal(str(settings.USDT_TO_COINS_RATE))` — dùng `Decimal(str(...))` tránh float precision loss

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
coins_credited = amount_usdt * Decimal(str(settings.USDT_TO_COINS_RATE))
# Dùng Decimal(str(...)) tránh float precision loss khi nhân với Decimal amount
```

## Memo format

- Người dùng ghi `UID-0042` vào trường `data` của tx MetaMask
- Backend decode: `bytes.fromhex(input_hex[:200]).decode('utf-8', errors='ignore')`, lấy prefix `UID-`
- Regex: `^(UID-\d{1,10})` — giới hạn 10 chữ số để tránh `OverflowError` khi parse PK
- Parse: `int(memo.split('-', 1)[1])` → PK của CustomUser; except `(ValueError, IndexError, OverflowError, CustomUser.DoesNotExist)`
