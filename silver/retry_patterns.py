def daily(count):
    return 1


def exponential(count):
    return 2 ** count


def fibonacci(count):
    previous = current = 1

    for i in range(2, count):
        previous, current = current, previous + current

    return current


class RetryPatterns:
    patterns = {
        'daily': daily,
        'exponential': exponential,
        'fibonacci': fibonacci
    }

    @classmethod
    def as_list(cls):
        return cls.patterns.keys()

    @classmethod
    def as_choices(cls):
        return list(
            (pattern, pattern.capitalize()) for pattern in cls.patterns
        )

    @classmethod
    def get_pattern_method(cls, name):
        return cls.patterns.get(name)
