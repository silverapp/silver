# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0005_auto_20150429_1732'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customer',
            options={'ordering': ['name', 'company']},
        ),
        migrations.AlterModelOptions(
            name='meteredfeature',
            options={'ordering': ('name',)},
        ),
        migrations.AlterModelOptions(
            name='plan',
            options={'ordering': ('name',)},
        ),
        migrations.AlterModelOptions(
            name='provider',
            options={'ordering': ['name', 'company']},
        ),
        migrations.AlterField(
            model_name='invoice',
            name='issue_date',
            field=models.DateField(db_index=True, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='number',
            field=models.IntegerField(db_index=True, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='series',
            field=models.CharField(db_index=True, max_length=20, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='meteredfeature',
            name='name',
            field=models.CharField(help_text=b'The feature display name.', max_length=200, db_index=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='name',
            field=models.CharField(help_text=b'Display name of the plan.', max_length=200, db_index=True),
        ),
        migrations.AlterField(
            model_name='proforma',
            name='issue_date',
            field=models.DateField(db_index=True, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='proforma',
            name='number',
            field=models.IntegerField(db_index=True, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='proforma',
            name='series',
            field=models.CharField(db_index=True, max_length=20, null=True, blank=True),
        ),
        migrations.AlterIndexTogether(
            name='customer',
            index_together=set([('name', 'company')]),
        ),
        migrations.AlterIndexTogether(
            name='provider',
            index_together=set([('name', 'company')]),
        ),
    ]
