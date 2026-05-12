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
LOGIN_REDIRECT_URL = '/dashboard/'
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
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER', default='noreply@aitrading.vn')

ADMIN_WALLET_ADDRESS = config('ADMIN_WALLET_ADDRESS', default='')
USDT_CONTRACT_BSC = config('USDT_CONTRACT_BSC', default='0x55d398326f99059fF775485246999027B3197955')
BSCSCAN_API_KEY = config('BSCSCAN_API_KEY', default='')
USDT_TO_COINS_RATE = config('USDT_TO_COINS_RATE', default=1, cast=int)
WALLET_SCAN_INTERVAL_SECONDS = config('WALLET_SCAN_INTERVAL_SECONDS', default=60, cast=int)

APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25

# Set to '1' in production to start the wallet scanner scheduler on app startup.
# In development, the scheduler starts automatically when using `runserver`.
DJANGO_RUN_SCHEDULER = config('DJANGO_RUN_SCHEDULER', default='0')
