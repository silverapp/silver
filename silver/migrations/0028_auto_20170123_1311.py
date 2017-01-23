# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import silver.utils.models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0027_auto_20170122_1415'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='created_at',
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='transaction',
            name='updated_at',
            field=silver.utils.models.AutoDateTimeField(default=django.utils.timezone.now),
        ),
    ]
