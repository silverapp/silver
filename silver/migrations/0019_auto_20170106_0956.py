# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0018_auto_20170106_0921'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentmethod',
            name='disabled',
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='enabled',
            field=models.BooleanField(default=True),
        ),
    ]
