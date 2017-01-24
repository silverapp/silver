# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import silver.utils.models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0029_auto_20170124_1042'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='updated_at',
            field=silver.utils.models.AutoDateTimeField(default=django.utils.timezone.now),
        ),
    ]
