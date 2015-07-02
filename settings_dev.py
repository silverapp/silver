"""
These settings are used by the ``manage.py`` command.

"""
import os

DEBUG = True

SITE_ID = 1

USE_TZ = True
TIME_ZONE = 'UTC'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite',
    }
}

EXTERNAL_APPS = [
    # Django core apps
    #'django_admin_bootstrapped',
    'flat',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',

    # Required apps
    'international',
    'django_fsm',
    'rest_framework',
    'django_filters',
    'django_xhtml2pdf',

    # Dev tools
    # 'django_extensions',
]

INTERNAL_APPS = [
    'silver',
]

INSTALLED_APPS = EXTERNAL_APPS + INTERNAL_APPS

ROOT_URLCONF = 'silver.urls'
PROJECT_ROOT = os.path.dirname(__file__)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [
            PROJECT_ROOT + '/templates/',
            PROJECT_ROOT + '/silver/templates/'
        ],
        'OPTIONS': {
            'context_processors': (
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages"
            )
        }
    }
]

MEDIA_ROOT = PROJECT_ROOT + '/app_media/'
MEDIA_URL = '/app_media/'

STATIC_ROOT = PROJECT_ROOT + '/app_static/'
STATIC_URL = '/app_static/'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

SECRET_KEY = 'secret'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'silver.api.pagination.LinkHeaderPagination',
    'PAGINATE_BY': 30,
    'PAGINATE_BY_PARAM': 'per_page',
    'MAX_PAGINATE_BY': 100,
}

from silver import HOOK_EVENTS as _HOOK_EVENTS
HOOK_EVENTS = _HOOK_EVENTS

SILVER_DEFAULT_DUE_DAYS = 5
SILVER_DOCUMENT_PREFIX = 'documents/'
SILVER_DOCUMENT_STORAGE = None

from django.utils.log import DEFAULT_LOGGING as LOGGING

LOGGING['loggers']['xhtml2pdf'] = {
    'level': 'DEBUG',
    'handlers': ['console']
}

LOGGING['loggers']['pisa'] = {
    'level': 'DEBUG',
    'handlers': ['console']
}

LOGGING['loggers']['django'] = {
    'level': 'DEBUG',
    'handlers': ['console']
}

LOGGING['loggers']['django.security'] = {
    'level': 'DEBUG',
    'handlers': ['console']
}

import sys

debug = 1

LOGGING['loggers']['silver'] = {
    'level': 'DEBUG' if debug else 'INFO',
    'handlers': ['dev-test']
}

LOGGING['handlers']['dev-test'] = {
    'class': 'logging.StreamHandler',
    'stream': sys.stdout,
}

