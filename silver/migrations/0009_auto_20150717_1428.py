# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0008_auto_20150430_1804'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoice',
            options={'ordering': ('-issue_date', 'series', '-number')},
        ),
        migrations.AlterModelOptions(
            name='proforma',
            options={'ordering': ('-issue_date', 'series', '-number')},
        ),
        migrations.AddField(
            model_name='subscription',
            name='cancel_date',
            field=models.DateField(help_text=b'The date when the subscription was canceled.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='trial_period_days',
            field=models.PositiveIntegerField(help_text=b'Number of trial period days granted when subscribing a customer to this plan.', null=True, verbose_name=b'Trial days', blank=True),
        ),
    ]
