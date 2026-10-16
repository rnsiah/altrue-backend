"""
Test settings for Altrue Backend
"""
from .settings import *
import os

# Use SQLite for testing (faster)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Use fast password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable email sending in tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Use synchronous channel layer for tests
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Test Stripe keys (use test keys)
STRIPE_SECRET_KEY = os.getenv('STRIPE_TEST_SECRET_KEY', 'sk_test_dummy')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_TEST_PUBLISHABLE_KEY', 'pk_test_dummy')
STRIPE_ENDPOINT_SECRET = os.getenv('STRIPE_TEST_ENDPOINT_SECRET', 'whsec_dummy')

# Disable AWS S3 in tests
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = BASE_DIR / 'test_media'

# Debug mode for detailed error messages
DEBUG = True

# Allowed hosts for tests
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Disable secure redirects in tests
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Use console logging only
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
    },
}

# CORS allow all for tests
CORS_ALLOW_ALL_ORIGINS = True

# Timezone-aware datetime support for SQLite backend (audit fix 2026-10-14)
USE_TZ = True
