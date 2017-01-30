# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0031_auto_20170125_1343'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customer',
            options={'ordering': ['first_name', 'last_name', 'company']},
        ),
        migrations.AddField(
            model_name='transaction',
            name='cancel_code',
            field=models.CharField(blank=True, max_length=32, null=True, choices=[(b'default', b'default')]),
        ),
        migrations.AddField(
            model_name='transaction',
            name='fail_code',
            field=models.CharField(blank=True, max_length=32, null=True, choices=[(b'default', b'default'), (b'expired_payment_method', b'expired_payment_method'), (b'insufficient_funds', b'insufficient_funds')]),
        ),
        migrations.AddField(
            model_name='transaction',
            name='refund_code',
            field=models.CharField(blank=True, max_length=32, null=True, choices=[(b'default', b'default')]),
        ),
    ]
