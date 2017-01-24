# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
import silver.utils.models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0028_auto_20170123_1311'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='updated_at',
            field=silver.utils.models.AutoDateTimeField(default=datetime.datetime.now),
        ),
    ]
