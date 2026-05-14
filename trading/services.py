import json
import re
import base64
import logging
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_DEMO_KEYS = {'your_gemini_api_key', ''}

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

def _strip_exchange(symbol: str) -> str:
    return symbol.split(':')[1] if ':' in symbol else symbol


def compute_indicators_local(candles: list) -> dict:
    """Tính RSI/MACD/EMA/Supertrend từ OHLCV cục bộ — không gọi API ngoài."""
    if len(candles) < 60:
        logger.warning('compute_indicators_local: chỉ có %d nến, cần >= 60', len(candles))
        return _mock_indicators()

    try:
        df = pd.DataFrame(candles)[['open', 'high', 'low', 'close']].astype(float)

        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.ema(length=20, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.supertrend(length=10, multiplier=3.0, append=True)

        last = df.iloc[-1]

        def _v(col):
            val = last.get(col)
            return float(val) if val is not None and pd.notna(val) else None

        result = {}

        rsi = _v('RSI_14')
        if rsi is not None:
            result['rsi'] = {'value': rsi}

        macd = _v('MACD_12_26_9')
        if macd is not None:
            result['macd'] = {
                'valueMACD':       macd,
                'valueMACDSignal': _v('MACDs_12_26_9'),
                'valueMACDHist':   _v('MACDh_12_26_9'),
            }

        ema20 = _v('EMA_20')
        if ema20 is not None:
            result['ema20'] = {'value': ema20}

        ema50 = _v('EMA_50')
        if ema50 is not None:
            result['ema50'] = {'value': ema50}

        st_cols     = [c for c in df.columns if re.match(r'^SUPERT_\d', c)]
        st_dir_cols = [c for c in df.columns if re.match(r'^SUPERTd_\d', c)]
        if st_cols and st_dir_cols:
            st_val = _v(st_cols[0])
            st_dir = _v(st_dir_cols[0])
            if st_val is not None:
                result['supertrend'] = {
                    'value':       st_val,
                    'valueAdvice': 'long' if (st_dir or 0) > 0 else 'short',
                }

        if not result:
            logger.warning('compute_indicators_local: tất cả indicator đều None. Columns: %s', list(df.columns))
            return _mock_indicators()
        return result

    except Exception:
        logger.exception('compute_indicators_local thất bại, dùng mock')
        return _mock_indicators()




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

    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
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


def _safe_num(val, fmt='.2f') -> str:
    """Format số an toàn — trả 'N/A' nếu không convert được."""
    try:
        return format(float(val), fmt)
    except (TypeError, ValueError):
        return 'N/A'


def _format_indicators(indicators: dict) -> str:
    lines = []
    if 'rsi' in indicators:
        lines.append(f"- RSI(14): {_safe_num(indicators['rsi'].get('value'))}")
    if 'macd' in indicators:
        m = indicators['macd']
        lines.append(
            f"- MACD: value={_safe_num(m.get('valueMACD'), '.4f')}, "
            f"signal={_safe_num(m.get('valueMACDSignal'), '.4f')}, "
            f"hist={_safe_num(m.get('valueMACDHist'), '.4f')}"
        )
    if 'ema20' in indicators:
        lines.append(f"- EMA(20): {_safe_num(indicators['ema20'].get('value'), '.4f')}")
    if 'ema50' in indicators:
        lines.append(f"- EMA(50): {_safe_num(indicators['ema50'].get('value'), '.4f')}")
    if 'supertrend' in indicators:
        st = indicators['supertrend']
        lines.append(
            f"- Supertrend: value={_safe_num(st.get('value'), '.4f')}, "
            f"trend={'UP' if st.get('valueAdvice') == 'long' else 'DOWN'}"
        )
    return '\n'.join(lines) if lines else '(Không có dữ liệu indicator)'


def _to_decimal_or_none(val):
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None
