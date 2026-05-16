import re
import logging
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.db.models import F

logger = logging.getLogger(__name__)
_scheduler_started = False

# BSC public RPC — không cần API key, thử lần lượt khi endpoint lỗi
# bsc-rpc.publicnode.com: hỗ trợ eth_getLogs (cần cho scan_admin_wallet)
# bsc-dataseed*: hỗ trợ eth_getTransactionByHash (nhanh hơn cho verify_txhash)
_BSC_RPC_URLS = [
    'https://bsc-rpc.publicnode.com',
    'https://bsc-dataseed.binance.org/',
    'https://bsc-dataseed1.binance.org/',
    'https://bsc-dataseed2.binance.org/',
]
_TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
_USDT_DECIMALS = 18
_MEMO_MAX_HEX_LEN = 200  # 100 bytes — đủ để decode memo UID-XXXX


def _rpc(method, params):
    """Gọi JSON-RPC đến BSC node. Thử lần lượt các endpoint đến khi thành công."""
    for url in _BSC_RPC_URLS:
        try:
            r = requests.post(
                url,
                json={'jsonrpc': '2.0', 'method': method, 'params': params, 'id': 1},
                timeout=15,
            )
            data = r.json()
            if 'error' not in data:
                return data.get('result')
            logger.warning('BSC RPC %s error from %s: %s', method, url, data['error'])
        except Exception as e:
            logger.warning('BSC RPC request failed (%s %s): %s', method, url, e)
    return None


def _usdt_amount(data_hex: str) -> Decimal:
    try:
        return Decimal(int(data_hex, 16)) / Decimal(10 ** _USDT_DECIMALS)
    except Exception:
        return Decimal('0')


def scan_admin_wallet():
    """Quét sự kiện Transfer USDT đến ví Admin qua BSC public RPC."""
    from .models import DepositTransaction, WalletScanState
    from accounts.models import CustomUser

    admin_wallet = settings.ADMIN_WALLET_ADDRESS.lower()
    usdt_contract = settings.USDT_CONTRACT_BSC.lower()

    state, _ = WalletScanState.objects.get_or_create(
        network='BSC', defaults={'last_scanned_block': 0},
    )

    latest_hex = _rpc('eth_blockNumber', [])
    if not latest_hex:
        return
    latest_block = int(latest_hex, 16)
    from_block = state.last_scanned_block + 1
    if from_block > latest_block:
        return
    to_block = min(latest_block, from_block + 4999)  # max 5000 blocks / scan

    # Topic filter: Transfer(_, admin_wallet) trên USDT contract
    admin_topic = '0x000000000000000000000000' + admin_wallet[2:]
    logs = _rpc('eth_getLogs', [{
        'address': usdt_contract,
        'topics': [_TRANSFER_TOPIC, None, admin_topic],
        'fromBlock': hex(from_block),
        'toBlock': hex(to_block),
    }])
    if logs is None:
        logger.error('eth_getLogs failed — will retry on next scan')
        return

    # Batch-check existing hashes để tránh N+1 queries
    all_hashes = [log.get('transactionHash', '').lower() for log in logs]
    existing_hashes = set(
        DepositTransaction.objects.filter(tx_hash__in=all_hashes).values_list('tx_hash', flat=True)
    )

    new_max_block = to_block  # advance đến cuối range nếu không có lỗi

    for log in logs:
        if log.get('removed'):
            continue  # block bị reorg

        tx_hash = log.get('transactionHash', '').lower()
        block_number = int(log.get('blockNumber', '0x0'), 16)

        if tx_hash in existing_hashes:
            continue  # đã xử lý

        topics = log.get('topics', [])
        if len(topics) < 3:
            continue
        amount_usdt = _usdt_amount(log.get('data', '0x0'))

        # Fetch tx để đọc memo từ input field
        tx = _rpc('eth_getTransactionByHash', [tx_hash])
        if tx is None:
            # RPC fail tạm thời — không advance qua block này để retry lần sau
            new_max_block = min(new_max_block, block_number - 1)
            continue
        memo = _decode_memo(tx.get('input', ''))
        user = _resolve_user_from_memo(memo)

        # Tx không có memo hợp lệ → PENDING, user cần tự nộp TxHash thủ công
        status = DepositTransaction.STATUS_COMPLETED if user else DepositTransaction.STATUS_PENDING
        confirmed = timezone.now() if user else None

        success = False
        try:
            with transaction.atomic():
                dep = DepositTransaction.objects.create(
                    user=user,
                    tx_hash=tx_hash,
                    amount_usdt=amount_usdt,
                    coins_credited=amount_usdt * Decimal(str(settings.USDT_TO_COINS_RATE)),
                    status=status,
                    memo=memo,
                    network='BSC',
                    confirmed_at=confirmed,
                )
                if user:
                    CustomUser.objects.filter(pk=user.pk).update(
                        coins=F('coins') + dep.coins_credited
                    )
            success = True
            logger.info('Processed deposit %s: %s USDT → user %s (status=%s)', tx_hash, amount_usdt, user, status)
        except IntegrityError:
            success = True  # race condition — tx đã tồn tại, không phải lỗi thật
            logger.warning('Duplicate tx skipped in scan: %s', tx_hash)
        except Exception:
            logger.exception('Failed to process tx %s — will retry on next scan', tx_hash)

        if not success:
            # Không advance qua block bị lỗi để retry ở lần scan sau
            new_max_block = min(new_max_block, block_number - 1)

    if new_max_block > state.last_scanned_block:
        state.last_scanned_block = new_max_block
        state.save()


