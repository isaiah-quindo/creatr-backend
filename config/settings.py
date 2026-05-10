"""
Django settings for config project.
"""

from pathlib import Path
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# Default to False so an unconfigured production deploy fails closed instead
# of leaking stack traces. Local dev sets DJANGO_DEBUG=True in backend/.env.
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-only-do-not-use-in-prod"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY environment variable is required when DEBUG=False."
        )

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',

    'rest_framework',
    'corsheaders',

    # Local apps
    'accounts',
    'creators',
    'inquiries',
    'embeds',
    'ai_tools',
]

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'accounts.auth_backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise serves collected static files in production; must sit
    # immediately after SecurityMiddleware per WhiteNoise's docs.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'


# Database — Supabase Postgres (via DATABASE_URL).
# Falls back to SQLite if DATABASE_URL is empty so `manage.py` still works
# before credentials are filled in.
_database_url = os.environ.get("DATABASE_URL", "").strip()
if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=0,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
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
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise compressed-manifest storage in production; default storage in
# dev so missing collectstatic doesn't break `runserver`.
if not DEBUG:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Production hardening — only flip these on when DEBUG=False so dev over HTTP
# still works. Railway terminates TLS at the edge and forwards X-Forwarded-Proto.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Share the session/CSRF cookies across creatr.ph and api.creatr.ph by
    # setting SESSION_COOKIE_DOMAIN=.creatr.ph in the backend's env.
    _cookie_domain = os.environ.get("SESSION_COOKIE_DOMAIN", "").strip()
    if _cookie_domain:
        SESSION_COOKIE_DOMAIN = _cookie_domain
        CSRF_COOKIE_DOMAIN = _cookie_domain


# CORS — allow the Next.js dev server to call the API
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000").split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

# CSRF — frontend running on a different port still counts as cross-origin.
# In prod, the frontend (creatr.ph) and backend (api.creatr.ph) are separate
# origins, so set CSRF_TRUSTED_ORIGINS explicitly. Falls back to the CORS
# allowlist for dev where they're typically the same.
_csrf_trusted = os.environ.get("CSRF_TRUSTED_ORIGINS", "").strip()
CSRF_TRUSTED_ORIGINS = (
    [o.strip() for o in _csrf_trusted.split(",") if o.strip()]
    if _csrf_trusted
    else list(CORS_ALLOWED_ORIGINS)
)


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
}


# Supabase (consumed by backend/integrations/supabase.py)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "creatr-media")


# Google Sign-In (Web client ID from https://console.cloud.google.com/apis/credentials)
# The same value is also exposed to the frontend as NEXT_PUBLIC_GOOGLE_CLIENT_ID.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")


# Email — Resend in production (HTTP API), Mailtrap SMTP in dev.
# accounts/emails.py uses RESEND_API_KEY when set; otherwise falls through to
# Django's SMTP backend pointed at EMAIL_HOST/PORT/USER/PASSWORD.
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "sandbox.smtp.mailtrap.io")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "2525"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "Creatr <onboarding@resend.dev>",
)

# Public URL of the Next.js frontend — used to build the link in verification emails.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")

EMAIL_VERIFICATION_TOKEN_HOURS = int(os.environ.get("EMAIL_VERIFICATION_TOKEN_HOURS", "24"))
