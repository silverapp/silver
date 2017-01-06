# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0017_auto_20161230_1420'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentmethod',
            name='state',
        ),
        migrations.RemoveField(
            model_name='paymentmethod',
            name='verified_at',
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='disabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='verified',
            field=models.BooleanField(default=False),
        ),
    ]
