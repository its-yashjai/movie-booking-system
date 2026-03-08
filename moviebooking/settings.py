
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

def env(key, default=None):
    return os.environ.get(key, default)

SECRET_KEY = "django-insecure-%ejejq7abc9^3iy8@#2x-9d#*cr&$lnau%!y@2e)+84d73z(_b"

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

_allowed_hosts = os.environ.get('ALLOWED_HOSTS', '*')
if _allowed_hosts == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',')]

if not any('railway.app' in host or host == '*' for host in ALLOWED_HOSTS):
    ALLOWED_HOSTS.append('moviebookingapp-production-0bce.up.railway.app')

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "movies",
    "bookings",
    "embed_video",
    "custom_admin",
    "cloudinary_storage",
    "cloudinary",
]

try:
    import debug_toolbar
    INSTALLED_APPS.append("debug_toolbar")
    HAS_DEBUG_TOOLBAR = True
except ImportError:
    HAS_DEBUG_TOOLBAR = False

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Serve static files in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if HAS_DEBUG_TOOLBAR:
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = "moviebooking.urls"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'email_templates'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ] if not DEBUG else [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]

WSGI_APPLICATION = "moviebooking.wsgi.application"

if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {
                "timeout": 20,  # Wait up to 20 seconds for locks to be released
            },
        }
    }
    from django.db.backends.signals import connection_created
    from django.dispatch import receiver
    
    @receiver(connection_created)
    def setup_sqlite_pragmas(sender, connection, **kwargs):

        if connection.vendor == 'sqlite':
            cursor = connection.cursor()
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=NORMAL;')  # Faster writes with WAL
            cursor.execute('PRAGMA busy_timeout=20000;')  # 20 second timeout
            cursor.close()

if not DEBUG:
    DATABASES['default']['CONN_MAX_AGE'] = 600
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'moviebooking',
    }
}

CSRF_TRUSTED_ORIGINS = [
    'https://moviebookingapp-production-0bce.up.railway.app',
    'https://*.railway.app',
    'https://*.up.railway.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://*.onrender.com',
]

CSRF_COOKIE_SECURE = not DEBUG  # Secure only in production
CSRF_COOKIE_HTTPONLY = False   # Must be False so JavaScript can read it for AJAX
CSRF_COOKIE_SAMESITE = 'Lax'   # Allows same-site form submissions

SESSION_COOKIE_SECURE = not DEBUG  # Secure only in production
SESSION_COOKIE_HTTPONLY = True     # Prevent JavaScript access to session cookies
SESSION_COOKIE_SAMESITE = 'Lax'    # Allow same-site requests

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0  # Disable HSTS to prevent redirect loops
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if DEBUG:
    
    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.history.HistoryPanel',
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
    ]
    

SESSION_ENGINE="django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS="default"

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

SEAT_RESERVATION_TIMEOUT=720  # 12 minutes to match Razorpay timeout 

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
if not any('onrender.com' in host or host == '*' for host in ALLOWED_HOSTS):
    ALLOWED_HOSTS.append('.onrender.com')
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailBackend',  # Custom email-based authentication
    'django.contrib.auth.backends.ModelBackend',  # Default username-based authentication
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'profile'  # Redirect to profile after login
LOGOUT_REDIRECT_URL = 'home'   # Redirect to home after logout

import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', 'drdvl5dab'),
    api_key=os.environ.get('CLOUDINARY_API_KEY', '858736468657877'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', '_Xj5H6Cl9l8vD6pzYi02eBLG0vk')
)

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
MEDIA_URL = '/media/'  # Cloudinary handles the actual URL transformation
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', 'drdvl5dab'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', '858736468657877'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', '_Xj5H6Cl9l8vD6pzYi02eBLG0vk')
}
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')

REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1')

RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')

if SENDGRID_API_KEY:
    EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
    ANYMAIL = {
        'SENDGRID_API_KEY': SENDGRID_API_KEY,
    }
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@moviebooking.com')
    print("✅ EMAIL: Using SendGrid backend (SENDGRID_API_KEY is set)")
elif not DEBUG:
    import warnings
    warnings.warn(
        "⚠️  WARNING: SENDGRID_API_KEY not set in production! "
        "Emails will use console backend (LOGGED ONLY, NOT SENT). "
        "Please set SENDGRID_API_KEY environment variable. "
        "Free tier limit: 100 emails/day."
    )
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@moviebooking.com')
    print("❌ EMAIL: Using console backend (SENDGRID_API_KEY not set in production)")
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@moviebooking.com')
    print("🧪 EMAIL: Using console backend (development mode)")

SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} | {name} | {funcName}:{lineno}d | {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'verbose',
            'stream': 'ext://sys.stdout',
        },
        'console_debug': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'stream': 'ext://sys.stdout',
            'filters': ['require_debug_true'],
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'verbose',
            'filename': os.path.join(BASE_DIR, 'logs', 'movie_booking.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'bookings.email_utils': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'anymail': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'bookings.razorpay_utils': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'bookings.views': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts.email_utils': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts.views': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console_debug'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

