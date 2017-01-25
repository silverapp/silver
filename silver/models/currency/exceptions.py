class RateNotFound(Exception):
    def __init__(self, from_currency, to_currency, date, *args, **kwargs):
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.date = date

    def __str__(self):
        return 'No rate for {} to {}, from {} was found.'.format(
            self.from_currency, self.to_currency, self.date
        )
