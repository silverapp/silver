# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0032_auto_20170130_1317'),
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
        migrations.AlterField(
            model_name='provider',
            name='email',
            field=models.CharField(max_length=254, null=True, blank=True),
        ),
    ]
