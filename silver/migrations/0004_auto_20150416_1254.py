# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0003_auto_20150416_1154'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoice',
            options={'ordering': ('-issue_date', 'series', 'number')},
        ),
        migrations.AlterModelOptions(
            name='proforma',
            options={'ordering': ('-issue_date', 'series', 'number')},
        ),
        migrations.AlterUniqueTogether(
            name='invoice',
            unique_together=set([('provider', 'series', 'number')]),
        ),
        migrations.AlterUniqueTogether(
            name='proforma',
            unique_together=set([('provider', 'series', 'number')]),
        ),
    ]
