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
    'rest_hooks',
    'django_xhtml2pdf',

    # Dev tools
    'django_extensions',
]

INTERNAL_APPS = [
    'silver',
]

INSTALLED_APPS = EXTERNAL_APPS + INTERNAL_APPS

ROOT_URLCONF = 'silver.urls'
STATIC_URL = '/static/'
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_DIRS = (PROJECT_ROOT + '/silver/templates/',)

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
    'PAGINATE_BY': 30,
    'PAGINATE_BY_PARAM': 'per_page',
    'MAX_PAGINATE_BY': 100,
}

from silver import HOOK_EVENTS as _HOOK_EVENTS
HOOK_EVENTS = _HOOK_EVENTS

# DEFAULT_TARGET_URL = 'http://presslabs.com/api'

PAYMENT_DUE_DAYS = 5
