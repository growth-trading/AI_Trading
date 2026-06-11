import re
import unicodedata
from decimal import Decimal, InvalidOperation


def _strip_emojis(text):
    """Remove emoji / symbol unicode characters, keep ASCII + Vietnamese."""
    result = []
    for ch in text:
        cat = unicodedata.category(ch)
        # Keep letters, numbers, punctuation, spaces
        if cat[0] in ('L', 'N', 'P', 'Z') or ch in '|.:/-+%\n':
            result.append(ch)
        else:
            result.append(' ')
    return ''.join(result)


def _price(text, pattern):
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    try:
        return Decimal(m.group(1).replace(',', '.'))
    except InvalidOperation:
        return None


def parse_signal_message(text):
    """
    Parse Telegram signal message.

    Returns one of:
        {'type': 'new_signal', 'data': {...}}
        {'type': 'tp_update',  'data': {...}}
        {'type': 'sl_hit',     'data': {...}}
        None  — not a recognized signal message
    """
    if not text:
        return None

    upper = text.upper()
    if 'RICH FOUNDATION' not in upper and 'TIN HIEU' not in upper and 'TÍN HIỆU' not in upper:
        return None

    clean = _strip_emojis(text)
    lines = [ln.strip() for ln in clean.split('\n') if ln.strip()]

    # Find the signal direction line (contains BUY or SELL)
    sig_line = None
    for ln in lines[:5]:
        if re.search(r'\b(BUY|SELL)\b', ln, re.IGNORECASE):
            sig_line = ln
            break
    if not sig_line:
        return None

    # --- TP update: "SELL TP1 | XAUUSD" ---
    tp_match = re.search(r'\b(BUY|SELL)\s+TP(\d)\b', sig_line, re.IGNORECASE)
    if tp_match:
        signal_type = tp_match.group(1).upper()
        tp_num = int(tp_match.group(2))
        sym_m = re.search(r'\|\s*([A-Z0-9]{3,10})', sig_line)
        symbol = sym_m.group(1) if sym_m else _extract_symbol(lines)
        status_map = {1: 'tp1', 2: 'tp2', 3: 'tp3', 4: 'tp4', 5: 'tp5'}
        return {
            'type': 'tp_update',
            'data': {
                'signal_type': signal_type,
                'symbol': symbol,
                'tp_num': tp_num,
                'new_status': status_map.get(tp_num, 'tp1'),
            },
        }

    # --- SL hit: "SELL SL | XAUUSD" or "SL HIT" ---
    if re.search(r'\bSL\b', sig_line, re.IGNORECASE) or 'SL HIT' in upper or 'CHẠM SL' in text.upper():
        dir_m = re.search(r'\b(BUY|SELL)\b', sig_line, re.IGNORECASE)
        signal_type = dir_m.group(1).upper() if dir_m else None
        sym_m = re.search(r'\|\s*([A-Z0-9]{3,10})', sig_line)
        symbol = sym_m.group(1) if sym_m else _extract_symbol(lines)
        return {
            'type': 'sl_hit',
            'data': {'signal_type': signal_type, 'symbol': symbol},
        }

    # --- New signal ---
    dir_m = re.search(r'\b(BUY|SELL)\b', sig_line, re.IGNORECASE)
    if not dir_m:
        return None
    signal_type = dir_m.group(1).upper()

    sym_m = re.search(r'\|\s*([A-Z0-9]{3,10})', sig_line)
    symbol = sym_m.group(1) if sym_m else _extract_symbol(lines)

    all_clean = '\n'.join(lines)

    tf_m = re.search(r'Khung\s*[:\s]+(\S+)', all_clean, re.IGNORECASE)
    timeframe = tf_m.group(1).strip('.,') if tf_m else '5m'

    entry = _price(all_clean, r'Gi[aá]\s*v[aà]o\s*[:\s]+([0-9]+[.,]?[0-9]*)')
    sl    = _price(all_clean, r'\bSL\s*[:\s]+([0-9]+[.,]?[0-9]*)')
    tp1   = _price(all_clean, r'\bTP1\s*[:\s]+([0-9]+[.,]?[0-9]*)')
    tp2   = _price(all_clean, r'\bTP2\s*[:\s]+([0-9]+[.,]?[0-9]*)')
    tp3   = _price(all_clean, r'\bTP3\s*[:\s]+([0-9]+[.,]?[0-9]*)')
    tp4   = _price(all_clean, r'\bTP4\s*[:\s]+([0-9]+[.,]?[0-9]*)')
    tp5   = _price(all_clean, r'\bTP5\s*[:\s]+([0-9]+[.,]?[0-9]*)')

    if not entry or not sl:
        return None

    return {
        'type': 'new_signal',
        'data': {
            'signal_type': signal_type,
            'symbol': symbol,
            'timeframe': timeframe,
            'entry': entry,
            'sl': sl,
            'tp1': tp1, 'tp2': tp2, 'tp3': tp3, 'tp4': tp4, 'tp5': tp5,
        },
    }


def _extract_symbol(lines):
    for ln in lines:
        m = re.search(r'\b([A-Z]{3,6}USD[A-Z]?|XAUUSD|BTCUSDT|ETHUSDT)\b', ln)
        if m:
            return m.group(1)
    return 'XAUUSD'
