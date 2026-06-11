import urllib.request
import urllib.parse
import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Đăng ký / xem / xóa Telegram webhook'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['set', 'info', 'delete'], nargs='?', default='set')
        parser.add_argument('--site', help='Public HTTPS URL, ví dụ: https://yourdomain.com')

    def handle(self, *args, **options):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')

        if not token:
            raise CommandError('TELEGRAM_BOT_TOKEN chưa set trong .env')

        action = options['action']
        base = f'https://api.telegram.org/bot{token}'

        if action == 'info':
            data = self._call(f'{base}/getWebhookInfo')
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))

        elif action == 'delete':
            data = self._call(f'{base}/deleteWebhook', {'drop_pending_updates': True})
            if data.get('ok'):
                self.stdout.write(self.style.SUCCESS('Webhook đã xóa.'))
            else:
                self.stdout.write(self.style.ERROR(str(data)))

        else:  # set
            site = (options.get('site') or '').rstrip('/')
            if not site:
                raise CommandError('Cần --site https://yourdomain.com')
            if not secret:
                raise CommandError('TELEGRAM_WEBHOOK_SECRET chưa set trong .env')

            webhook_url = f'{site}/trading/tg-webhook/{secret}/'
            payload = {
                'url': webhook_url,
                'allowed_updates': ['message', 'channel_post'],
                'drop_pending_updates': True,
            }
            data = self._call(f'{base}/setWebhook', payload)
            if data.get('ok'):
                self.stdout.write(self.style.SUCCESS(f'Webhook đã set:\n  {webhook_url}'))
            else:
                self.stdout.write(self.style.ERROR(f'Thất bại: {data}'))

    def _call(self, url, payload=None):
        try:
            if payload:
                body = json.dumps(payload).encode()
                req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
            else:
                req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            raise CommandError(f'Lỗi gọi Telegram API: {exc}')
