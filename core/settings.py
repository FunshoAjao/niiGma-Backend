import os
from decouple import config
from pathlib import Path
from datetime import timedelta
import dj_database_url
import firebase_admin
from firebase_admin import credentials

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'niigma-backend-service.onrender.com',
    'localhost',
    '127.0.0.1'
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

SYSTEM_APP = [
    'accounts',
    'calories',
    'symptoms',
    'ovulations',
    'mindspace',
    'reminders',
]

THIRD_PARTY_APP = [
    'celery',
    'corsheaders',
    'drf_spectacular',
    'drf_yasg',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_redis',
]

INSTALLED_APPS += SYSTEM_APP + THIRD_PARTY_APP

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
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
        'DIRS': [os.path.join(BASE_DIR, 'accounts/services/templates')],
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

WSGI_APPLICATION = 'core.wsgi.application'

# Email settings
EMAIL_BACKEND = config("EMAIL_BACKEND")
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = False
EMAIL_USE_SSL = config("EMAIL_USE_SSL")

# Database
ENVIRONMENT = config("ENVIRONMENT")
if ENVIRONMENT == "testing":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DBNAME_DEV'),
            'USER': config('DATABASE_USER'),
            'HOST': config('DATABASE_HOST'),
            'PORT': config('DATABASE_PORT'),
            'PASSWORD' : config('DATABASE_PASSWORD')
        }
    }
    
elif ENVIRONMENT == "prod":
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600)
    }

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    "EXCEPTION_HANDLER": "common.exception_handlers.custom_exception_handler",
    'DEFAULT_PAGINATION_CLASS': 'utils.pagination.CustomPageNumberPagination',
    'PAGE_SIZE': 10
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=4),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SPECTACULAR_SETTINGS = {
    'TITLE': 'Niigma-Backend',
    'DESCRIPTION': 'Backend documentation for the Niigma project',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

OPENAI_API_KEY = config("OPENAI_API_KEY")


# Redis Configuration
REDIS_URL=config("REDIS_HOST")
REDIS_HOST = config("REDIS_HOST")
REDIS_PORT = config("REDIS_PORT")

# Celery configuration
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BROKER_URL = REDIS_URL

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        "KEY_PREFIX": 'core',
        "TIMEOUT": 300
    }
}

if ENVIRONMENT == "prod":
    import sentry_sdk

    sentry_sdk.init(
        dsn="https://89326407107b0a6506a6a83b2511ab05@o4508864956858368.ingest.us.sentry.io/4509286400786432",
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
    )
    
