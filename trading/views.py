import base64
import binascii
import io
import json
import logging
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta, datetime as _dt, timezone as _tz
from decimal import Decimal, InvalidOperation
from django.core.cache import cache
from PIL import Image

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
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from django.views.decorators.csrf import csrf_exempt
from accounts.models import CustomUser, pay_referral_commission
from .models import ChartAnalysisLog, TradingViewProduct, UserTVSubscription, AIPlanSettings, BrokerLink, CopyTradeExchange, TradingSignal
from .services import compute_indicators_local, analyze_with_gemini


@require_GET
def landing(request):
    return render(request, 'landing/index.html')


@require_GET
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


@require_GET
def services_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.is_email_verified:
        return redirect('verify_otp')

    brokers = BrokerLink.objects.filter(is_active=True).order_by('category', 'sort_order', 'pk')
    return render(request, 'trading/services.html', {'brokers': brokers})


@require_GET
def copy_trade_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.is_email_verified:
        return redirect('verify_otp')

    brokers = {b.slug: b for b in BrokerLink.objects.filter(is_active=True)}
    copy_exchanges = CopyTradeExchange.objects.filter(is_active=True)
    return render(request, 'trading/copytrade.html', {'brokers': brokers, 'copy_exchanges': copy_exchanges})


@require_GET
def signals_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.is_email_verified:
        return redirect('verify_otp')

    signals = TradingSignal.objects.all()[:100]
    return render(request, 'trading/signals.html', {'signals': signals})


@csrf_exempt
def tradingview_webhook_view(request, secret):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    expected = getattr(settings, 'TV_WEBHOOK_SECRET', '')
    if not expected or secret != expected:
        return JsonResponse({'ok': False}, status=403)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False}, status=400)

    try:
        signal_raw = body.get('signal', '')
        if 'long' in signal_raw.lower():
            signal_type = 'BUY'
        elif 'short' in signal_raw.lower():
            signal_type = 'SELL'
        else:
            return JsonResponse({'ok': False, 'error': 'Unknown signal type'}, status=400)

        ticker   = body.get('ticker', '').upper()
        exchange = body.get('exchange', '').upper()
        symbol   = f"{exchange}:{ticker}" if exchange else ticker

        interval_raw = body.get('interval', '5')
        try:
            timeframe = f"{int(interval_raw)}m"
        except (ValueError, TypeError):
            timeframe = str(interval_raw)

        def _dec(val):
            if val is None:
                return None
            try:
                return Decimal(str(val))
            except InvalidOperation:
                return None

        entry = _dec(body.get('close'))
        sl    = _dec(body.get('sl'))
        if not entry or not sl:
            return JsonResponse({'ok': False, 'error': 'Missing entry or sl'}, status=400)

        TradingSignal.objects.create(
            signal_type=signal_type,
            symbol=symbol,
            timeframe=timeframe,
            entry=entry,
            sl=sl,
            tp1=_dec(body.get('tp1')),
            tp2=_dec(body.get('tp2')),
            tp3=_dec(body.get('tp3')),
            tp4=_dec(body.get('tp4')),
            tp5=_dec(body.get('tp5')),
            status='active',
        )
        logger.info('tv_webhook: %s %s @ %s', signal_type, symbol, entry)

    except Exception as exc:
        logger.exception('tv_webhook: error: %s', exc)
        return JsonResponse({'ok': False}, status=500)

    return JsonResponse({'ok': True})



_PLAN_DAYS = {'week': 7, 'month': 30, 'year': 365}

class _InsufficientCoins(Exception):
    pass


@require_POST
def subscribe_tradingview_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)

    # Chống double-click: block 10s/user
    if not cache.add(f'subscribe:tv:lock:{request.user.pk}', 1, 10):
        return JsonResponse({'error': 'Yêu cầu đang xử lý, vui lòng chờ giây lát.'}, status=429)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)

    plan = body.get('plan')
    product_slug = body.get('product_slug', '')

    if plan not in _PLAN_DAYS:
        return JsonResponse({'error': 'Gói không hợp lệ'}, status=400)

    try:
        product = TradingViewProduct.objects.get(slug=product_slug, is_active=True)
    except TradingViewProduct.DoesNotExist:
        return JsonResponse({'error': 'Sản phẩm không tồn tại'}, status=404)

    if product.is_coming_soon:
        return JsonResponse({'error': 'Sản phẩm chưa ra mắt, vui lòng chờ.'}, status=400)

    cost = getattr(product, f'{plan}_cost')
    days = _PLAN_DAYS[plan]
    now = timezone.now()

    try:
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=request.user.pk)

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
            # coins__gte=cost đảm bảo atomic check+update, bảo vệ cả SQLite lẫn PostgreSQL
            updated = CustomUser.objects.filter(
                pk=user.pk, coins__gte=cost
            ).update(coins=F('coins') - cost)
            if not updated:
                raise _InsufficientCoins()
            UserTVSubscription.objects.filter(pk=sub.pk).update(expires_at=new_expiry)

        user.refresh_from_db(fields=['coins'])
        try:
            pay_referral_commission(request.user.pk, cost)
        except Exception:
            logger.exception('Referral commission failed after TV purchase for user %s', request.user.pk)
        return JsonResponse({
            'success': True,
            'expires_at': new_expiry.isoformat(),
            'coins_remaining': str(user.coins),
        })
    except _InsufficientCoins:
        return JsonResponse({'error': 'Không đủ xu. Vui lòng nạp thêm.'}, status=402)
    except Exception:
        logger.exception('subscribe_tradingview failed for user %s', request.user.pk)
        return JsonResponse({'error': 'Đăng ký thất bại, vui lòng thử lại.'}, status=500)


