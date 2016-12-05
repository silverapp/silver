# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0014_auto_20161122_1145'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='state',
            field=django_fsm.FSMField(default=b'initial', max_length=8, choices=[(b'canceled', 'Canceled'), (b'refunded', 'Refunded'), (b'initial', 'Initial'), (b'failed', 'Failed'), (b'settled', 'Settled'), (b'pending', 'Pending')]),
        ),
    ]
