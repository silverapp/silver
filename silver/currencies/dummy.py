from decimal import Decimal

from .rates import ExchangeRateBase
from .exceptions import RateNotFound
from .converters import CurrencyConverter


class DummyExchangeRate(ExchangeRateBase):
    def get_rate(self, to_currency, from_currency, date):
        if to_currency != from_currency:
            raise RateNotFound(to_currency, from_currency, date)

        return Decimal('1.00')

CurrencyConverter.register(DummyExchangeRate)
