from settings import *

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': os.getenv('SILVER_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('SILVER_DB_NAME', 'db.sqlite3'),
        'USER': os.getenv('SILVER_DB_USER', 'silver'),
        'PASSWORD': os.getenv('SILVER_DB_PASSWORD', 'password'),
        'HOST': os.getenv('SILVER_DB_HOST', ''),
        'PORT': os.getenv('SILVER_DB_PORT', '3306'),
    }
}

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0']