@require_GET
def trading_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    ai_cfg = AIPlanSettings.get()
    plans = {
        'week':  ai_cfg.week_cost,
        'month': ai_cfg.month_cost,
        'year':  ai_cfg.year_cost,
    }
    recent_logs = []
    if user.has_ai_trading_access:
        recent_logs = list(
            ChartAnalysisLog.objects.filter(user=user).order_by('-created_at')[:20]
        )
    return render(request, 'trading/index.html', {
        'has_ai_access': user.has_ai_trading_access,
        'ai_expires_at': user.ai_trading_expires_at,
        'ai_plans': plans,
        'recent_logs': recent_logs,
    })


@require_POST
def subscribe_ai_trading_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)

    # Chống double-click: block 10s/user
    if not cache.add(f'subscribe:ai:lock:{request.user.pk}', 1, 10):
        return JsonResponse({'error': 'Yêu cầu đang xử lý, vui lòng chờ giây lát.'}, status=429)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)

    plan = body.get('plan')
    if plan not in _PLAN_DAYS:
        return JsonResponse({'error': 'Gói không hợp lệ'}, status=400)

    ai_cfg = AIPlanSettings.get()
    plan_costs = {
        'week':  ai_cfg.week_cost,
        'month': ai_cfg.month_cost,
        'year':  ai_cfg.year_cost,
    }
    cost = plan_costs[plan]
    days = _PLAN_DAYS[plan]
    now = timezone.now()

    try:
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
            new_expiry = (
                user.ai_trading_expires_at + timedelta(days=days)
                if user.ai_trading_expires_at and user.ai_trading_expires_at > now
                else now + timedelta(days=days)
            )
            # coins__gte=cost đảm bảo atomic check+update, bảo vệ cả SQLite lẫn PostgreSQL
            updated = CustomUser.objects.filter(
                pk=user.pk, coins__gte=cost
            ).update(
                coins=F('coins') - cost,
                ai_trading_expires_at=new_expiry,
            )
            if not updated:
                raise _InsufficientCoins()

        user.refresh_from_db(fields=['coins', 'ai_trading_expires_at'])
        try:
            pay_referral_commission(request.user.pk, cost)
        except Exception:
            logger.exception('Referral commission failed after AI purchase for user %s', request.user.pk)
        return JsonResponse({
            'success': True,
            'expires_at': user.ai_trading_expires_at.isoformat(),
            'coins_remaining': str(user.coins),
        })
    except _InsufficientCoins:
        return JsonResponse({'error': 'Không đủ xu. Vui lòng nạp thêm.'}, status=402)
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

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)

    symbol          = body.get('symbol', 'OANDA:XAUUSD').strip().upper()
    interval        = body.get('interval', '60').strip()
    chart_image_b64 = body.get('chart_image') or ''
    candles         = body.get('candles')
    lang            = body.get('lang', 'vi') if body.get('lang') in ('vi', 'en') else 'vi'

    try:
        cp = float(body.get('current_price') or 0)
        current_price = cp if 0 < cp < 10 ** 10 else None
    except (TypeError, ValueError):
        current_price = None

    if not re.match(r'^[A-Z0-9_:.]{1,50}$', symbol):
        return JsonResponse({'error': 'Symbol không hợp lệ'}, status=400)
    if interval not in {'1', '5', '15', '30', '60', '120', '240', 'D', 'W'}:
        return JsonResponse({'error': 'Interval không hợp lệ'}, status=400)
    if chart_image_b64 and len(chart_image_b64) > 2_000_000:
        return JsonResponse({'error': 'Ảnh chụp biểu đồ quá lớn (>1.5MB). Vui lòng thử lại.'}, status=400)
    if isinstance(candles, list):
        if len(candles) > 500:
            return JsonResponse({'error': 'Quá nhiều nến'}, status=400)
        required_keys = {'open', 'high', 'low', 'close'}
        if candles and not all(isinstance(c, dict) and required_keys.issubset(c) for c in candles):
            candles = None

    # Validate ảnh trước rate-limit — tránh consume slot cho request lỗi của client
    if not chart_image_b64:
        return JsonResponse({'error': 'Không chụp được ảnh biểu đồ. Vui lòng thử lại.'}, status=400)
    try:
        image_bytes = base64.b64decode(chart_image_b64, validate=True)
        if not image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('not png')
    except (ValueError, binascii.Error):
        return JsonResponse({'error': 'Ảnh biểu đồ không hợp lệ. Vui lòng thử lại.'}, status=400)

    # Nén ảnh xuống tối đa 640px JPEG để giảm token Gemini (token tính theo pixel)
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        if img.width > 640:
            new_h = int(img.height * 640 / img.width)
            img = img.resize((640, new_h), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=80, optimize=True)
        image_bytes = buf.getvalue()
        image_mime  = 'image/jpeg'
    except Exception:
        image_mime = 'image/png'  # giữ nguyên ảnh gốc nếu PIL thất bại

    # Rate-limit — tối đa 5 lần / phút / user
    # cache.add trả False nếu key đã tồn tại → incr; True nếu vừa tạo → rate_count = 1
    rate_key = f'ai:analyze:rate:{request.user.pk}'
    if not cache.add(rate_key, 1, 60):
        rate_count = cache.incr(rate_key)
    else:
        rate_count = 1
    if rate_count > 5:
        return JsonResponse({'error': 'Bạn đang phân tích quá nhanh. Vui lòng chờ 1 phút.'}, status=429)

    _ALLOWED_SIGNALS = {'BUY', 'SELL', 'HOLD'}

    def _clamp_price(v, max_val=10 ** 12):
        if v is None:
            return None
        try:
            d = Decimal(str(v))
            return None if abs(d) > max_val else d
        except (TypeError, ValueError, InvalidOperation):
            return None

    def _decr_rate():
        try:
            cache.decr(rate_key)
        except Exception:
            pass

    try:
        indicators = compute_indicators_local(candles if isinstance(candles, list) else [])

        result = analyze_with_gemini(image_bytes, indicators, symbol, interval,
                                     current_price=current_price, lang=lang,
                                     image_mime=image_mime)

        # Sanitize Gemini output before persisting
        if result.get('signal') not in _ALLOWED_SIGNALS:
            result['signal'] = 'HOLD'
        result['confidence'] = max(0, min(100, int(result.get('confidence', 0) or 0)))
        result['entry'] = _clamp_price(result.get('entry'))
        result['sl']    = _clamp_price(result.get('sl'))
        result['tp']    = _clamp_price(result.get('tp'))

        log = ChartAnalysisLog.objects.create(
            user=request.user,
            symbol=symbol,
            interval=interval,
            **result,
        )

        # Chuyển Decimal sang float chỉ khi serialize JSON (giữ precision cho DB)
        json_result = {
            **result,
            'entry': float(result['entry']) if result['entry'] is not None else None,
            'sl':    float(result['sl'])    if result['sl']    is not None else None,
            'tp':    float(result['tp'])    if result['tp']    is not None else None,
            'log_id': log.pk,
        }
        return JsonResponse({'success': True, 'data': json_result})

    except RuntimeError as e:
        _decr_rate()
        msg = str(e)
        if 'quá tải' in msg or 'quota' in msg.lower():
            logger.warning('AI API overloaded for user %s: %s | cause: %s', request.user.pk, msg, e.__cause__)
            return JsonResponse({'error': msg}, status=429)
        logger.warning('analyze_chart RuntimeError for user %s: %s', request.user.pk, msg)
        return JsonResponse({'error': 'Phân tích thất bại, vui lòng thử lại.'}, status=500)
    except Exception:
        logger.exception('analyze_chart failed for user %s symbol %s', request.user.pk, symbol)
        _decr_rate()
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

