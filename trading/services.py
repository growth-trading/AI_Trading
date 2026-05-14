import json
import base64
import requests
import google.generativeai as genai
from django.conf import settings

_DEMO_KEYS = {'your_gemini_api_key', 'your_taapi_api_key', 'your_chart_img_api_key', ''}

# 1×1 transparent PNG (fallback image for demo mode)
_EMPTY_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f'
    b'\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)

def _mock_indicators() -> dict:
    return {
        'rsi':        {'value': 58.4},
        'macd':       {'valueMACD': 12.5, 'valueMACDSignal': 9.3, 'valueMACDHist': 3.2},
        'ema20':      {'value': 3288.50},
        'ema50':      {'value': 3241.00},
        'supertrend': {'value': 3265.00, 'valueAdvice': 'long'},
    }

def _mock_levels(price: float, signal: str) -> tuple:
    """Tính entry/SL/TP tương đối theo giá thực."""
    p = float(price)
    if signal == 'BUY':
        return round(p, 5), round(p * 0.9940, 5), round(p * 1.0150, 5)
    else:  # SELL
        return round(p, 5), round(p * 1.0060, 5), round(p * 0.9850, 5)


def _mock_analysis(symbol: str, current_price=None) -> dict:
    clean = _strip_exchange(symbol)
    price = float(current_price) if current_price else None

    if 'XAU' in clean:
        sig = 'BUY'
        e, sl, tp = _mock_levels(price, sig) if price else (3318.50, 3295.00, 3368.00)
        return {
            'signal': sig, 'confidence': 74, 'entry': e, 'sl': sl, 'tp': tp,
            'reasoning': (
                '[DEMO] RSI (58.4) đang tăng, MACD histogram dương (+3.2) xác nhận đà bullish. '
                'EMA20 nằm trên EMA50 cho thấy xu hướng tăng ngắn hạn còn duy trì. '
                'Supertrend UP — vào BUY gần vùng hỗ trợ EMA20 với R:R ≈ 2.5.'
            ),
        }
    if 'XAG' in clean:
        sig = 'BUY'
        e, sl, tp = _mock_levels(price, sig) if price else (32.85, 32.20, 34.20)
        return {
            'signal': sig, 'confidence': 61, 'entry': e, 'sl': sl, 'tp': tp,
            'reasoning': (
                '[DEMO] Bạc hình thành đáy cao hơn trên khung H1. RSI phân kỳ tăng. '
                'MACD vừa cắt lên trên đường signal. Vào BUY với SL dưới vùng hỗ trợ gần nhất.'
            ),
        }
    if 'EUR' in clean:
        sig = 'SELL'
        e, sl, tp = _mock_levels(price, sig) if price else (1.0842, 1.0890, 1.0755)
        return {
            'signal': sig, 'confidence': 68, 'entry': e, 'sl': sl, 'tp': tp,
            'reasoning': (
                '[DEMO] EURUSD phá vỡ hỗ trợ trendline tăng. RSI (42) cho thấy áp lực bán. '
                'MACD histogram âm và mở rộng. Mục tiêu vùng hỗ trợ phía dưới.'
            ),
        }
    if 'GBP' in clean:
        sig = 'SELL'
        e, sl, tp = _mock_levels(price, sig) if price else (1.2650, 1.2710, 1.2520)
        return {
            'signal': sig, 'confidence': 62, 'entry': e, 'sl': sl, 'tp': tp,
            'reasoning': (
                '[DEMO] GBPUSD chạm kháng cự vùng 1.2700. RSI overbought (68). '
                'Nến rejection xuất hiện, MACD bắt đầu phân kỳ âm.'
            ),
        }
    if 'BTC' in clean:
        sig = 'BUY'
        e, sl, tp = _mock_levels(price, sig) if price else (103_200.0, 101_000.0, 108_500.0)
        return {
            'signal': sig, 'confidence': 66, 'entry': e, 'sl': sl, 'tp': tp,
            'reasoning': (
                '[DEMO] BTC tích lũy sideway, RSI 55 cho thấy còn room tăng. '
                'Volume nến xanh áp đảo. Supertrend UP kể từ 3 nến trước.'
            ),
        }
    if 'ETH' in clean:
        sig = 'BUY'
        e, sl, tp = _mock_levels(price, sig) if price else (2450.0, 2380.0, 2600.0)
        return {
            'signal': sig, 'confidence': 58, 'entry': e, 'sl': sl, 'tp': tp,
            'reasoning': (
                '[DEMO] ETH đang trong uptrend ngắn hạn. EMA20 hỗ trợ tốt. '
                'RSI (54) chưa overbought, còn dư địa tăng lên vùng kháng cự tiếp theo.'
            ),
        }
    return {
        'signal': 'HOLD', 'confidence': 48,
        'entry': None, 'sl': None, 'tp': None,
        'reasoning': (
            '[DEMO] Tín hiệu hiện tại chưa rõ ràng. RSI ở vùng trung tính (50±5), '
            'MACD chưa có giao cắt xác nhận. Chờ breakout rõ ràng trước khi vào lệnh.'
        ),
    }

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
    if settings.CHART_IMG_API_KEY in _DEMO_KEYS:
        return _EMPTY_PNG
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
    if settings.TAAPI_API_KEY in _DEMO_KEYS:
        return _mock_indicators()
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


def analyze_with_gemini(image_bytes: bytes, indicators: dict, symbol: str, interval: str,
                        current_price=None) -> dict:
    """Gọi Gemini 2.5 Flash Vision, trả về dict tín hiệu."""
    if settings.GEMINI_API_KEY in _DEMO_KEYS:
        return _mock_analysis(symbol, current_price=current_price)
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

    clean_symbol = _strip_exchange(symbol)
    tv_interval_label = {
        '1': 'M1', '5': 'M5', '15': 'M15', '30': 'M30',
        '60': 'H1', '120': 'H2', '240': 'H4',
        'D': 'D1', 'W': 'W1',
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
