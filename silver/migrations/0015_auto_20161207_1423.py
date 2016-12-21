# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import silver.models.payment_processors.fields
import django_fsm
import silver.models.payment_processors.manual
import payment_processors.braintree_processor.payment_processors


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0014_auto_20161122_1145'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='payment_processor',
            field=silver.models.payment_processors.fields.PaymentProcessorField(max_length=64, choices=[(payment_processors.braintree_processor.payment_processors.BraintreeTriggered(), b'BraintreeTriggered'), (silver.models.payment_processors.manual.ManualProcessor(), b'Manual')]),
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
