from .exceptions import RateNotFound


class CurrencyConverterBase(object):
    @property
    def known_currencies(self):
        """
            Returns a list of known currencies. If left empty the
            CurrencyConverter manager will ignore it.
        """
        return []

    def convert(self, amount, from_currency, to_currency, date):
        raise RateNotFound(from_currency, to_currency, date)
