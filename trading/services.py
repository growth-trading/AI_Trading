import json
import re
import base64
import logging
from decimal import Decimal, InvalidOperation
import pandas as pd
import ta as ta_lib
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

_GEMINI_CONFIGURED = False


def _strip_exchange(symbol: str) -> str:
    return symbol.split(':', 1)[1] if ':' in symbol else symbol


def _supertrend(df: pd.DataFrame, length: int = 10, multiplier: float = 3.0):
    high, low, close = df['high'], df['low'], df['close']
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    hl2 = (high + low) / 2
    upper = (hl2 + multiplier * atr).values.copy()
    lower = (hl2 - multiplier * atr).values.copy()
    close_vals = close.values
    n = len(df)
    supert = [float('nan')] * n
    direction = [float('nan')] * n
    for i in range(1, n):
        upper[i] = upper[i] if (upper[i] < upper[i - 1] or close_vals[i - 1] > upper[i - 1]) else upper[i - 1]
        lower[i] = lower[i] if (lower[i] > lower[i - 1] or close_vals[i - 1] < lower[i - 1]) else lower[i - 1]
        prev = supert[i - 1]
        is_nan = prev != prev
        if is_nan or prev == upper[i - 1]:
            supert[i], direction[i] = (lower[i], 1) if close_vals[i] > upper[i] else (upper[i], -1)
        else:
            supert[i], direction[i] = (upper[i], -1) if close_vals[i] < lower[i] else (lower[i], 1)
    return pd.Series(supert, index=df.index), pd.Series(direction, index=df.index)


def compute_indicators_local(candles: list) -> dict:
    """Tính RSI/MACD/EMA/Supertrend từ OHLCV cục bộ — không gọi API ngoài."""
    if len(candles) < 60:
        logger.warning('compute_indicators_local: chỉ có %d nến, cần >= 60; bỏ qua indicator', len(candles))
        return {}

    try:
        df = pd.DataFrame(candles)[['open', 'high', 'low', 'close']].astype(float)
        result = {}

        rsi_val = ta_lib.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
        if pd.notna(rsi_val):
            result['rsi'] = {'value': float(rsi_val)}

        macd_obj = ta_lib.trend.MACD(df['close'], window_fast=12, window_slow=26, window_sign=9)
        macd_val = macd_obj.macd().iloc[-1]
        if pd.notna(macd_val):
            result['macd'] = {
                'valueMACD':       float(macd_val),
                'valueMACDSignal': float(macd_obj.macd_signal().iloc[-1]),
                'valueMACDHist':   float(macd_obj.macd_diff().iloc[-1]),
            }

        ema20_val = ta_lib.trend.EMAIndicator(df['close'], window=20).ema_indicator().iloc[-1]
        if pd.notna(ema20_val):
            result['ema20'] = {'value': float(ema20_val)}

        ema50_val = ta_lib.trend.EMAIndicator(df['close'], window=50).ema_indicator().iloc[-1]
        if pd.notna(ema50_val):
            result['ema50'] = {'value': float(ema50_val)}

        st_val, st_dir = _supertrend(df, length=10, multiplier=3.0)
        last_st, last_dir = st_val.iloc[-1], st_dir.iloc[-1]
        if pd.notna(last_st):
            result['supertrend'] = {
                'value':       float(last_st),
                'valueAdvice': 'long' if (last_dir or 0) > 0 else 'short',
            }

        if not result:
            logger.error('compute_indicators_local: tất cả indicator đều None')
            return {}
        return result

    except Exception:
        logger.exception('compute_indicators_local thất bại')
        return {}




