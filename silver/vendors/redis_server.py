from redis import StrictRedis

from django.conf import settings

redis = StrictRedis.from_url(
    getattr(settings, 'CONFIG_SERVER', 'redis://127.0.0.1:6379')
)
