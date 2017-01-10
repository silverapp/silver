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
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0014_auto_20161122_1145'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='state',
            field=django_fsm.FSMField(default=b'initial', max_length=8, choices=[(b'canceled', 'Canceled'), (b'refunded', 'Refunded'), (b'initial', 'Initial'), (b'failed', 'Failed'), (b'settled', 'Settled'), (b'pending', 'Pending')]),
        ),
    ]
