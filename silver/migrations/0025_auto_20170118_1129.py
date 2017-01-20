# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0024_auto_20170117_0955'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='failed_url',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='success_url',
        ),
    ]
