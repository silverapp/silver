# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0031_auto_20170125_1343'),
    ]

    operations = [
        migrations.RenameField(
            model_name='provider',
            old_name='display_email',
            new_name='email'
        ),
        migrations.RemoveField(
            model_name='provider',
            name='notification_email'
        ),
    ]