def verify_txhash(tx_hash: str):
    """Xác minh TxHash qua BSC public RPC — không cần API key."""
    admin_wallet = settings.ADMIN_WALLET_ADDRESS.lower()
    usdt_contract = settings.USDT_CONTRACT_BSC.lower()

    tx = _rpc('eth_getTransactionByHash', [tx_hash])
    if not tx or not tx.get('blockNumber'):
        return None  # không tìm thấy hoặc chưa confirmed (pending)

    receipt = _rpc('eth_getTransactionReceipt', [tx_hash])
    if not receipt:
        return None

    block_number = int(tx['blockNumber'], 16)
    memo = _decode_memo(tx.get('input', ''))

    for log in receipt.get('logs', []):
        if log.get('address', '').lower() != usdt_contract:
            continue
        topics = log.get('topics', [])
        if len(topics) < 3 or topics[0].lower() != _TRANSFER_TOPIC:
            continue
        to_addr = '0x' + topics[2][-40:]
        if to_addr.lower() != admin_wallet:
            continue
        from_addr = '0x' + topics[1][-40:]
        amount_usdt = _usdt_amount(log.get('data', '0x0'))
        return {
            'tx_hash': tx_hash.lower(),
            'amount_usdt': amount_usdt,
            'block_number': block_number,
            'from_address': from_addr.lower(),
            'memo': memo,
        }

    return None  # không tìm thấy USDT transfer đến admin_wallet trong tx này


def _decode_memo(input_hex: str) -> str:
    try:
        if input_hex and input_hex != '0x':
            hex_str = input_hex.replace('0x', '')[:_MEMO_MAX_HEX_LEN]
            raw = bytes.fromhex(hex_str)
            text = raw.decode('utf-8', errors='ignore').strip()
            m = re.match(r'^(UID-\d{1,10})', text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return ''


def _resolve_user_from_memo(memo: str):
    from accounts.models import CustomUser
    if memo.startswith('UID-'):
        try:
            uid = int(memo.split('-', 1)[1])
            return CustomUser.objects.get(pk=uid)
        except (ValueError, IndexError, OverflowError, CustomUser.DoesNotExist):
            pass
    return None


def start_scheduler():
    global _scheduler_started
    if _scheduler_started:
        return
    import django
    if not django.apps.registry.apps.ready:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore

        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), 'default')
        scheduler.add_job(
            scan_admin_wallet,
            trigger='interval',
            seconds=settings.WALLET_SCAN_INTERVAL_SECONDS,
            id='scan_admin_wallet',
            replace_existing=True,
            max_instances=1,
        )
        scheduler.start()
        _scheduler_started = True
        logger.info('Wallet scanner scheduler started.')
    except Exception as e:
        logger.error('Scheduler start failed: %s', e)
