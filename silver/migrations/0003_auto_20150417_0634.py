# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0002_auto_20150416_1009'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='meta',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='provider',
            name='meta',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='meta',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
    ]
