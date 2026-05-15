import base64
import binascii
import json
import logging
import re
import threading
import urllib.parse
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

from django.shortcuts import get_object_or_404
from accounts.models import CustomUser
from .models import ChartAnalysisLog, TradingViewProduct, UserTVSubscription
from .services import compute_indicators_local, analyze_with_gemini

# 1×1 transparent PNG — dùng khi canvas capture thất bại
_PNG_FALLBACK = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f'
    b'\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)


def landing(request):
    if request.user.is_authenticated:
        return redirect('trading')
    return render(request, 'landing/index.html')


def tradingview_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.is_email_verified:
        return redirect('verify_otp')

    now = timezone.now()
    products = TradingViewProduct.objects.filter(is_active=True)

    active_subs = {
        sub.product_id: sub
        for sub in UserTVSubscription.objects.filter(
            user=request.user,
            expires_at__gt=now,
        ).select_related('product')
    }

    product_list = [
        {
            'product': p,
            'subscription': active_subs.get(p.pk),
            'has_access': p.pk in active_subs,
        }
        for p in products
    ]

    return render(request, 'trading/tradingview.html', {
        'product_list': product_list,
    })



_TV_PLAN_DAYS = {'week': 7, 'month': 30, 'year': 365}


@require_POST
def subscribe_tradingview_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)

    plan = body.get('plan')
    product_slug = body.get('product_slug', '')

    if plan not in _TV_PLAN_DAYS:
        return JsonResponse({'error': 'Gói không hợp lệ'}, status=400)

    try:
        product = TradingViewProduct.objects.get(slug=product_slug, is_active=True)
    except TradingViewProduct.DoesNotExist:
        return JsonResponse({'error': 'Sản phẩm không tồn tại'}, status=404)

    cost = getattr(product, f'{plan}_cost')
    days = _TV_PLAN_DAYS[plan]
    now = timezone.now()

    try:
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
            if user.coins < cost:
                return JsonResponse({'error': 'Không đủ xu. Vui lòng nạp thêm.'}, status=402)

            sub, _ = UserTVSubscription.objects.get_or_create(
                user=user,
                product=product,
                defaults={'expires_at': now},
            )
            # Lock the subscription row to prevent concurrent expiry miscalculation
            sub = UserTVSubscription.objects.select_for_update().get(pk=sub.pk)
            new_expiry = (
                sub.expires_at + timedelta(days=days)
                if sub.expires_at > now
                else now + timedelta(days=days)
            )
            UserTVSubscription.objects.filter(pk=sub.pk).update(expires_at=new_expiry)
            CustomUser.objects.filter(pk=user.pk).update(coins=F('coins') - cost)

        user.refresh_from_db(fields=['coins'])
        return JsonResponse({
            'success': True,
            'expires_at': new_expiry.isoformat(),
            'coins_remaining': float(user.coins),
        })
    except Exception:
        logger.exception('subscribe_tradingview failed for user %s', request.user.pk)
        return JsonResponse({'error': 'Đăng ký thất bại, vui lòng thử lại.'}, status=500)


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

        user.refresh_from_db(fields=['coins', 'ai_trading_expires_at'])
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

    # Rate-limit: tối đa 5 lần phân tích / phút / user (atomic incr tránh race condition)
    rate_key = f'ai:analyze:rate:{request.user.pk}'
    try:
        rate_count = cache.incr(rate_key)
    except ValueError:
        cache.add(rate_key, 0, 60)
        rate_count = cache.incr(rate_key)
    if rate_count > 5:
        return JsonResponse({'error': 'Bạn đang phân tích quá nhanh. Vui lòng chờ 1 phút.'}, status=429)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)

    symbol          = body.get('symbol', 'OANDA:XAUUSD').strip().upper()
    interval        = body.get('interval', '60').strip()
    current_price   = body.get('current_price')
    chart_image_b64 = body.get('chart_image') or ''
    candles         = body.get('candles')

    if not re.match(r'^[A-Z0-9_:.]{1,50}$', symbol):
        return JsonResponse({'error': 'Symbol không hợp lệ'}, status=400)
    if interval not in {'1', '5', '15', '30', '60', '120', '240', 'D', 'W'}:
        return JsonResponse({'error': 'Interval không hợp lệ'}, status=400)
    if chart_image_b64 and len(chart_image_b64) > 2_000_000:
        chart_image_b64 = ''
    if isinstance(candles, list):
        if len(candles) > 500:
            return JsonResponse({'error': 'Quá nhiều nến'}, status=400)
        required_keys = {'open', 'high', 'low', 'close'}
        if candles and not all(isinstance(c, dict) and required_keys.issubset(c) for c in candles[:5]):
            candles = None

    _ALLOWED_SIGNALS = {'BUY', 'SELL', 'HOLD'}

    def _clamp_price(v, max_val=10 ** 12):
        if v is None:
            return None
        try:
            f = float(v)
            return None if abs(f) > max_val else v
        except (TypeError, ValueError):
            return None

    try:
        if chart_image_b64:
            try:
                image_bytes = base64.b64decode(chart_image_b64, validate=True)
                if not image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError('not png')
            except (ValueError, binascii.Error):
                image_bytes = _PNG_FALLBACK
        else:
            image_bytes = _PNG_FALLBACK

        indicators = compute_indicators_local(candles if isinstance(candles, list) else [])
        result      = analyze_with_gemini(image_bytes, indicators, symbol, interval,
                                          current_price=current_price)

        # Sanitize Gemini output before persisting
        if result.get('signal') not in _ALLOWED_SIGNALS:
            result['signal'] = 'HOLD'
        result['confidence'] = max(0, min(100, int(result.get('confidence', 0) or 0)))
        result['entry'] = _clamp_price(result.get('entry'))
        result['sl']    = _clamp_price(result.get('sl'))
        result['tp']    = _clamp_price(result.get('tp'))

        ChartAnalysisLog.objects.create(
            user=request.user,
            symbol=symbol,
            interval=interval,
            **result,
        )

        return JsonResponse({'success': True, 'data': result})

    except Exception:
        logger.exception('analyze_chart failed for user %s symbol %s', request.user.pk, symbol)
        # Hoàn trả rate-limit slot khi xử lý thất bại (không phải lỗi của user)
        try:
            cache.decr(rate_key)
        except Exception:
            pass
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


_CHART_RATE_LIMIT = 30   # req/phút/user cho chart-data
_TICK_RATE_LIMIT  = 60   # req/phút/user cho tick (polling)


def chart_data_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    cd_rate_key = f'chart:rate:{request.user.pk}'
    try:
        cd_count = cache.incr(cd_rate_key)
    except ValueError:
        cache.add(cd_rate_key, 0, 60)
        cd_count = cache.incr(cd_rate_key)
    if cd_count > _CHART_RATE_LIMIT:
        return JsonResponse({'error': 'Quá nhiều yêu cầu. Vui lòng chờ.'}, status=429)

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
    if not re.match(r'^[A-Z0-9]{1,20}$', ticker):
        raise ValueError(f'Invalid Binance ticker: {ticker}')
    ticker = urllib.parse.quote(ticker, safe='')
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

    tk_rate_key = f'tick:rate:{request.user.pk}'
    try:
        tk_count = cache.incr(tk_rate_key)
    except ValueError:
        cache.add(tk_rate_key, 0, 60)
        tk_count = cache.incr(tk_rate_key)
    if tk_count > _TICK_RATE_LIMIT:
        return JsonResponse({'error': 'Quá nhiều yêu cầu. Vui lòng chờ.'}, status=429)

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
