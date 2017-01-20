# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0025_auto_20170118_1129'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='consumable',
        ),
    ]
