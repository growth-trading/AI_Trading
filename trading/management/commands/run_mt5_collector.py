"""
MT5 Data Collector
==================
Process độc lập, kết nối MT5 một lần duy nhất, liên tục làm mới cache.
Các Django worker chỉ đọc cache — không bao giờ gọi MT5 trực tiếp khi cache còn hạn.

Chạy:
    python manage.py run_mt5_collector
    python manage.py run_mt5_collector --symbols OANDA:XAUUSD,OANDA:EURUSD --intervals 60,240

Production (chạy nền):
    nohup python manage.py run_mt5_collector >> logs/mt5_collector.log 2>&1 &
"""
import time
import signal
import logging

from django.core.cache import cache
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# Tất cả cặp cần pre-fetch
_DEFAULT_SYMBOLS = [
    'OANDA:XAUUSD', 'OANDA:XAGUSD',
    'OANDA:EURUSD', 'OANDA:GBPUSD', 'OANDA:USDJPY',
]
_DEFAULT_INTERVALS = ['1', '5', '15', '30', '60', '120', '240', 'D', 'W']

# Tần suất làm mới (giây) = ~80% TTL để cache không bao giờ hết hạn
_REFRESH_EVERY = {
    '1': 12,  '5': 36,  '15': 70,  '30': 95,
    '60': 140, '120': 280, '240': 480,
    'D': 1440, 'W': 2880,
}

_MT5_SYMBOLS = {
    'OANDA:XAUUSD': 'XAUUSD', 'OANDA:XAGUSD': 'XAGUSD',
    'OANDA:EURUSD': 'EURUSD', 'OANDA:GBPUSD': 'GBPUSD',
    'OANDA:USDJPY': 'USDJPY',
}

_CACHE_TTL = {
    '1': 15, '5': 45, '15': 90, '30': 120,
    '60': 180, '120': 360, '240': 600,
    'D': 1800, 'W': 3600,
}


class Command(BaseCommand):
    help = 'Chạy MT5 data collector — pre-fetch candles vào Redis cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            default=','.join(_DEFAULT_SYMBOLS),
            help='Danh sách symbol cách nhau bằng dấu phẩy',
        )
        parser.add_argument(
            '--intervals',
            default=','.join(_DEFAULT_INTERVALS),
            help='Danh sách interval cách nhau bằng dấu phẩy',
        )

    def handle(self, *args, **options):
        try:
            import MetaTrader5 as mt5
        except ImportError:
            self.stderr.write(self.style.ERROR('MetaTrader5 chưa cài. Chạy: pip install MetaTrader5'))
            return

        symbols   = [s.strip() for s in options['symbols'].split(',') if s.strip()]
        intervals = [i.strip() for i in options['intervals'].split(',') if i.strip()]

        self.stdout.write(self.style.SUCCESS(
            f'MT5 Collector khởi động — {len(symbols)} symbols × {len(intervals)} intervals'
        ))

        # Kết nối MT5 một lần
        if not mt5.initialize():
            self.stderr.write(self.style.ERROR(f'Không thể khởi động MT5: {mt5.last_error()}'))
            return

        if mt5.account_info() is None:
            from django.conf import settings
            acc = getattr(settings, 'MT5_ACCOUNT', '')
            pwd = getattr(settings, 'MT5_PASSWORD', '')
            srv = getattr(settings, 'MT5_SERVER', '')
            if acc and pwd and srv:
                if not mt5.login(int(acc), password=pwd, server=srv):
                    self.stderr.write(self.style.ERROR(f'MT5 login thất bại: {mt5.last_error()}'))
                    mt5.shutdown()
                    return
            else:
                self.stderr.write(self.style.WARNING(
                    'Không có MT5 credentials, dùng terminal đang login sẵn.'
                ))

        self.stdout.write(self.style.SUCCESS('MT5 đã kết nối. Bắt đầu collection loop...'))

        # Build timeframe map
        tf_map = {
            '1': mt5.TIMEFRAME_M1,  '5': mt5.TIMEFRAME_M5,
            '15': mt5.TIMEFRAME_M15, '30': mt5.TIMEFRAME_M30,
            '60': mt5.TIMEFRAME_H1,  '120': mt5.TIMEFRAME_H2,
            '240': mt5.TIMEFRAME_H4, 'D': mt5.TIMEFRAME_D1,
            'W': mt5.TIMEFRAME_W1,
        }

        sym_cache = {}  # base → resolved MT5 symbol name

        def resolve(base):
            if base in sym_cache:
                return sym_cache[base]
            for suffix in ('', 'm', '.', 'pro', 'c', 'n'):
                name = base + suffix
                if mt5.symbol_info(name) is not None:
                    mt5.symbol_select(name, True)
                    sym_cache[base] = name
                    return name
            sym_cache[base] = base
            return base

        last_fetch = {}   # (symbol, interval) → timestamp
        running    = [True]

        def _shutdown(signum, frame):
            running[0] = False
            self.stdout.write('\nMT5 Collector dừng...')

        signal.signal(signal.SIGINT,  _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        stats = {'ok': 0, 'err': 0}

        while running[0]:
            now = time.time()
            for symbol in symbols:
                mt5_base = _MT5_SYMBOLS.get(symbol, symbol.split(':')[-1])
                mt5_sym  = resolve(mt5_base)
                tf_key   = None  # reset per symbol per interval

                for interval in intervals:
                    key = (symbol, interval)
                    if now - last_fetch.get(key, 0) < _REFRESH_EVERY.get(interval, 140):
                        continue

                    tf = tf_map.get(interval, mt5.TIMEFRAME_H1)
                    try:
                        rates = mt5.copy_rates_from_pos(mt5_sym, tf, 0, 150)
                        if rates is None or len(rates) == 0:
                            logger.warning('collector: no data %s %s err=%s', symbol, interval, mt5.last_error())
                            stats['err'] += 1
                            continue

                        candles = [
                            {
                                'time':  int(r['time']),
                                'open':  round(float(r['open']),  6),
                                'high':  round(float(r['high']),  6),
                                'low':   round(float(r['low']),   6),
                                'close': round(float(r['close']), 6),
                            }
                            for r in rates
                        ]
                        ttl = _CACHE_TTL.get(interval, 180)
                        cache.set(f'mt5:candles:{symbol}:{interval}', candles, ttl)
                        cache.set(f'mt5:tick:{symbol}:{interval}',    candles[-1], max(5, ttl // 3))
                        last_fetch[key] = now
                        stats['ok'] += 1
                        logger.debug('cached %s %s (%d candles)', symbol, interval, len(candles))

                    except Exception as exc:
                        logger.error('collector error %s %s: %s', symbol, interval, exc)
                        stats['err'] += 1

            # Log thống kê mỗi 60s
            if int(now) % 60 == 0:
                self.stdout.write(
                    f'[collector] ok={stats["ok"]} err={stats["err"]} '
                    f'cache_keys={len(last_fetch)}'
                )

            time.sleep(1)

        mt5.shutdown()
        self.stdout.write(self.style.SUCCESS(
            f'MT5 Collector đã dừng. Tổng: ok={stats["ok"]} err={stats["err"]}'
        ))
