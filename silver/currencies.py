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