def analyze_with_gemini(image_bytes: bytes, indicators: dict, symbol: str, interval: str,
                        current_price=None, lang: str = 'vi', image_mime: str = 'image/png') -> dict:
    """Gọi Gemini 2.5 Flash Vision, trả về dict tín hiệu."""
    global _GEMINI_CONFIGURED
    if not _GEMINI_CONFIGURED:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _GEMINI_CONFIGURED = True
    model = genai.GenerativeModel('gemini-2.5-flash')

    clean_symbol = _strip_exchange(symbol)
    tv_interval_label = {
        '1': 'M1', '5': 'M5', '15': 'M15', '30': 'M30',
        '60': 'H1', '120': 'H2', '240': 'H4',
        'D': 'D1', 'W': 'W1',
    }.get(interval, interval)

    indicator_text = _format_indicators(indicators)

    if lang == 'en':
        price_line = f'\nCurrent price: {current_price}' if current_price else ''
        lang_instruction = 'Write the reasoning in English.'
        reasoning_hint = '2-3 sentence explanation in English based on chart pattern and indicators'
    else:
        price_line = f'\nGiá hiện tại: {current_price}' if current_price else ''
        lang_instruction = 'Viết reasoning bằng tiếng Việt.'
        reasoning_hint = 'chuỗi giải thích ngắn gọn 2-3 câu bằng tiếng Việt dựa trên pattern chart và indicator'

    prompt = f"""Bạn là chuyên gia phân tích kỹ thuật trading. Hãy phân tích biểu đồ {clean_symbol} khung {tv_interval_label}.{price_line}

Dữ liệu indicator chính xác từ hệ thống:
{indicator_text}

Nhìn vào biểu đồ và kết hợp với các chỉ số trên, hãy đưa ra phân tích và tín hiệu giao dịch. Entry/SL/TP phải sát với giá hiện tại.

Trả về JSON hợp lệ (không có markdown, không có text thừa) theo đúng format sau:
{{
  "signal": "BUY" hoặc "SELL" hoặc "HOLD",
  "confidence": số nguyên 0-100 (% độ tin cậy),
  "entry": số thực (giá vào lệnh đề xuất, null nếu HOLD),
  "sl": số thực (stop loss, null nếu HOLD),
  "tp": số thực (take profit, null nếu HOLD),
  "reasoning": "{reasoning_hint}"
}}
{lang_instruction}"""

    image_part = {
        'mime_type': image_mime,
        'data': base64.b64encode(image_bytes).decode('utf-8'),
    }

    try:
        response = model.generate_content([prompt, image_part])
    except Exception as e:
        err_str = str(e)
        if 'ResourceExhausted' in type(e).__name__ or 'quota' in err_str.lower() or '429' in err_str:
            raise RuntimeError('Gemini đang quá tải, vui lòng thử lại sau ít phút.') from e
        raise

    try:
        raw = response.text.strip()
    except (ValueError, AttributeError, IndexError) as e:
        logger.warning('Gemini response unavailable for %s: %s', symbol, e)
        raise RuntimeError('Gemini response blocked or empty')

    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning('Gemini returned non-JSON for %s: %.200s', symbol, raw)
        raise RuntimeError('Gemini returned non-JSON response')

    def _safe_confidence(v):
        try:
            return max(0, min(100, int(float(str(v).rstrip('%').strip()))))
        except (TypeError, ValueError):
            return 0

    return {
        'signal': str(data.get('signal', 'HOLD')).upper(),
        'confidence': _safe_confidence(data.get('confidence', 0)),
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
        if m.get('valueMACD') is not None:
            parts = [f"value={_safe_num(m.get('valueMACD'), '.4f')}"]
            if m.get('valueMACDSignal') is not None:
                parts.append(f"signal={_safe_num(m.get('valueMACDSignal'), '.4f')}")
            if m.get('valueMACDHist') is not None:
                parts.append(f"hist={_safe_num(m.get('valueMACDHist'), '.4f')}")
            lines.append(f"- MACD: {', '.join(parts)}")
    if 'ema20' in indicators:
        lines.append(f"- EMA(20): {_safe_num(indicators['ema20'].get('value'), '.4f')}")
    if 'ema50' in indicators:
        lines.append(f"- EMA(50): {_safe_num(indicators['ema50'].get('value'), '.4f')}")
    if 'supertrend' in indicators:
        st = indicators['supertrend']
        if st.get('value') is not None:
            lines.append(
                f"- Supertrend: value={_safe_num(st.get('value'), '.4f')}, "
                f"trend={'UP' if st.get('valueAdvice') == 'long' else 'DOWN'}"
            )
    return '\n'.join(lines) if lines else '(Không có dữ liệu indicator)'


def _to_decimal_or_none(val):
    if val is None:
        return None
    try:
        d = Decimal(str(val))
        return d if d.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None
