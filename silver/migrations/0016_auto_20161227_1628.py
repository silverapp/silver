# Copyright (c) 2017 Presslabs SRL
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

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0015_auto_20161206_1016'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='data',
            field=jsonfield.fields.JSONField(default={}, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='external_reference',
            field=models.CharField(max_length=256, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='meta',
            field=jsonfield.fields.JSONField(default={}, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='paymentmethod',
            name='data',
            field=jsonfield.fields.JSONField(default={}, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='paymentmethod',
            name='payment_processor',
            field=models.CharField(max_length=256, choices=[(b'manual', b'Manual')]),
        ),
        migrations.AlterField(
            model_name='provider',
            name='meta',
            field=jsonfield.fields.JSONField(default={}, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='invoice',
            field=models.ForeignKey(blank=True, to='silver.Invoice', null=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='proforma',
            field=models.ForeignKey(blank=True, to='silver.Proforma', null=True),
        ),
    ]
