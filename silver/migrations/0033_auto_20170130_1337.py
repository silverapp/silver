# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0032_auto_20170130_1317'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentmethod',
            name='enabled',
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='canceled',
            field=models.BooleanField(default=False),
        ),
    ]
