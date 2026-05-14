import json
import logging
import threading
import urllib.request
from datetime import timedelta, datetime as _dt, timezone as _tz

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Global lock: chỉ 1 thread gọi MT5 cùng lúc (MT5 IPC không thread-safe)
_mt5_lock = threading.Lock()

# TTL cache (giây) theo interval — refresh trước khi nến đóng
_CACHE_TTL = {
    '1': 15, '5': 45, '15': 90, '30': 120,
    '60': 180, '120': 360, '240': 600,
    'D': 1800, 'W': 3600,
}

try:
    import MetaTrader5 as _mt5
    _HAS_MT5 = True
except ImportError:
    _mt5 = None
    _HAS_MT5 = False
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from django.conf import settings
from django.views.decorators.http import require_POST
from django.utils import timezone

from accounts.models import CustomUser
from .models import ChartAnalysisLog
from .services import fetch_chart_image, fetch_indicators, analyze_with_gemini


def landing(request):
    if request.user.is_authenticated:
        return redirect('trading')
    return render(request, 'landing/index.html')


def trading_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    plans = {
        'week':  settings.AI_PLAN_WEEK_COST,
        'month': settings.AI_PLAN_MONTH_COST,
        'year':  settings.AI_PLAN_YEAR_COST,
    }
    return render(request, 'trading/index.html', {
        'has_ai_access': user.has_ai_trading_access,
        'ai_expires_at': user.ai_trading_expires_at,
        'ai_plans': plans,
    })


_AI_PLAN_DAYS = {'week': 7, 'month': 30, 'year': 365}


@require_POST
def subscribe_ai_trading_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)

    plan = body.get('plan')
    if plan not in _AI_PLAN_DAYS:
        return JsonResponse({'error': 'Gói không hợp lệ'}, status=400)

    plan_costs = {
        'week':  settings.AI_PLAN_WEEK_COST,
        'month': settings.AI_PLAN_MONTH_COST,
        'year':  settings.AI_PLAN_YEAR_COST,
    }
    cost = plan_costs[plan]
    days = _AI_PLAN_DAYS[plan]
    now = timezone.now()

    try:
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
            if user.coins < cost:
                return JsonResponse({'error': 'Không đủ xu. Vui lòng nạp thêm.'}, status=402)

            new_expiry = (
                user.ai_trading_expires_at + timedelta(days=days)
                if user.ai_trading_expires_at and user.ai_trading_expires_at > now
                else now + timedelta(days=days)
            )
            # F() đảm bảo atomic deduction kể cả khi select_for_update là no-op (SQLite)
            CustomUser.objects.filter(pk=user.pk).update(
                coins=F('coins') - cost,
                ai_trading_expires_at=new_expiry,
            )
            user.coins -= cost
            user.ai_trading_expires_at = new_expiry

        return JsonResponse({
            'success': True,
            'expires_at': user.ai_trading_expires_at.isoformat(),
            'coins_remaining': float(user.coins),
        })
    except Exception:
        logger.exception('subscribe_ai_trading failed for user %s', request.user.pk)
        return JsonResponse({'error': 'Đăng ký thất bại, vui lòng thử lại.'}, status=500)


@require_POST
def analyze_chart_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)
    if not request.user.has_ai_trading_access:
        return JsonResponse({'error': 'Bạn chưa mua gói AI Trading'}, status=403)

    # Rate-limit: tối đa 5 lần phân tích / phút / user
    rate_key = f'ai:analyze:rate:{request.user.pk}'
    rate_count = cache.get(rate_key, 0)
    if rate_count >= 5:
        return JsonResponse({'error': 'Bạn đang phân tích quá nhanh. Vui lòng chờ 1 phút.'}, status=429)
    cache.set(rate_key, rate_count + 1, 60)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)

    symbol        = body.get('symbol', 'OANDA:XAUUSD').strip()
    interval      = body.get('interval', '60').strip()
    current_price = body.get('current_price')

    try:
        image_bytes = fetch_chart_image(symbol, interval)
        indicators  = fetch_indicators(symbol, interval)
        result      = analyze_with_gemini(image_bytes, indicators, symbol, interval,
                                          current_price=current_price)

        ChartAnalysisLog.objects.create(
            user=request.user,
            symbol=symbol,
            interval=interval,
            **result,
        )

        return JsonResponse({'success': True, 'data': result})

    except Exception:
        logger.exception('analyze_chart failed for user %s symbol %s', request.user.pk, symbol)
        return JsonResponse({'error': 'Phân tích thất bại, vui lòng thử lại.'}, status=500)


_MT5_SYMBOLS = {
    'OANDA:XAUUSD': 'XAUUSD',
    'OANDA:XAGUSD': 'XAGUSD',
    'OANDA:EURUSD': 'EURUSD',
    'OANDA:GBPUSD': 'GBPUSD',
    'OANDA:USDJPY': 'USDJPY',
    'NASDAQ:AAPL':  'AAPL',
    'NASDAQ:TSLA':  'TSLA',
}

_mt5_symbol_cache = {}

