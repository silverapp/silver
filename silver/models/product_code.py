import logging

from django.db import models

logger = logging.getLogger(__name__)


class ProductCode(models.Model):
    value = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.value
