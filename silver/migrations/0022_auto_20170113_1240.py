# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0021_auto_20170109_1159'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='phone',
            field=models.CharField(max_length=14, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='provider',
            name='phone',
            field=models.CharField(max_length=14, null=True, blank=True),
        ),
    ]
