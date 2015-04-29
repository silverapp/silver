# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0003_auto_20150417_0634'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='series',
            field=models.CharField(max_length=20, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='proforma',
            name='series',
            field=models.CharField(max_length=20, null=True, blank=True),
        ),
    ]
