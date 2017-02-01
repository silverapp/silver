from django.utils import timezone

from .exceptions import RateNotFound


class CurrencyConverter(object):
    _exchangers = []

    @classmethod
    def register(cls, exchanger_class):
        cls._exchangers.append(exchanger_class)

    @classmethod
    def unregister(cls, exchanger_class):
        try:
            cls._exchangers.remove(exchanger_class)
        except ValueError:
            return

    @classmethod
    def all_instances(cls):
        return [exchanger() for exchanger in cls._exchangers]

    @classmethod
    def convert(cls, amount, from_currency, to_currency, date=None):
        if not date:
            date = timezone.now().date()

        for exchanger in cls.all_instances():
            known_currencies = set(exchanger.known_currencies)

            if (known_currencies and not
                    known_currencies.issuperset([from_currency, to_currency])):
                continue

            try:
                rate = exchanger.get_rate(from_currency, to_currency, date)

                return amount * rate
            except RateNotFound:
                continue

        raise RateNotFound(from_currency, to_currency, date)
