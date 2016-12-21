# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0015_auto_20161207_1423'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='payment_processor',
            field=models.CharField(max_length=256, choices=[(b'manual', b'Manual'), (b'braintree', b'Braintree')]),
        ),
    ]
