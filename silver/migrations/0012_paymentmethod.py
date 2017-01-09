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
import django.utils.timezone
import silver.models.payment_processors.fields
import silver.models.payment_processors.manual
import django_fsm
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0011_auto_20160927_0807'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('payment_processor', silver.models.payment_processors.fields.PaymentProcessorField(max_length=64, choices=[(silver.models.payment_processors.manual.ManualProcessor(), b'Manual')])),
                ('added_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('verified_at', models.DateTimeField(null=True, blank=True)),
                ('data', jsonfield.fields.JSONField(null=True, blank=True)),
                ('state', django_fsm.FSMField(default=b'uninitialized', max_length=50, choices=[(b'uninitialized', b'Uninitialized'), (b'unverified', b'Unverified'), (b'enabled', b'Enabled'), (b'disabled', b'Disabled'), (b'removed', b'Removed')])),
                ('customer', models.ForeignKey(to='silver.Customer')),
            ],
        ),
    ]
