from __future__ import absolute_import

import os

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

app = Celery('silver')
app.config_from_object(settings, namespace='CELERY')

app.autodiscover_tasks()

task = app.task
