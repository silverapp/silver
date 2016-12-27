# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0016_auto_20161222_1437'),
    ]

    operations = [
        migrations.CreateModel(
            name='BraintreePaymentMethod',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('silver.paymentmethod',),
        ),
    ]