_mt5_symbol_cache: dict = {}


def _mt5_resolve_symbol(base: str) -> str:
    if base in _mt5_symbol_cache:
        return _mt5_symbol_cache[base]
    if len(_mt5_symbol_cache) >= 200:
        _mt5_symbol_cache.clear()
    for suffix in ('', 'm', '.', 'pro', 'c', 'n'):
        name = base + suffix
        if _mt5.symbol_info(name) is not None:
            _mt5.symbol_select(name, True)
            _mt5_symbol_cache[base] = name
            return name
    _mt5_symbol_cache[base] = base
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
        result = _mt5.login(int(account), password=password, server=server)
        if result:
            _mt5_symbol_cache.clear()
        return result
    return False


def _interval_secs(iv):
    if iv == 'D': return 86400
    if iv == 'W': return 604800
    try:
        return int(iv) * 60
    except (ValueError, TypeError):
        return 3600

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


@require_GET
def chart_data_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)

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
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        logger.warning('Binance fetch failed for %s %s: %s', symbol, interval, e)
        raise _MT5Unavailable('Không thể tải dữ liệu Binance')
    if not isinstance(data, list):
        logger.warning('Binance returned non-list for %s %s: %s', symbol, interval, str(data)[:200])
        raise _MT5Unavailable('Binance trả dữ liệu không hợp lệ')
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
            cache.set(f'mt5:tick:{symbol}:{interval}', candles[-1], 1)

        return candles


