# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0006_auto_20150430_1457'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='trial_period_days',
            field=models.PositiveIntegerField(help_text=b'Number of trial period days granted when subscribing a customer to this plan.', null=True, verbose_name=b'Trial days'),
        ),
    ]
