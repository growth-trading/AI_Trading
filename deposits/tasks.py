import logging
import requests
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)

_BSC_RPC_URLS = [
    'https://bsc-rpc.publicnode.com',
    'https://bsc-dataseed.binance.org/',
    'https://bsc-dataseed1.binance.org/',
    'https://bsc-dataseed2.binance.org/',
]
_TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
_USDT_DECIMALS = 18


def _rpc(method, params):
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


def verify_txhash(tx_hash: str):
    """Xác minh TxHash qua BSC public RPC — không cần API key."""
    admin_wallet = settings.ADMIN_WALLET_ADDRESS.lower()
    usdt_contract = settings.USDT_CONTRACT_BSC.lower()

    tx = _rpc('eth_getTransactionByHash', [tx_hash])
    if not tx or not tx.get('blockNumber'):
        return None

    receipt = _rpc('eth_getTransactionReceipt', [tx_hash])
    if not receipt:
        return None

    block_number = int(tx['blockNumber'], 16)

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
        }

    return None
