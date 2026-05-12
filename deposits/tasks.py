import logging
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction
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
        logger.error(f"BscScan API error: {e}")
        return

    if data.get('status') != '1':
        return

    max_block = state.last_scanned_block
    for tx in data.get('result', []):
        tx_hash = tx.get('hash', '')
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

        with transaction.atomic():
            dep = DepositTransaction.objects.create(
                user=user,
                tx_hash=tx_hash,
                amount_usdt=amount_usdt,
                coins_credited=amount_usdt * settings.USDT_TO_COINS_RATE,
                status=DepositTransaction.STATUS_COMPLETED,
                memo=memo,
                network='BSC',
                confirmed_at=timezone.now(),
            )
            if user:
                user.__class__.objects.filter(pk=user.pk).update(
                    coins=F('coins') + dep.coins_credited
                )

        max_block = max(max_block, block_number)
        logger.info(f"Processed deposit {tx_hash}: {amount_usdt} USDT → user {user}")

    if max_block > state.last_scanned_block:
        state.last_scanned_block = max_block
        state.save()


def verify_txhash(tx_hash: str):
    """Xác minh một TxHash cụ thể qua BscScan. Trả về dict thông tin hoặc None."""
    admin_wallet = settings.ADMIN_WALLET_ADDRESS.lower()
    usdt_contract = settings.USDT_CONTRACT_BSC.lower()
    api_key = settings.BSCSCAN_API_KEY

    try:
        resp = requests.get(
            'https://api.bscscan.com/api',
            params={
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': usdt_contract,
                'address': admin_wallet,
                'apikey': api_key,
            },
            timeout=15,
        )
        data = resp.json()
    except Exception as e:
        logger.error(f"BscScan verify error: {e}")
        return None

    if data.get('status') != '1':
        return None

    for tx in data.get('result', []):
        if tx.get('hash', '').lower() != tx_hash.lower():
            continue
        if tx.get('to', '').lower() != admin_wallet:
            return None
        decimals = int(tx.get('tokenDecimal', 18))
        amount = Decimal(int(tx.get('value', 0))) / Decimal(10 ** decimals)
        return {
            'tx_hash': tx.get('hash'),
            'amount_usdt': amount,
            'block_number': int(tx.get('blockNumber', 0)),
            'from_address': tx.get('from'),
            'memo': _decode_memo(tx.get('input', '')),
        }
    return None


def _decode_memo(input_hex: str) -> str:
    try:
        if input_hex and input_hex != '0x':
            raw = bytes.fromhex(input_hex.replace('0x', ''))
            text = raw.decode('utf-8', errors='ignore').strip()
            if text.startswith('UID-'):
                return text[:20]
    except Exception:
        pass
    return ''


def _resolve_user_from_memo(memo: str):
    from accounts.models import CustomUser
    if memo.startswith('UID-'):
        try:
            uid = int(memo.split('-')[1])
            return CustomUser.objects.get(pk=uid)
        except (ValueError, CustomUser.DoesNotExist):
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
        logger.info("Wallet scanner scheduler started.")
    except Exception as e:
        logger.error(f"Scheduler start failed: {e}")
