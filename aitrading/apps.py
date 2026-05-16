import logging
import subprocess
import time
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AitradingConfig(AppConfig):
    name = 'aitrading'
    verbose_name = 'AI Trading Core'

    def ready(self):
        self._ensure_redis()

    def _ensure_redis(self):
        from django.conf import settings
        import redis as redis_lib

        def _ping():
            redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=3).ping()

        try:
            _ping()
            logger.info('Redis already running: %s', settings.REDIS_URL)
            return
        except Exception:
            pass

        logger.info('Redis chưa chạy, đang khởi động redis-server...')
        try:
            subprocess.Popen(
                ['redis-server'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.5)
            _ping()
            logger.info('Redis khởi động thành công.')
        except Exception as e:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                f'Không thể kết nối hoặc khởi động Redis tại {settings.REDIS_URL}: {e}\n'
                'Hãy cài Redis và đảm bảo redis-server có trong PATH.'
            ) from e
