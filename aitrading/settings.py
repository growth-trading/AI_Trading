from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-me')
DEBUG = config('DEBUG', default=False, cast=bool)
# In production: set ALLOWED_HOSTS in .env, e.g. ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
_allowed_hosts = config('ALLOWED_HOSTS', default='*')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',')]

INSTALLED_APPS = [
    'aitrading.apps.AitradingConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'deposits',
    'trading',
    'profiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'accounts.middleware.IPRateLimitMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.EmailVerifiedMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'aitrading.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'aitrading.wsgi.application'

_db_engine = config('DB_ENGINE', default='sqlite')

_db_sslmode = config('DB_SSLMODE', default='')

if _db_engine == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='aitrading'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='5432'),
            'OPTIONS': {'sslmode': _db_sslmode} if _db_sslmode else {},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'accounts.CustomUser'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/trading/'
LOGOUT_REDIRECT_URL = '/'

LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = (
    'django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG
    else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = 'aitrading.email_backend.CertifiSMTPBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER', default='noreply@richaitrading.vn')

ADMIN_WALLET_ADDRESS = config('ADMIN_WALLET_ADDRESS', default='')
USDT_CONTRACT_BSC = config('USDT_CONTRACT_BSC', default='0x55d398326f99059fF775485246999027B3197955')
BSCSCAN_API_KEY = config('BSCSCAN_API_KEY', default='')
USDT_TO_COINS_RATE = config('USDT_TO_COINS_RATE', default=1, cast=int)
WALLET_SCAN_INTERVAL_SECONDS = max(10, config('WALLET_SCAN_INTERVAL_SECONDS', default=60, cast=int))

# AI Chart Analysis
MT5_ACCOUNT  = config('MT5_ACCOUNT',  default='')
MT5_PASSWORD = config('MT5_PASSWORD', default='')
MT5_SERVER   = config('MT5_SERVER',   default='')

GEMINI_API_KEY = config('GEMINI_API_KEY', default='')

TELEGRAM_BOT_TOKEN      = config('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_WEBHOOK_SECRET = config('TELEGRAM_WEBHOOK_SECRET', default='')

# Referral payout — gửi USDT tự động từ ví admin
ADMIN_PRIVATE_KEY = config('ADMIN_PRIVATE_KEY', default='')
REFERRAL_MIN_PAYOUT_COINS = config('REFERRAL_MIN_PAYOUT_COINS', default=10, cast=int)


# TradingView subscription plan costs (in coins)
TV_PLAN_WEEK_COST  = config('TV_PLAN_WEEK_COST',  default=10,  cast=int)
TV_PLAN_MONTH_COST = config('TV_PLAN_MONTH_COST', default=30,  cast=int)
TV_PLAN_YEAR_COST  = config('TV_PLAN_YEAR_COST',  default=200, cast=int)

# Cache — Redis bắt buộc, không có fallback LocMemCache
REDIS_URL = config('REDIS_URL', default='')
if not REDIS_URL:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        'REDIS_URL chưa được cấu hình trong .env. '
        'Hãy set REDIS_URL=redis://127.0.0.1:6379/0 và đảm bảo Redis đang chạy.'
    )

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 3,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': False,
        },
        'KEY_PREFIX': 'ait',
        'TIMEOUT': 300,
    }
}

# Security settings cho production (HTTPS required)
if not DEBUG:
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

