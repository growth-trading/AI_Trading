from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-me')
DEBUG = config('DEBUG', default=True, cast=bool)
# In production: set ALLOWED_HOSTS in .env, e.g. ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
_allowed_hosts = config('ALLOWED_HOSTS', default='*')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',')]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_apscheduler',
    'accounts',
    'deposits',
    'trading',
    'profiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
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

# AI Trading subscription plan costs (in coins)
AI_PLAN_WEEK_COST  = config('AI_PLAN_WEEK_COST',  default=20,  cast=int)
AI_PLAN_MONTH_COST = config('AI_PLAN_MONTH_COST', default=50,  cast=int)
AI_PLAN_YEAR_COST  = config('AI_PLAN_YEAR_COST',  default=400, cast=int)

# TradingView subscription plan costs (in coins)
TV_PLAN_WEEK_COST  = config('TV_PLAN_WEEK_COST',  default=10,  cast=int)
TV_PLAN_MONTH_COST = config('TV_PLAN_MONTH_COST', default=30,  cast=int)
TV_PLAN_YEAR_COST  = config('TV_PLAN_YEAR_COST',  default=200, cast=int)

# Cache — dùng Redis nếu REDIS_URL được set, fallback LocMemCache (chỉ dùng cho dev single-process)
REDIS_URL = config('REDIS_URL', default='')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'IGNORE_EXCEPTIONS': True,
            },
            'KEY_PREFIX': 'ait',
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'ait-mt5',
        }
    }

# Security settings cho production (HTTPS required)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG and not REDIS_URL:
    import warnings
    warnings.warn(
        'PRODUCTION without REDIS_URL: rate limiting and cache will not work across workers. '
        'Set REDIS_URL in .env (e.g. redis://127.0.0.1:6379/0).',
        RuntimeWarning,
        stacklevel=2,
    )

APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25

# Set to '1' in production to start the wallet scanner scheduler on app startup.
# In development, the scheduler starts automatically when using `runserver`.
DJANGO_RUN_SCHEDULER = config('DJANGO_RUN_SCHEDULER', default='0')
