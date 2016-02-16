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


"""
These settings are used by the ``manage.py`` command.

"""
import os

DEBUG = False

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
    #'django_extensions',
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
    'DEFAULT_PAGINATION_CLASS': 'silver.api.pagination.LinkHeaderPagination'
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
LOGGING['formatters'] = {}
LOGGING['formatters']['verbose'] = {
    'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
    'datefmt': "%d/%b/%Y %H:%M:%S"
}
