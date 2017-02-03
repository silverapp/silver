# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0032_auto_20170201_1342'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmethod',
            name='display_info',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='valid_until',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