@require_GET
def tick_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)

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
                    raw_data = json.loads(r.read())
                if not isinstance(raw_data, list) or not raw_data:
                    raise ValueError('Binance returned empty or invalid data')
                d = raw_data[0]
                candle = {
                    'time': int(d[0]) // 1000, 'open': float(d[1]),
                    'high': float(d[2]), 'low': float(d[3]), 'close': float(d[4]),
                }
                cache.set(tick_cache_key, candle, 1)
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
                cache.set(tick_key, candle, 1)

        return JsonResponse({'success': True, 'candle': candle})

    except Exception:
        logger.exception('tick_view failed for user %s symbol %s', request.user.pk, symbol)
        return JsonResponse({'error': 'Không thể tải dữ liệu, vui lòng thử lại.'}, status=500)


def _candles_since(symbol: str, interval: str, since_ts: int) -> list:
    """Lấy toàn bộ nến từ since_ts đến hiện tại. Dùng để kiểm tra trạng thái kèo trong lịch sử."""
    if symbol.startswith('BINANCE:'):
        ticker = symbol.split(':', 1)[1]
        if not re.match(r'^[A-Z0-9]{1,20}$', ticker):
            return []
        ticker = urllib.parse.quote(ticker, safe='')
        bi = _BINANCE_INTERVAL.get(interval, '1h')
        url = (f'https://api.binance.com/api/v3/klines?symbol={ticker}'
               f'&interval={bi}&startTime={since_ts * 1000}&limit=1000')
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            if not isinstance(data, list):
                return []
            return [
                {'time': int(d[0]) // 1000, 'open': float(d[1]),
                 'high': float(d[2]), 'low': float(d[3]), 'close': float(d[4])}
                for d in data
            ]
        except Exception as e:
            logger.warning('_candles_since Binance failed %s %s: %s', symbol, interval, e)
            return []
    else:
        try:
            return _mt5_candles(symbol, interval, since_ts=since_ts, before_ts=None)
        except Exception as e:
            logger.warning('_candles_since MT5 failed %s %s: %s', symbol, interval, e)
            return []


def _determine_trade_status(candles: list, signal: str, entry, sl, tp) -> str:
    """Kiểm tra theo thứ tự thời gian xem TP hay SL đã bị chạm. Trả về 'TP', 'SL' hoặc 'RUNNING'."""
    is_buy = signal == 'BUY'
    try:
        sl_f = float(sl)
        tp_f = float(tp)
        entry_f = float(entry)
    except (TypeError, ValueError):
        return 'RUNNING'
    for candle in candles:
        try:
            high   = float(candle['high'])
            low    = float(candle['low'])
            open_p = float(candle.get('open', entry_f))
        except (KeyError, TypeError, ValueError):
            continue
        sl_hit = (low <= sl_f)  if is_buy else (high >= sl_f)
        tp_hit = (high >= tp_f) if is_buy else (low  <= tp_f)
        if sl_hit and tp_hit:
            return 'SL' if abs(open_p - sl_f) < abs(open_p - tp_f) else 'TP'
        if sl_hit:
            return 'SL'
        if tp_hit:
            return 'TP'
    return 'RUNNING'


@require_GET
def trade_status_view(request, log_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)
    try:
        log = ChartAnalysisLog.objects.get(pk=log_id, user=request.user)
    except ChartAnalysisLog.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy'}, status=404)

    if log.trade_status in ('TP', 'SL'):
        return JsonResponse({'status': log.trade_status, 'cached': True})

    if not (log.entry and log.sl and log.tp) or log.signal == 'HOLD':
        return JsonResponse({'status': 'NONE'})

    since_ts = int(log.created_at.timestamp())
    candles  = _candles_since(log.symbol, log.interval, since_ts)
    if not candles:
        return JsonResponse({'status': 'RUNNING', 'current_price': None})

    status = _determine_trade_status(candles, log.signal, log.entry, log.sl, log.tp)
    current_price = candles[-1].get('close')

    if status in ('TP', 'SL'):
        ChartAnalysisLog.objects.filter(pk=log.pk).update(trade_status=status)

    return JsonResponse({'status': status, 'current_price': current_price})
