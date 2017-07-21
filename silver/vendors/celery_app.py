from __future__ import absolute_import

from celery import Celery
from django.conf import settings


app = Celery('silver')
app.config_from_object(settings)

app.autodiscover_tasks()

task = app.task
