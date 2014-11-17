"""Settings that need to be set in order to run the tests."""
import os
import logging


logging.getLogger("factory").setLevel(logging.WARN)


TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

APP_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

COVERAGE_REPORT_HTML_OUTPUT_DIR = os.path.join(
    os.path.join(APP_ROOT, 'tests/coverage'))
COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$', 'locale$',
    'migrations', 'fixtures', 'admin$', 'django_extensions',
]
SECRET_KEY = 'secret'
# COVERAGE_MODULE_EXCLUDES += EXTERNAL_APPS
