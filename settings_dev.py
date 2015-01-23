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
    'rest_hooks'

    # Dev tools
    'django_extensions',
]

INTERNAL_APPS = [
    'silver',
]

INSTALLED_APPS = EXTERNAL_APPS + INTERNAL_APPS

ROOT_URLCONF = 'silver.urls'
STATIC_URL = '/static/'

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

from django.contrib import messages

MESSAGE_TAGS = {
    messages.SUCCESS: 'alert-success success',
    messages.WARNING: 'alert-warning warning',
    messages.ERROR: 'alert-danger error'
}

HOOK_EVENTS = {
    # 'any.event.name': 'App.Model.Action' (created/updated/deleted)
    'customer.created': 'silver.Customer.created+',
    'customer.updated': 'silver.Customer.updated+',
    'customer.deleted': 'silver.Customer.deleted+',

    'plan.created': 'silver.Plan.created+',
    'plan.updated': 'silver.Plan.updated+',
    'plan.deleted': 'silver.Plan.deleted+',

    'subscription.created': 'silver.Subscription.created+',
    'subscription.updated': 'silver.Subscription.updated+',
    'subscription.deleted': 'silver.Subscription.deleted+',

    'metered-feature.created': 'silver.MeteredFeature.created+',
    # changing metered features is not enabled through the API, but this can
    # still be done through the admin panel
    'metered-feature.updated': 'silver.MeteredFeature.updated+',
    'metered-feature.deleted': 'silver.MeteredFeature.deleted+',

    'mf-units-log.created': 'silver.MeteredFeatureUnitsLog.created+',
    'mf-units-log.updated': 'silver.MeteredFeatureUnitsLog.updated+',
    # removing logs is not enabled through the API, but this can still be done
    # through the admin panel
    'mf-units-log.deleted': 'silver.MeteredFeatureUnitsLog.deleted+',

    'provider.created': 'silver.Provider.created+',
    'provider.updated': 'silver.Provider.updated+',
    'provider.deleted': 'silver.Provider.deleted+',
}

# DEFAULT_TARGET_URL = 'http://presslabs.com/api'
