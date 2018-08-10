# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import datetime

from silver import HOOK_EVENTS as _HOOK_EVENTS
from django.utils.log import DEFAULT_LOGGING as LOGGING

"""
These settings are used by the ``manage.py`` command.

"""

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
    # Django autocomplete
    'dal',
    'dal_select2',

    # Django core apps
    # 'django_admin_bootstrapped',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',

    # Required apps
    'django_fsm',
    'rest_framework',
    'django_filters',

    # Dev tools
    # 'django_extensions',
]

INTERNAL_APPS = [
    'silver',
]

INSTALLED_APPS = EXTERNAL_APPS + INTERNAL_APPS

ROOT_URLCONF = 'silver.urls'
PROJECT_ROOT = os.path.dirname(__file__)

FIXTURE_DIRS = (
    PROJECT_ROOT,
    PROJECT_ROOT + '/silver/'
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [
            PROJECT_ROOT + '/payment_processors/templates/',
            PROJECT_ROOT + '/templates/',
            PROJECT_ROOT + '/silver/templates/',
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

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

SECRET_KEY = 'secret'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'silver.api.pagination.LinkHeaderPagination'
}

HOOK_EVENTS = _HOOK_EVENTS

SILVER_DEFAULT_DUE_DAYS = 5
SILVER_DOCUMENT_PREFIX = 'documents/'
SILVER_DOCUMENT_STORAGE = None
SILVER_PAYMENT_TOKEN_EXPIRATION = datetime.timedelta(minutes=5)
SILVER_AUTOMATICALLY_CREATE_TRANSACTIONS = True

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
LOGGING['formatters'] = LOGGING.get('formatters', {})
LOGGING['formatters']['verbose'] = {
    'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
    'datefmt': "%d/%b/%Y %H:%M:%S"
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

PAYMENT_PROCESSORS = {
    'manual': {
        'class': 'silver.payment_processors.manual.ManualProcessor'
    },
}

PAYMENT_METHOD_SECRET = b'YOUR_FERNET_KEY_HERE'  # Fernet.generate_key()

CELERY_BROKER_URL = 'redis://localhost:6379/'
CELERY_BEAT_SCHEDULE = {
    'generate-pdfs': {
        'task': 'silver.tasks.generate_pdfs',
        'schedule': datetime.timedelta(seconds=5)
    },
}
LOCK_MANAGER_CONNECTION = {'host': 'localhost', 'port': 6379, 'db': 1}

PDF_GENERATION_TIME_LIMIT = 60

TRANSACTION_SAVE_TIME_LIMIT = 5

try:
    from settings_local import *
except ImportError:
    pass
