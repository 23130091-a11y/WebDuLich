"""
Django settings for travel_project project.

Cấu hình theo 12-factor: mọi giá trị nhạy cảm đọc từ environment variables.
- Dev local:  USE_LOCAL_DB=true + file .env (xem .env.example)
- Production (Railway): DATABASE_URL tự inject, SECRET_KEY/ALLOWED_HOSTS/DJANGO_DEBUG
  đặt trong Variables của Railway. DJANGO_DEBUG mặc định là False (an toàn mặc định).
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    # Chỉ dùng fallback insecure khi dev. Production bắt buộc đặt env SECRET_KEY.
    'django-insecure-#05+7kdse&hdu$&w2#u#7utz77m(n4d7rb0&+e0@vqa^(rcf1_',
)

DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() in ('1', 'true', 'yes')

# Django test runner luôn chạy ở chế độ dev (SSL redirect sẽ 301 mọi POST test)
IS_TEST = 'test' in sys.argv

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv('ALLOWED_HOSTS', '').split(',')
    if h.strip()
]
if DEBUG:
    ALLOWED_HOSTS += ['localhost', '127.0.0.1', 'testserver']

# Production không được phép chạy với cấu hình thiếu an toàn. Fail-fast thay
# vì chạy "tạm ổn" — lỗi cấu hình phải xuất hiện lúc deploy, không phải lúc
# bị tấn công.
if not DEBUG and not IS_TEST:
    if not os.getenv('SECRET_KEY'):
        raise RuntimeError(
            'SECRET_KEY chưa đặt trong environment variables — '
            'bắt buộc cấu hình khi chạy production (xem .env.example).'
        )
    if not ALLOWED_HOSTS:
        raise RuntimeError(
            'ALLOWED_HOSTS chưa đặt trong environment variables — '
            'bắt buộc cấu hình khi chạy production (xem .env.example).'
        )

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'taggit',

    'drf_spectacular',

    'travel',
    'users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'myproject.urls'
WSGI_APPLICATION = 'myproject.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

# ---------------------------------------------------------------------------
# Database
# Thứ tự ưu tiên:
#   1. DATABASE_URL (chuẩn Railway / dj-database-url)
#   2. Biến PG* riêng lẻ (fallback)
#   3. USE_LOCAL_DB=true → SQLite cho dev
# ---------------------------------------------------------------------------
USE_LOCAL_DB = os.getenv('USE_LOCAL_DB', 'false').lower() in ('1', 'true', 'yes')
DATABASE_URL = os.getenv('DATABASE_URL', '')

if DATABASE_URL:
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
elif not USE_LOCAL_DB and os.getenv('PGHOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('PGDATABASE', 'railway'),
            'USER': os.getenv('PGUSER', 'postgres'),
            'PASSWORD': os.getenv('PGPASSWORD'),
            'HOST': os.getenv('PGHOST'),
            'PORT': os.getenv('PGPORT', '5432'),
            'OPTIONS': {'sslmode': 'require'},
            'CONN_MAX_AGE': 600,
        }
    }
else:
    # Dev local: SQLite. (USE_LOCAL_DB=true hoặc không cấu hình gì.)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ---------------------------------------------------------------------------
# Security hardening (chỉ hiệu lực khi DEBUG=False)
# ---------------------------------------------------------------------------
if not DEBUG and not IS_TEST:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'true').lower() in ('1', 'true')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 ngày
    SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Session cookie luôn HttpOnly (chống đánh cắp qua XSS) kể cả khi dev
SESSION_COOKIE_HTTPONLY = True

# Admin URL không dùng đường dẫn mặc định /admin/ — chống scan bot.
# Đổi trong production bằng env ADMIN_URL_PATH (ví dụ: /quan-tri-xyz123/).
ADMIN_URL_PATH = os.getenv('ADMIN_URL_PATH', 'admin/')

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Redirect khi @login_required chặn khách (session hết hạn...). Về trang chủ —
# nơi có auth modal (baseIndex.html). KHÔNG trỏ /accounts/login/ vì không có
# template registration/login.html → sẽ 500 thay vì hiện trang đăng nhập.
LOGIN_URL = '/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# DRF / JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # SessionAuthentication: cho phép session (đặt bởi login/register Django)
        # dùng được với API logout/preferences. LƯU Ý đi kèm: nó ép CSRF trên
        # các request session-based, nên frontend phải gửi X-CSRFToken cho
        # những fetch đó (đã thêm trong index.js / baseIndex.html).
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/min',
        'login': '10/min',
        'register': '5/h',
    },
}

SIMPLE_JWT = {
    # Access token ngắn để giảm thiệt hại nếu token bị lộ.
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
# django-ratelimit resolve dotted path qua import_string nên string này OK
# (trỏ sang travel.views.get_client_ip). Hàm đó chỉ tin X-Forwarded-For
# khi TRUST_X_FORWARDED_FOR=True — bật khi chạy sau proxy mình kiểm soát
# (Railway/nginx), dev local giữ False để dùng REMOTE_ADDR (chống spoof).
RATELIMIT_IP_META_KEY = 'travel.views.get_client_ip'
TRUST_X_FORWARDED_FOR = os.getenv('TRUST_X_FORWARDED_FOR', 'false').lower() in ('1', 'true', 'yes')

# ---------------------------------------------------------------------------
# Static / media files
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'travel/static')]
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        # Lưu ý: phải dùng StaticFilesStorage (không phải FileSystemStorage
        # trần) cho dev/test — FileSystemStorage không OPTIONS sẽ mặc định
        # lấy MEDIA_ROOT/MEDIA_URL, làm {% static %} render thành /media/... (404).
        # Manifest storage (production) yêu cầu collectstatic đã chạy.
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if (DEBUG or IS_TEST)
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Cache timeouts (in seconds)
CACHE_TTL = {
    'homepage': 300,       # 5 minutes
    'search': 600,        # 10 minutes
    'destination_detail': 300,  # 5 minutes
    'sentiment': 86400,   # 24 hours (AI results don't change)
    'recommendation': 3600,  # 1 hour
    'weather': 600,       # 10 minutes
}

# Lưu ý: cache backend mặc định là LocMemCache (per-process).
# Khi chạy >= 2 worker (Railway scaling > 1), cần chuyển sang Redis:
#   CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#                        'LOCATION': os.environ['REDIS_URL']}}
# Chưa thêm bây giờ để tránh over-engineering ở quy mô hiện tại.

# ---------------------------------------------------------------------------
# External services
# ---------------------------------------------------------------------------
# OpenWeatherMap API Key (for weather service) — https://openweathermap.org/api
OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')

# Meilisearch Cloud (https://cloud.meilisearch.com) — search engine cho api_search.
# Để trống → hệ thống tự dùng ORM search (icontains + fuzzy) làm fallback,
# mọi view vẫn hoạt động bình thường khi chưa cấu hình hay khi cloud gặp sự cố.
MEILI_HOST = os.getenv('MEILI_HOST', '')
MEILI_API_KEY = os.getenv('MEILI_API_KEY', '')

# Email config (Gmail SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# Nếu SMTP lỗi trong dev, đổi sang: 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'webmaster@localhost'

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.request': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}