# FCM Settings
FIREBASE_SERVICE_ACCOUNT_KEY = {
    "type": config("TYPE"),
    "project_id": config("PROJECT_ID"),
    "private_key_id": config("PRIVATE_KEY_ID"),
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDgM/UPukAHgH/e\nbPnCADMjGLigifLvLovpD0+tpnbFfy02DVFzonX13xhKJAe4QXFGpXAfR1xZ7061\nh8ITtn1obPkr+rxSgN2R+GhpdErph4t8nVT3ZDrm/WdlYj5VfdVYHXWB0WCTzssR\nUoNm8tX7cMiUjvLupWHcgmriYTLCvk8EBLv/E9nB7SHUlShqCmuT/6gDLLV8bY03\naYZ9VqeHso7roX2IYJeoCCsxVx30hKD1TmH/OpgC4RRUFSpLkxEF9G1gZL855N8d\nZpezTZKIJ7RC7FEcFyIVKjd014ulxfGFmP7VIrsHr9WlOogIewRXNVVznx7UoGKg\nnbNpADtDAgMBAAECggEARA0BMQjjLmO+bBC/rjbJTrnOMEwuxJJoPRE8qgSAwGld\nm65nLqX9D+frQ3W0MiUK8Np+McBDM7kDNu5B5iHZ5rxM1SCB0Lj0h73SU0/M/Rz7\nJZPLmlt91WbM32T2bpSHEPvAEusuWS7HTDazU6gZcvxEpXLOIclo7rlXH+dItPrl\nFnWHe5eM1r/RIcAL9GdZxaflHHSoj3S3SXljGe5llltYNh5aGCV/KejMa6+VBRed\nlBZmV5TPP4FOfShvetW+Dw+UKn+csaEM7Sf6U01Y/sf62xLvvlRcacVu7e/ecXFJ\netUm+Vz85AXkUk0FuMzsoZmzYEqzFhwaAtno5xmsoQKBgQD3W78sSOmPKWqC0j3L\nUye+r9lAruh6ff4EQr6wda1ek9GwSfDzoshxWtO8TRW7AJAY1t0ABNtZHB4KLI6H\nuIdmZiklru49Hj3Odp4OtEZt+kWXO8VOit7qlYobJZYrxPR7Qb4YY30XquUjeP5p\nE2ieGJUTiHclmsc7kigkaTBeXQKBgQDoCR6eeKlVYGQLc/1Og+y8rpdp5geGWy69\nib0noZzVX/hcrq44K00AKf6OpbWqjNYtQ5w7jMlOL7Lz74gepU31aU8tNPDHYaPk\nWh75LQ2tOgNY24cIHE/PVMWhByZyV4eoCvAjJ9P9pE90CVDDZ+/JqufZzfEAyGa3\nKCXShn8mHwKBgG69KE0PJ2DsTb7bmMaaJ8T6vOx0YafVGA+YQf6F8GPTEaE2uSSZ\nz9rPqtM2P3BExD4akz4a7ohqShiL8hNYzWVOf0Vbl1TNYSY5fHFgy9cYoGcgXyjW\niw3CfN3CagSWXE2CFTSd9bbOz16eIGeyRLfikXr5MT4omOFWgZorbXgRAoGAfWUY\nR/nbQQljZ5EaTkkbMeiEaTVn0aMLQmDieT1sfR9tH+FCw5Ya+cC4EazZ3T5ZLIMC\nNmhiDb/XTN6gyDb7R2nO4RZgHM/Wezx8ypofbwMP9gBFHAv40Yn1d41eqKJG7Hhk\nyArpFISsb3/tRnyv6GNVAq651Ht4jvjCX+BRbG8CgYBsxN1Sack71gvGDjTjgDtz\nWXDZlAZCq09u9PI0TNFW6aBz9pNmOVykS4y147cIWG+kHdGraJCZiSQTNCnbJ0dH\nu69voIH5IQ6+S9MO9rR/5mMApRRItPAt2HCmVG4hqicfYq50bFnG+ngnmFU/vvY0\nulfnXXWm1MQAxCpN0QYf/g==\n-----END PRIVATE KEY-----\n", #config("PRIVATE_KEY").replace("\n", "\\n"),
    "client_email": config("CLIENT_EMAIL"),
    "client_id": config("CLIENT_ID"),
    "auth_uri": config("AUTH_URI"),
    "token_uri": config("TOKEN_URI"),
    "auth_provider_x509_cert_url": config("AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": config("CLIENT_X509_CERT_URL"),
}

FIREBASE_CREDENTIALS = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY)
# FIREBASE_CREDENTIALS = credentials.Certificate('https://hauliin-bucket.ams3.cdn.digitaloceanspaces.com/hauliin-bucket/media/Backend-Credential-(FireBase)/hauliin-firebase-adminsdk-o83nv-f1c4fd1bf5.json')
FCM_SERVER_KEY = config('FCM_SERVER_KEY')
FCM_DJANGO_SETTINGS = {
    "DEFAULT_FIREBASE_APP": firebase_admin.initialize_app(
        credential=FIREBASE_CREDENTIALS
    ),
    "APP_VERBOSE_NAME": "",
    "ONE_DEVICE_PER_USER": True,
    "DELETE_INACTIVE_DEVICES": False,
}