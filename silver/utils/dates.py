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

from __future__ import absolute_import

from datetime import timedelta
from dateutil.relativedelta import *


ONE_DAY = timedelta(days=1)
ONE_MONTH = relativedelta(months=1)


def next_month(date):
    return date + ONE_MONTH


def first_day_of_month(date):
    return date + relativedelta(day=1)


def last_day_of_month(date):
    return date + relativedelta(day=31)


def prev_month(date):
    return date - ONE_MONTH
