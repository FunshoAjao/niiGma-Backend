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
if config("ENVIRONMENT") == "prod":
    DEBUG = False
if config("ENVIRONMENT") == "testing":
    DEBUG = True

ALLOWED_HOSTS = [
    'niigma-backend-service.onrender.com',
    'niigma-backend-service-6gdy.onrender.com',
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
    'django_filters',
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
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
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
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCvvnsqLF35JJO1\nAoY5bQuKIDAOcVvXzTEkrybxFIia9YG4GphAcBqHM8DtGp5nrM4w022sQDNJgZaJ\nkwvf3fZp1eQWHmY2J7YsCMrQanyFjOokHs7j4Tp9w+fXmLSpVHnWaWV8Iy7wxWzO\n8ZLQgX8x9sZMIEmi0AKv5Zumik3ubx39GObpwdqLIFsMwhAFBvSbe2QRmpviEoiR\nkuIWak9X2hJrTy9hBpd/ljBOkkT4tG/975LCkSXDCnvvIR9DtAuElwRr6zRPiLCh\n6UV1l5lsR898c9NMQpL+E4Pxf94cStQkZ9cARAZH/JVzJfLZTqxYTPllnZjkWxDz\nmcr5CvcNAgMBAAECggEAGhUklWVBSy0tCNPHlPVEnaraRwJ29Ye8D+w41NXN0mW2\na1rzFrksjr1VGDt3n/5rGZ7/a22ZzwJ/E4rx27dHD30RnWDEnav2IwHpC9aKBY4c\n3+B8pyBxvGGbYomE4o6piHNa/vn/yPccB3id5/kYJhOwaXLvSs0hYPasS6LCHy06\nqSDogHTQD0mz5caSbsW2PyAUrNVA6PrwyeVDKPkpMnXSiDPU0LhYpSpZr/Hs2+7y\ntUXULDzm8T4aosZ4h3AhX6/kv5CYo1cwfmvKfogR6j8vugS8Ad5o8rz1QXqOuTne\nN4xhEEP+0kjMsjMVXV/w040Yk0JKsMqESNHh/vM30QKBgQDWFZGFw92BRiEM9B0L\nRO0uxdOx8Q5cyVh/Ps9RqBBC6hFfLhB1QwyFwOf2NkkMkRPQdKIVxvAjcO62eMko\nphyZbqfb2Zp/gFQ30HoxaBvte8/PAhkDNvnhXTMFqizSqRR8fBYR3eDiOYuwF4OU\nlyqjZD6aJXsspLd7XqXeBtQXJQKBgQDSJzU3+WPXdRcDrW53FoFDDjiQxN1RgEya\nxWYPu+UNZkTnWhT/Fj9pmaYO+aWRlIVg4EnvvFdE7rXZ1kbSNFj0QVrcaolyUF/J\nHfbq08nNswkamFInJX/JPyCiiS57K5tR7AZSPo+lOhN8v+6MnzMfxdqLgtvY9eYD\nfBOARqEvyQKBgDQH2e5gxBz/Jlk3mzd58QtFGUZOB+eVJ+UFJu35orogmUhAsc9O\nFGUNlVLJrsdXGzG2pw4T45k5gUrn4Dv440qHElTkdiA22EEYcho/60m0pbTyFZIq\ncmDLffMKgQpR/aCjp9l/y4Av7DtH+7rJYpuDaZOdOGqJPe7F+hoUHsfhAoGBAIAe\nKxGu1rF5zsgNKXUsoS1SNCX9/rc7MniAs5IQCLo8iPFKN9azp4EnjNdAVzIDi7Td\nx/WBqup5ZSAixBZOl5SBa3VI9fZdDag8vlW3PCZNadVu21bGQ7ta4vh0DYRFt3Eg\nJVJqlYQzfcHl+PZ979sE8hFve7wvXUTulaz0YjwRAoGAYVYBZJ9nQtIrybhiE+Mh\nMvK2yYhAuJVyt7EmuhCun8tCGgt/nWSSrUU4DtOQZAsaqFdeIamvYmYSWqeu2fDH\nKbXvfl7g23QgnCoAdT7//uR9fbYoB6ENt7AX6E7Yc548OUgWqzwyKMoF0eRgisdS\nEIPsp6vKozdmbMw4K/moJM4=\n-----END PRIVATE KEY-----\n", #config("PRIVATE_KEY").replace("\n", "\\n"),
    "client_email": config("CLIENT_EMAIL"),
    "client_id": config("CLIENT_ID"),
    "auth_uri": config("AUTH_URI"),
    "token_uri": config("TOKEN_URI"),
    "auth_provider_x509_cert_url": config("AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": config("CLIENT_X509_CERT_URL"),
}

FIREBASE_CREDENTIALS = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY)
FCM_SERVER_KEY = config('FCM_SERVER_KEY')
FCM_DJANGO_SETTINGS = {
    "DEFAULT_FIREBASE_APP": firebase_admin.initialize_app(
        credential=FIREBASE_CREDENTIALS
    ),
    "APP_VERBOSE_NAME": "",
    "ONE_DEVICE_PER_USER": True,
    "DELETE_INACTIVE_DEVICES": False,
}
