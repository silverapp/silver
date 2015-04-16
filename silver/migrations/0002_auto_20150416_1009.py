# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documententry',
            name='description',
            field=models.CharField(max_length=1024),
        ),
        migrations.AlterField(
            model_name='documententry',
            name='unit',
            field=models.CharField(max_length=1024, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='product_code',
            field=models.ForeignKey(help_text=b'The product code for this plan.', to='silver.ProductCode'),
        ),
    ]
