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


def scan_admin_wallet():
    """Quét ví Admin tìm giao dịch USDT mới trên BSC."""
    from .models import DepositTransaction, WalletScanState
    from accounts.models import CustomUser

    admin_wallet = settings.ADMIN_WALLET_ADDRESS.lower()
    usdt_contract = settings.USDT_CONTRACT_BSC.lower()
    api_key = settings.BSCSCAN_API_KEY

    if not admin_wallet or not api_key:
        return

    state, _ = WalletScanState.objects.get_or_create(
        network='BSC',
        defaults={'last_scanned_block': 0},
    )

    try:
        resp = requests.get(
            'https://api.bscscan.com/api',
            params={
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': usdt_contract,
                'address': admin_wallet,
                'startblock': state.last_scanned_block + 1,
                'sort': 'asc',
                'apikey': api_key,
            },
            timeout=15,
        )
        data = resp.json()
    except Exception as e:
        logger.error('BscScan API error: %s', e)
        return

    if data.get('status') != '1':
        if data.get('message') != 'No transactions found':
            logger.warning('BscScan scan error: %s', data.get('message'))
        return

    max_block = state.last_scanned_block
    for tx in data.get('result', []):
        tx_hash = tx.get('hash', '').lower()   # normalize lowercase
        to_addr = tx.get('to', '').lower()
        block_number = int(tx.get('blockNumber', 0))
        raw_value = int(tx.get('value', 0))
        decimals = int(tx.get('tokenDecimal', 18))
        amount_usdt = Decimal(raw_value) / Decimal(10 ** decimals)

        if to_addr != admin_wallet:
            continue
        if DepositTransaction.objects.filter(tx_hash=tx_hash).exists():
            max_block = max(max_block, block_number)
            continue

        memo = _decode_memo(tx.get('input', ''))
        user = _resolve_user_from_memo(memo)

        # Tx không decode được memo → PENDING, chờ admin xử lý thủ công
        status = DepositTransaction.STATUS_COMPLETED if user else DepositTransaction.STATUS_PENDING
        confirmed = timezone.now() if user else None

        try:
            with transaction.atomic():
                dep = DepositTransaction.objects.create(
                    user=user,
                    tx_hash=tx_hash,
                    amount_usdt=amount_usdt,
                    coins_credited=amount_usdt * settings.USDT_TO_COINS_RATE,
                    status=status,
                    memo=memo,
                    network='BSC',
                    confirmed_at=confirmed,
                )
                if user:
                    CustomUser.objects.filter(pk=user.pk).update(
                        coins=F('coins') + dep.coins_credited
                    )
        except IntegrityError:
            # Race condition với manual submit hoặc scan chạy song song — bỏ qua
            logger.warning('Duplicate tx skipped in scan: %s', tx_hash)

        max_block = max(max_block, block_number)
        logger.info('Processed deposit %s: %s USDT → user %s (status=%s)', tx_hash, amount_usdt, user, status)

    if max_block > state.last_scanned_block:
        state.last_scanned_block = max_block
        state.save()


def verify_txhash(tx_hash: str):
    """Xác minh TxHash qua BscScan dùng 2 bước — hỗ trợ mọi TX kể cả rất cũ."""
    admin_wallet = settings.ADMIN_WALLET_ADDRESS.lower()
    usdt_contract = settings.USDT_CONTRACT_BSC.lower()
    api_key = settings.BSCSCAN_API_KEY

    # Bước 1: Lấy block number qua proxy (không bị giới hạn 10000 record lịch sử)
    try:
        resp = requests.get(
            'https://api.bscscan.com/api',
            params={
                'module': 'proxy',
                'action': 'eth_getTransactionByHash',
                'txhash': tx_hash,
                'apikey': api_key,
            },
            timeout=15,
        )
        proxy_data = resp.json()
    except Exception as e:
        logger.error('BscScan proxy error: %s', e)
        return None

    tx_result = proxy_data.get('result')
    if not tx_result or tx_result == 'null' or not isinstance(tx_result, dict):
        return None

    block_hex = tx_result.get('blockNumber')
    if not block_hex:
        return None
    try:
        block_number = int(block_hex, 16)
    except (ValueError, TypeError):
        return None

    # Bước 2: Query tokentx trong đúng block đó để lấy thông tin token transfer
    try:
        resp = requests.get(
            'https://api.bscscan.com/api',
            params={
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': usdt_contract,
                'address': admin_wallet,
                'startblock': block_number,
                'endblock': block_number,
                'sort': 'asc',
                'apikey': api_key,
            },
            timeout=15,
        )
        data = resp.json()
    except Exception as e:
        logger.error('BscScan tokentx error: %s', e)
        return None

    for tx in data.get('result', []):
        if tx.get('hash', '').lower() != tx_hash.lower():
            continue
        if tx.get('to', '').lower() != admin_wallet:
            return None
        decimals = int(tx.get('tokenDecimal', 18))
        amount = Decimal(int(tx.get('value', 0))) / Decimal(10 ** decimals)
        return {
            'tx_hash': tx.get('hash', '').lower(),
            'amount_usdt': amount,
            'block_number': block_number,
            'from_address': tx.get('from', '').lower(),
            'memo': _decode_memo(tx.get('input', '')),
        }

    return None


def _decode_memo(input_hex: str) -> str:
    try:
        if input_hex and input_hex != '0x':
            # Giới hạn 200 hex chars (~100 bytes) — memo UID-XXXX chỉ cần vài byte đầu
            hex_str = input_hex.replace('0x', '')[:200]
            raw = bytes.fromhex(hex_str)
            text = raw.decode('utf-8', errors='ignore').strip()
            # Strict: chỉ khớp UID- theo sau là chữ số, không chấp nhận ký tự thừa
            m = re.match(r'^(UID-\d+)', text)
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
        except (ValueError, IndexError, CustomUser.DoesNotExist):
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
