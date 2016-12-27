# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0015_auto_20161206_1016'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='data',
            field=jsonfield.fields.JSONField(default={}, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='external_reference',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='meta',
            field=jsonfield.fields.JSONField(default={}, null=True, blank=True),
        ),
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
            model_name='provider',
            name='meta',
            field=jsonfield.fields.JSONField(default={}, null=True, blank=True),
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
    ]
