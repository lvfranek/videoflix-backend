"""
Django settings for the Videoflix backend.

All environment-specific values are read from the .env file; see
.env.template for the full list of variables.

- Access tokens live 30 minutes because the frontend refreshes them
  every 20 minutes.
- Activation and password reset links are valid for 24 hours, as
  stated in the emails.
- The frontend runs on another origin and sends cookies, so CORS
  allows the origins from CSRF_TRUSTED_ORIGINS with credentials.
- Emails are sent via SMTP once real server data is in .env;
  otherwise they are printed to the console.
- Behind an HTTPS reverse proxy (e.g. Caddy) Django trusts the
  X-Forwarded-Proto header, so absolute URLs use https.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def env_bool(name, default=False):
    """
    Interpret common truthy strings ("true", "1", "yes") from the
    environment.
    """
    return os.getenv(name, str(default)).strip().lower() in (
        'true',
        '1',
        'yes',
    )


def env_list(name, default=''):
    """
    Split a comma-separated environment variable into a clean list.
    """
    return [
        item.strip()
        for item in os.getenv(name, default).split(',')
        if item.strip()
    ]


BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = env_bool('DEBUG')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')

CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500'
)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_rq',
    'auth_app',
    'video_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': int(os.getenv('DB_PORT', 5432)),
    }
}


CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_LOCATION', 'redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'videoflix',
    }
}


RQ_QUEUES = {
    'default': {
        'HOST': os.getenv('REDIS_HOST', 'redis'),
        'PORT': int(os.getenv('REDIS_PORT', 6379)),
        'DB': int(os.getenv('REDIS_DB', 0)),
        'DEFAULT_TIMEOUT': 900,
    },
}


AUTH_USER_MODEL = 'auth_app.User'

PASSWORD_RESET_TIMEOUT = 60 * 60 * 24


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'auth_app.authentication.CookieJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}


CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS

CORS_ALLOW_CREDENTIALS = True


PASSWORD_VALIDATION = 'django.contrib.auth.password_validation'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': f'{PASSWORD_VALIDATION}.UserAttributeSimilarityValidator'},
    {'NAME': f'{PASSWORD_VALIDATION}.MinimumLengthValidator'},
    {'NAME': f'{PASSWORD_VALIDATION}.CommonPasswordValidator'},
    {'NAME': f'{PASSWORD_VALIDATION}.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


PLACEHOLDER_EMAIL_HOSTS = ('', 'smtp.example.com')


def build_smtp_options(host):
    """Collect the SMTP connection settings from the environment."""
    return {
        'host': host,
        'port': int(os.getenv('EMAIL_PORT', 587)),
        'username': os.getenv('EMAIL_HOST_USER', ''),
        'password': os.getenv('EMAIL_HOST_PASSWORD', ''),
        'use_tls': env_bool('EMAIL_USE_TLS', True),
        'use_ssl': env_bool('EMAIL_USE_SSL'),
        'timeout': 10,
    }


def build_default_mailer():
    """
    Send emails via SMTP once real server data is in .env, otherwise
    print them to the console.
    """
    host = os.getenv('EMAIL_HOST', '')
    if host in PLACEHOLDER_EMAIL_HOSTS:
        return {'BACKEND': 'django.core.mail.backends.console.EmailBackend'}
    return {
        'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'OPTIONS': build_smtp_options(host),
    }


MAILERS = {'default': build_default_mailer()}

DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL', 'Videoflix <noreply@videoflix.local>'
)


FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://127.0.0.1:5500').rstrip('/')
