# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0013_transaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='status',
            field=django_fsm.FSMField(default=b'uninitialized', max_length=50),
        )
    ]
