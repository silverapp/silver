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
import silver.models.payment_processors.fields


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0020_auto_20170106_0956'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='payment_processor',
            field=silver.models.payment_processors.fields.PaymentProcessorField(max_length=256),
        ),
    ]
