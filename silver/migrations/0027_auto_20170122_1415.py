# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0026_auto_20170119_1405'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customer',
            name='emails',
        ),
        migrations.AddField(
            model_name='customer',
            name='email',
            field=models.CharField(max_length=254, null=True, blank=True),
        ),
    ]
