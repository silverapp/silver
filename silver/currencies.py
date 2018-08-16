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

from django.conf import settings
from django.utils.module_loading import import_string


class RateNotFound(Exception):
    def __init__(self, from_currency=None, to_currency=None, date=None):
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.date = date

    def __str__(self):
        if not all([self.from_currency, self.to_currency]):
            return 'No rate was found.'

        if not self.date:
            return 'No rate for {} to {}.'.format(self.from_currency,
                                                  self.to_currency)

        return 'No rate for {} to {}, from {} was found.'.format(
            self.from_currency, self.to_currency, self.date
        )


class DummyConverter(object):
    def convert(self, amount, from_currency, to_currency, date):
        if from_currency != to_currency:
            raise RateNotFound(from_currency, to_currency, date)
        return amount

try:
    CurrencyConverter = import_string(settings.SILVER_CURRENCY_CONVERTER)()
except AttributeError:
    CurrencyConverter = DummyConverter()
