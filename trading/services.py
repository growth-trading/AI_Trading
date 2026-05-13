import json
import base64
import requests
import google.generativeai as genai
from django.conf import settings

# TradingView interval → TAAPI interval
_INTERVAL_MAP = {
    '1': '1m', '5': '5m', '15': '15m', '30': '30m',
    '60': '1h', '120': '2h', '240': '4h',
    'D': '1d', 'W': '1w',
}

# TradingView interval → Chart-IMG interval
_CHART_IMG_INTERVAL_MAP = {
    '1': '1m', '5': '5m', '15': '15m', '30': '30m',
    '60': '1h', '120': '2h', '240': '4h',
    'D': '1D', 'W': '1W',
}


def _strip_exchange(symbol: str) -> str:
    """'OANDA:XAUUSD' → 'XAUUSD'"""
    return symbol.split(':')[1] if ':' in symbol else symbol


def _get_exchange(symbol: str) -> str:
    """'BINANCE:BTCUSDT' → 'binance', 'OANDA:XAUUSD' → 'oanda'"""
    if ':' not in symbol:
        return 'binance'
    return symbol.split(':')[0].lower()


def fetch_chart_image(symbol: str, interval: str) -> bytes:
    """Gọi Chart-IMG API, trả về ảnh PNG dạng bytes."""
    chart_interval = _CHART_IMG_INTERVAL_MAP.get(interval, '1h')
    resp = requests.get(
        'https://api.chart-img.com/v2/tradingview/advanced-chart',
        params={
            'symbol': symbol,
            'interval': chart_interval,
            'theme': 'dark',
            'width': 1280,
            'height': 720,
            'key': settings.CHART_IMG_API_KEY,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content


def fetch_indicators(symbol: str, interval: str) -> dict:
    """Gọi TAAPI.io bulk endpoint, trả về dict các indicator."""
    taapi_interval = _INTERVAL_MAP.get(interval, '1h')
    exchange = _get_exchange(symbol)
    clean_symbol = _strip_exchange(symbol)

    # TAAPI dùng format "BTC/USDT" cho crypto, "XAU/USD" cho metals
    if '/' not in clean_symbol and len(clean_symbol) > 5:
        # e.g. BTCUSDT → BTC/USDT (best effort)
        taapi_symbol = clean_symbol[:-4] + '/' + clean_symbol[-4:]
    elif len(clean_symbol) == 6 and clean_symbol.isalpha():
        # e.g. XAUUSD → XAU/USD
        taapi_symbol = clean_symbol[:3] + '/' + clean_symbol[3:]
    else:
        taapi_symbol = clean_symbol

    payload = {
        'secret': settings.TAAPI_API_KEY,
        'construct': {
            'exchange': exchange,
            'symbol': taapi_symbol,
            'interval': taapi_interval,
            'indicators': [
                {'id': 'rsi', 'indicator': 'rsi'},
                {'id': 'macd', 'indicator': 'macd'},
                {'id': 'ema20', 'indicator': 'ema', 'optInTimePeriod': 20},
                {'id': 'ema50', 'indicator': 'ema', 'optInTimePeriod': 50},
                {'id': 'supertrend', 'indicator': 'supertrend'},
            ],
        },
    }

    resp = requests.post('https://api.taapi.io/bulk', json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    result = {}
    for item in data.get('data', []):
        iid = item.get('id')
        val = item.get('result', {})
        result[iid] = val
    return result


def analyze_with_gemini(image_bytes: bytes, indicators: dict, symbol: str, interval: str) -> dict:
    """Gọi Gemini 2.5 Flash Vision, trả về dict tín hiệu."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

    clean_symbol = _strip_exchange(symbol)
    tv_interval_label = {
        '1': '1 phút', '5': '5 phút', '15': '15 phút', '30': '30 phút',
        '60': '1 giờ', '120': '2 giờ', '240': '4 giờ',
        'D': '1 ngày', 'W': '1 tuần',
    }.get(interval, interval)

    indicator_text = _format_indicators(indicators)

    prompt = f"""Bạn là chuyên gia phân tích kỹ thuật trading. Hãy phân tích biểu đồ {clean_symbol} khung {tv_interval_label}.

Dữ liệu indicator chính xác từ hệ thống:
{indicator_text}

Nhìn vào biểu đồ và kết hợp với các chỉ số trên, hãy đưa ra phân tích và tín hiệu giao dịch.

Trả về JSON hợp lệ (không có markdown, không có text thừa) theo đúng format sau:
{{
  "signal": "BUY" hoặc "SELL" hoặc "HOLD",
  "confidence": số nguyên 0-100 (% độ tin cậy),
  "entry": số thực (giá vào lệnh đề xuất, null nếu HOLD),
  "sl": số thực (stop loss, null nếu HOLD),
  "tp": số thực (take profit, null nếu HOLD),
  "reasoning": "chuỗi giải thích ngắn gọn 2-3 câu dựa trên pattern chart và indicator"
}}"""

    image_part = {
        'mime_type': 'image/png',
        'data': base64.b64encode(image_bytes).decode('utf-8'),
    }

    response = model.generate_content([prompt, image_part])
    raw = response.text.strip()

    # Strip markdown code block nếu có
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)

    return {
        'signal': str(data.get('signal', 'HOLD')).upper(),
        'confidence': int(data.get('confidence', 0)),
        'entry': _to_decimal_or_none(data.get('entry')),
        'sl': _to_decimal_or_none(data.get('sl')),
        'tp': _to_decimal_or_none(data.get('tp')),
        'reasoning': str(data.get('reasoning', '')),
    }


def _format_indicators(indicators: dict) -> str:
    lines = []
    if 'rsi' in indicators:
        lines.append(f"- RSI(14): {indicators['rsi'].get('value', 'N/A'):.2f}")
    if 'macd' in indicators:
        m = indicators['macd']
        lines.append(
            f"- MACD: value={m.get('valueMACD', 'N/A'):.4f}, "
            f"signal={m.get('valueMACDSignal', 'N/A'):.4f}, "
            f"hist={m.get('valueMACDHist', 'N/A'):.4f}"
        )
    if 'ema20' in indicators:
        lines.append(f"- EMA(20): {indicators['ema20'].get('value', 'N/A'):.4f}")
    if 'ema50' in indicators:
        lines.append(f"- EMA(50): {indicators['ema50'].get('value', 'N/A'):.4f}")
    if 'supertrend' in indicators:
        st = indicators['supertrend']
        lines.append(
            f"- Supertrend: value={st.get('value', 'N/A'):.4f}, "
            f"trend={'UP' if st.get('valueAdvice') == 'long' else 'DOWN'}"
        )
    return '\n'.join(lines) if lines else '(Không có dữ liệu indicator)'


def _to_decimal_or_none(val):
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None