def _mt5_resolve_symbol(base):
    if base in _mt5_symbol_cache:
        return _mt5_symbol_cache[base]
    for suffix in ('', 'm', '.', 'pro', 'c', 'n'):
        name = base + suffix
        if _mt5.symbol_info(name) is not None:
            _mt5_symbol_cache[base] = name
            _mt5.symbol_select(name, True)
            return name
    return base

_BINANCE_INTERVAL = {
    '1': '1m', '5': '5m', '15': '15m', '30': '30m',
    '60': '1h', '120': '2h', '240': '4h', 'D': '1d', 'W': '1w',
}


def _mt5_connect():
    if not _HAS_MT5:
        return False
    if not _mt5.initialize():
        return False
    # Nếu terminal đã login sẵn thì dùng luôn
    if _mt5.account_info() is not None:
        return True
    # Thử login bằng credentials trong .env
    account  = settings.MT5_ACCOUNT
    password = settings.MT5_PASSWORD
    server   = settings.MT5_SERVER
    if account and password and server:
        return _mt5.login(int(account), password=password, server=server)
    return False


def _interval_secs(iv):
    if iv == 'D': return 86400
    if iv == 'W': return 604800
    try: return int(iv) * 60
    except: return 3600

_MT5_TF = None

def _get_mt5_tf():
    global _MT5_TF
    if _MT5_TF is None and _HAS_MT5:
        _MT5_TF = {
            '1': _mt5.TIMEFRAME_M1,  '5': _mt5.TIMEFRAME_M5,
            '15': _mt5.TIMEFRAME_M15, '30': _mt5.TIMEFRAME_M30,
            '60': _mt5.TIMEFRAME_H1,  '120': _mt5.TIMEFRAME_H2,
            '240': _mt5.TIMEFRAME_H4, 'D': _mt5.TIMEFRAME_D1,
            'W': _mt5.TIMEFRAME_W1,
        }
    return _MT5_TF or {}



def _rates_to_candles(rates):
    return [
        {
            'time':  int(r['time']),
            'open':  round(float(r['open']),  6),
            'high':  round(float(r['high']),  6),
            'low':   round(float(r['low']),   6),
            'close': round(float(r['close']), 6),
        }
        for r in rates
    ]


def chart_data_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    symbol    = request.GET.get('symbol', 'OANDA:XAUUSD').strip()
    interval  = request.GET.get('interval', '60').strip()
    since_raw  = request.GET.get('since')
    before_raw = request.GET.get('before')

    try:
        since_ts  = int(float(since_raw))  if since_raw  else None
        before_ts = int(float(before_raw)) if before_raw else None
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Tham số không hợp lệ'}, status=400)

    try:
        if symbol.startswith('BINANCE:'):
            candles = _binance_candles(symbol, interval, since_ts, before_ts)
        else:
            candles = _mt5_candles(symbol, interval, since_ts, before_ts)

        return JsonResponse({'success': True, 'candles': candles})

    except _MT5Unavailable as e:
        return JsonResponse({'error': str(e)}, status=503)
    except Exception:
        logger.exception('chart_data failed for user %s symbol %s', request.user.pk, symbol)
        return JsonResponse({'error': 'Không thể tải dữ liệu biểu đồ, vui lòng thử lại.'}, status=500)


class _MT5Unavailable(Exception):
    pass


def _binance_candles(symbol, interval, since_ts, before_ts):
    ticker = symbol.split(':', 1)[1]
    bi = _BINANCE_INTERVAL.get(interval, '1h')

    # Cache chỉ cho request latest (không since/before)
    if not since_ts and not before_ts:
        ck = f'binance:candles:{symbol}:{interval}'
        cached = cache.get(ck)
        if cached is not None:
            return cached

    if since_ts:
        url = (f'https://api.binance.com/api/v3/klines?symbol={ticker}'
               f'&interval={bi}&startTime={since_ts * 1000}&limit=10')
    elif before_ts:
        url = (f'https://api.binance.com/api/v3/klines?symbol={ticker}'
               f'&interval={bi}&endTime={before_ts * 1000 - 1}&limit=150')
    else:
        url = f'https://api.binance.com/api/v3/klines?symbol={ticker}&interval={bi}&limit=150'

    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    candles = [
        {'time': int(d[0]) // 1000, 'open': float(d[1]),
         'high': float(d[2]), 'low': float(d[3]), 'close': float(d[4])}
        for d in data
    ]

    if not since_ts and not before_ts:
        cache.set(ck, candles, _CACHE_TTL.get(interval, 180))

    return candles


