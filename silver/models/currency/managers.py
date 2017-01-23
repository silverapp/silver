from django.utils import timezone

from .exceptions import RateNotFound


class CurrencyConverter(object):
    _converters = []

    @classmethod
    def register(cls, converter_class):
        cls._converters.append(converter_class)

    @classmethod
    def unregister(cls, converter_class):
        try:
            cls._converters.remove(converter_class)
        except ValueError:
            return

    @classmethod
    def all_instances(cls):
        return [converter() for converter in cls._converters]

    @classmethod
    def convert(cls, amount, from_currency, to_currency, date=None):
        if not date:
            date = timezone.now().date()

        for converter in cls.all_instances():
            known_currencies = set(converter.known_currencies)

            if (known_currencies and not
                    known_currencies.issuperset([from_currency, to_currency])):
                continue

            try:
                return converter.convert(amount, from_currency, to_currency,
                                         date)
            except RateNotFound:
                continue

        raise RateNotFound(from_currency, to_currency, date)
