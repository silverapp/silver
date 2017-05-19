from redlock import Redlock

from django.conf import settings


lock_manager = Redlock([settings.LOCK_MANAGER_CONNECTION,])