def _mt5_candles(symbol, interval, since_ts, before_ts):
    # Dữ liệu lịch sử (before_ts): cache dài vì không thay đổi
    if before_ts:
        hist_key = f'mt5:hist:{symbol}:{interval}:{before_ts}'
        cached = cache.get(hist_key)
        if cached is not None:
            return cached

    # Dữ liệu mới nhất: cache ngắn, kiểm tra trước khi lock
    latest_key = None
    if not since_ts and not before_ts:
        latest_key = f'mt5:candles:{symbol}:{interval}'
        cached = cache.get(latest_key)
        if cached is not None:
            return cached

    # Cache miss — cần gọi MT5, dùng lock để tránh thundering herd
    with _mt5_lock:
        # Double-check sau khi có lock
        if latest_key:
            cached = cache.get(latest_key)
            if cached is not None:
                return cached

        if not _mt5_connect():
            err = _mt5.last_error() if _HAS_MT5 else 'MT5 not installed'
            raise _MT5Unavailable(f'MT5 không khả dụng: {err}')

        mt5_base = _MT5_SYMBOLS.get(symbol, symbol.split(':')[-1])
        mt5_sym  = _mt5_resolve_symbol(mt5_base)
        tf       = _get_mt5_tf().get(interval, _mt5.TIMEFRAME_H1)
        logger.info('mt5_candles: sym=%s tf=%s since=%s before=%s', mt5_sym, tf, since_ts, before_ts)

        if since_ts:
            date_from = _dt.fromtimestamp(since_ts, tz=_tz.utc)
            rates = _mt5.copy_rates_range(mt5_sym, tf, date_from, _dt.now(_tz.utc))
        elif before_ts:
            date_to   = _dt.fromtimestamp(before_ts - 1, tz=_tz.utc)
            date_from = date_to - timedelta(seconds=151 * _interval_secs(interval))
            rates = _mt5.copy_rates_range(mt5_sym, tf, date_from, date_to)
        else:
            rates = _mt5.copy_rates_from_pos(mt5_sym, tf, 0, 150)

        logger.info('mt5_candles: rates=%s err=%s', rates is not None and len(rates), _mt5.last_error())

        if rates is None or len(rates) == 0:
            if before_ts:
                cache.set(f'mt5:hist:{symbol}:{interval}:{before_ts}', [], 600)
                return []
            raise _MT5Unavailable(f'MT5 không có dữ liệu: {_mt5.last_error()}')

        candles = _rates_to_candles(rates)

        if before_ts:
            cache.set(f'mt5:hist:{symbol}:{interval}:{before_ts}', candles, 600)
        elif latest_key:
            ttl = _CACHE_TTL.get(interval, 180)
            cache.set(latest_key, candles, ttl)
            # Cập nhật tick cùng lúc
            cache.set(f'mt5:tick:{symbol}:{interval}', candles[-1], max(5, ttl // 3))

        return candles


def tick_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    symbol   = request.GET.get('symbol', 'OANDA:XAUUSD').strip()
    interval = request.GET.get('interval', '60').strip()

    try:
        if symbol.startswith('BINANCE:'):
            # Cache 3s để giảm tải Binance API khi nhiều user poll đồng thời
            tick_cache_key = f'binance:tick:{symbol}:{interval}'
            candle = cache.get(tick_cache_key)
            if candle is None:
                ticker = symbol.split(':', 1)[1]
                bi  = _BINANCE_INTERVAL.get(interval, '1h')
                url = f'https://api.binance.com/api/v3/klines?symbol={ticker}&interval={bi}&limit=1'
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as r:
                    d = json.loads(r.read())[0]
                candle = {
                    'time': int(d[0]) // 1000, 'open': float(d[1]),
                    'high': float(d[2]), 'low': float(d[3]), 'close': float(d[4]),
                }
                cache.set(tick_cache_key, candle, 3)
        else:
            tick_key = f'mt5:tick:{symbol}:{interval}'
            cached = cache.get(tick_key)
            if cached is not None:
                return JsonResponse({'success': True, 'candle': cached})

            with _mt5_lock:
                cached = cache.get(tick_key)
                if cached is not None:
                    return JsonResponse({'success': True, 'candle': cached})

                if not _mt5_connect():
                    logger.warning('tick: MT5 connect failed, err=%s', _mt5.last_error() if _HAS_MT5 else 'no MT5')
                    return JsonResponse({'error': 'MT5 không khả dụng'}, status=503)

                mt5_base = _MT5_SYMBOLS.get(symbol, symbol.split(':')[-1])
                mt5_sym  = _mt5_resolve_symbol(mt5_base)
                tf       = _get_mt5_tf().get(interval, _mt5.TIMEFRAME_H1)
                rates    = _mt5.copy_rates_from_pos(mt5_sym, tf, 0, 1)
                if rates is None or len(rates) == 0:
                    return JsonResponse({'error': 'MT5 không có dữ liệu cho symbol này'}, status=503)
                r = rates[0]
                candle = {
                    'time':  int(r['time']),
                    'open':  round(float(r['open']),  6),
                    'high':  round(float(r['high']),  6),
                    'low':   round(float(r['low']),   6),
                    'close': round(float(r['close']), 6),
                }
                ttl = max(5, _CACHE_TTL.get(interval, 60) // 3)
                cache.set(tick_key, candle, ttl)

        return JsonResponse({'success': True, 'candle': candle})

    except Exception:
        logger.exception('tick_view failed for user %s symbol %s', request.user.pk, symbol)
        return JsonResponse({'error': 'Không thể tải dữ liệu, vui lòng thử lại.'}, status=500)
