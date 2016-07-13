# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0008_auto_20150430_1804'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoice',
            options={'ordering': ('-issue_date', 'series', '-number')},
        ),
        migrations.AlterModelOptions(
            name='proforma',
            options={'ordering': ('-issue_date', 'series', '-number')},
        ),
        migrations.AddField(
            model_name='subscription',
            name='cancel_date',
            field=models.DateField(
                help_text=b'The date when the subscription was canceled.',
                null=True,
                blank=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='trial_period_days',
            field=models.PositiveIntegerField(
                help_text=b'Number of trial period days granted when subscribing a customer to this plan.',
                null=True,
                verbose_name=b'Trial days',
                blank=True),
        ),
    ]
