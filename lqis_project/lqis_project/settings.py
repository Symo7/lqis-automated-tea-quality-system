"""Django settings for lqis_project production-ready architecture."""
import os
from pathlib import Path

import dj_database_url
import sentry_sdk
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Sentry APM Integration
# Initialize Sentry early to capture any startup exceptions. Real deployment needs a DSN from sentry.io
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0, # Track 100% of performance spikes (N+1 queries/slow APIs)
        profiles_sample_rate=1.0,
    )

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-phase-1-lqis-dev-key-change-me')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS_ENV = os.environ.get('ALLOWED_HOSTS', '*')
if ALLOWED_HOSTS_ENV == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(',') if host.strip()]
    
# Render integration (from `render.yaml`)
render_external_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if render_external_hostname:
    ALLOWED_HOSTS.append(render_external_hostname)

INSTALLED_APPS = [
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary',
    'django.contrib.staticfiles',
    'users',
    'core',
    'sampling',
    'ai_engine',
    'dashboard',
    'reporting',
    'django_q',
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

ROOT_URLCONF = 'lqis_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.role_flags',
            ],
        },
    },
]

WSGI_APPLICATION = 'lqis_project.wsgi.application'
ASGI_APPLICATION = 'lqis_project.asgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=0, # Crucial: forces immediate Postgres release to prevent Free-Tier cluster lockouts
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Use WhiteNoise to serve static files efficiently
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Storage Configuration
if os.environ.get('CLOUDINARY_URL'):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = "users:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "users:login"

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' if not DEBUG else 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'your-email@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'your-app-password')
DEFAULT_FROM_EMAIL = f"LQIS Automated System <{EMAIL_HOST_USER}>"

# Django-Q2 Configuration (Background Tasks Database Broker)
Q_CLUSTER = {
    'name': 'lqis_queue',
    'workers': 1, # Limited to 1 worker so `django-q2` does not eat the 20 DB connection limit
    'recycle': 500,
    'timeout': 60,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'redis': None,
    'orm': 'default'  # Utilize PostgreSQL/SQLite as the message broker for simplicity
}

# Extensive Request and Database Profiling
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'WARNING',  # Only print warnings and above to console by default
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING', # Catch 400s (malformed JSON payload stress testing) and 500s
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': os.environ.get('DB_LOG_LEVEL', 'WARNING'), # Set DB_LOG_LEVEL=DEBUG in .env to watch queries explode
            'propagate': False,
        },
    },
}
