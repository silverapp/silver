# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0033_auto_20170203_1540'),
    ]

    operations = [
        migrations.AddField(
            model_name='Document',
            name='transaction_currency',
            field=models.CharField(max_length=4),
        ),
    ]
