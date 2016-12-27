# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0015_auto_20161206_1016'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='data',
            field=jsonfield.fields.JSONField(default={}, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='paymentmethod',
            name='payment_processor',
            field=models.CharField(max_length=256, choices=[(b'manual', b'Manual'), (b'braintree', b'Braintree')]),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='invoice',
            field=models.ForeignKey(blank=True, to='silver.Invoice', null=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='proforma',
            field=models.ForeignKey(blank=True, to='silver.Proforma', null=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='state',
            field=django_fsm.FSMField(default=b'initial', max_length=8, choices=[(b'canceled', 'Canceled'), (b'refunded', 'Refunded'), (b'initial', 'Initial'), (b'failed', 'Failed'), (b'settled', 'Settled'), (b'pending', 'Pending')]),
        ),
    ]
