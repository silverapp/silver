from .exceptions import RateNotFound


class RateExchangerBase(object):
    @property
    def known_currencies(self):
        """
            Returns a list of known currencies. If left empty the
            CurrencyConverter manager will ignore it.
        """
        return []

    def get_rate(self, from_currency, to_currency, date):
        raise RateNotFound(from_currency, to_currency, date)
