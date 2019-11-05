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


class INTERVALS(object):
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'


def next_month(date):
    return date + ONE_MONTH


def first_day_of_interval(date, interval):
    if interval == INTERVALS.DAY:
        return date
    elif interval == INTERVALS.WEEK:
        return first_day_of_week(date)
    elif interval == INTERVALS.MONTH:
        return first_day_of_month(date)
    elif interval == INTERVALS.YEAR:
        return first_day_of_year(date)


def end_of_interval(start_date, interval, interval_count):
    if interval == INTERVALS.YEAR:
        relative_delta = {'years': interval_count}
    elif interval == INTERVALS.MONTH:
        relative_delta = {'months': interval_count}
    elif interval == INTERVALS.WEEK:
        relative_delta = {'weeks': interval_count}
    elif interval == INTERVALS.DAY:
        relative_delta = {'days': interval_count}
    else:
        return None

    return start_date + relativedelta(**relative_delta) - ONE_DAY


def first_day_of_week(date):
    return date + relativedelta(weekday=MO(-1))


def last_day_of_week(date):
    return date + relativedelta(weekday=SU(-1))


def first_day_of_month(date):
    return date + relativedelta(day=1)


def last_day_of_month(date):
    return date + relativedelta(day=31)


def first_day_of_year(date):
    return date + relativedelta(month=1, day=1)


def last_day_of_year(date):
    return date + relativedelta(month=12, day=31)


def prev_month(date):
    return date - ONE_MONTH
