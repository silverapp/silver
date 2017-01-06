# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0019_document_view'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentmethod',
            name='disabled',
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='enabled',
            field=models.BooleanField(default=True),
        ),
    ]
