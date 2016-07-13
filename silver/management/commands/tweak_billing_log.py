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


import datetime as dt
from datetime import datetime
from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils import timezone

from silver.models import Subscription, BillingLog


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--date',
                    action='store',
                    dest='date'),
    )

    def handle(self, *args, **options):
        if options['date']:
            date = datetime.strptime(options['date'], '%Y-%m-%d')
        else:
            now = timezone.now().date()
            date = dt.date(now.year, now.month - 1, 1)

        for subscription in Subscription.objects.all():
            self.stdout.write('Tweaking for subscription %d' % subscription.id)
            BillingLog.objects.create(subscription=subscription,
                                      billing_date=date)
