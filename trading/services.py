import json
import re
import base64
import logging
from decimal import Decimal, InvalidOperation
import pandas as pd
import pandas_ta  # noqa: F401  # registers df.ta accessor on pandas DataFrame
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

_GEMINI_CONFIGURED = False


def _strip_exchange(symbol: str) -> str:
    return symbol.split(':', 1)[1] if ':' in symbol else symbol


def compute_indicators_local(candles: list) -> dict:
    """Tính RSI/MACD/EMA/Supertrend từ OHLCV cục bộ — không gọi API ngoài."""
    if len(candles) < 60:
        logger.warning('compute_indicators_local: chỉ có %d nến, cần >= 60; bỏ qua indicator', len(candles))
        return {}

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
            logger.error('compute_indicators_local: tất cả indicator đều None — có thể lỗi pandas_ta. Columns: %s', list(df.columns))
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
