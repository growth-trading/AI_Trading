import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AitradingConfig(AppConfig):
    name = 'aitrading'
    verbose_name = 'AI Trading Core'

    def ready(self):
        self._ensure_redis()

    def _ensure_redis(self):
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
        import redis as redis_lib

        try:
            redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=3).ping()
            logger.info('Redis connected: %s', settings.REDIS_URL)
        except Exception as e:
            raise ImproperlyConfigured(
                f'Không thể kết nối Redis tại {settings.REDIS_URL}: {e}\n'
                'Hãy khởi động Redis trước khi chạy server (vd: redis-server), '
                'sau đó đặt REDIS_URL=redis://127.0.0.1:6379/0 trong .env.'
            ) from e
