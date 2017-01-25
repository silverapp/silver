from .base import CurrencyConverterBase
from .exceptions import RateNotFound
from .managers import CurrencyConverter


class DummyConverter(CurrencyConverterBase):
    def convert(self, amount, to_currency, from_currency, date):
        if to_currency != from_currency:
            raise RateNotFound(to_currency, from_currency, date)

        return amount

CurrencyConverter.register(DummyConverter)
