import calendar
import logging
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_USDT_ABI = [
    {
        "inputs": [
            {"name": "recipient", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]
_BSC_RPC_LIST = [
    "https://bsc-dataseed.binance.org/",
    "https://bsc-dataseed1.binance.org/",
    "https://bsc-dataseed2.binance.org/",
    "https://bsc-rpc.publicnode.com",
]


def is_payout_window() -> bool:
    """Trả True nếu đang trong 2 ngày cuối tháng."""
    now = timezone.localtime(timezone.now())
    last_day = calendar.monthrange(now.year, now.month)[1]
    return now.day >= last_day - 1


def send_usdt_bsc(to_address: str, amount_usdt: Decimal) -> str:
    """
    Gửi USDT BEP-20 trên BSC từ ví admin.
    Trả về tx_hash dạng chuỗi 0x...
    Raise ValueError/ConnectionError/Exception nếu thất bại.
    """
    try:
        from web3 import Web3
    except ImportError:
        raise RuntimeError("Thư viện web3 chưa được cài đặt. Chạy: pip install web3")

    private_key = getattr(settings, "ADMIN_PRIVATE_KEY", "")
    if not private_key:
        raise ValueError("ADMIN_PRIVATE_KEY chưa được cấu hình trong .env")

    w3 = None
    for rpc in _BSC_RPC_LIST:
        candidate = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
        if candidate.is_connected():
            w3 = candidate
            break
    if w3 is None:
        raise ConnectionError("Không thể kết nối BSC RPC")

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.USDT_CONTRACT_BSC),
        abi=_USDT_ABI,
    )

    account = w3.eth.account.from_key(private_key)
    to_checksum = Web3.to_checksum_address(to_address)
    # USDT BEP-20 có 18 decimals
    amount_wei = int(amount_usdt * Decimal("1e18"))

    nonce = w3.eth.get_transaction_count(account.address, "pending")
    tx = contract.functions.transfer(to_checksum, amount_wei).build_transaction(
        {
            "chainId": 56,
            "from": account.address,
            "nonce": nonce,
            "gasPrice": w3.eth.gas_price,
            "gas": 100000,
        }
    )
    signed = w3.eth.account.sign_transaction(tx, private_key)
    raw_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hash = raw_hash.hex()
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash
    logger.info("USDT payout sent: %s USDT → %s  tx=%s", amount_usdt, to_address, tx_hash)
    return tx_hash
