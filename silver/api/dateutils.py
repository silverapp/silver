import datetime


def get_valid_date(year, month, day):
    """
    What does it do.
    """

    if year and month and day:
        if month > 12:
            month = 12
        if day > 31:
            day = 31
        while True:
            try:
                return datetime.date(
                    year=year,
                    month=month,
                    day=day
                )
            except ValueError:
                day -= 1
                if day == 0:
                    day = 31
                    month -= 1
                if month == 0:
                    year -= 1
                    month = 12
    else:
        return None


def last_date_that_fits(initial_date, end_date, interval_type, interval_count):
    """
    What does it do.

    :param initial_date: description
    :param end_date: decription
    :param interval_type: description
    :param interval_count: description
    """

    if initial_date and end_date:
        if initial_date == end_date:
            return initial_date

        if initial_date < end_date:
            if interval_type == 'year':
                delta = end_date.year - initial_date.year
                if initial_date.month > end_date.month:
                    delta -= 1
                elif initial_date.month == end_date.month:
                    if initial_date.day > end_date.day:
                        delta -= 1
                years_to_add = int(delta / interval_count)
                years_to_add *= interval_count
                day = initial_date.day
                return get_valid_date(
                    year=initial_date.year + years_to_add,
                    month=initial_date.month,
                    day=day
                )

            elif interval_type == 'month':
                delta = end_date.month - initial_date.month
                delta += (end_date.year - initial_date.year) * 12
                if initial_date.day > end_date.day:
                    delta -= 1
                months_to_add = delta // interval_count
                months_to_add *= interval_count
                month = (initial_date.month + months_to_add) % 12
                years_to_add = (initial_date.month + months_to_add) // 12
                year = initial_date.year + years_to_add
                if month == 0:
                    month = 12
                    year -= 1
                day = initial_date.day
                return get_valid_date(year=year, month=month, day=day)

            else:
                days_allowed = (end_date - initial_date).days
                days_to_add = 0
                if interval_type == 'week':
                    days_to_add = days_allowed // (interval_count * 7)
                elif interval_type == 'day':
                    days_to_add = days_allowed // interval_count
                else:
                    return None
                days_to_add *= interval_count
                if interval_type == 'week':
                    days_to_add *= 7
                start_date = initial_date + datetime.timedelta(days=days_to_add)
                return start_date
    else:
        return None


def next_date_after_period(initial_date, interval_type, interval_count):
    """
    What does it do.

    :param initial_date: description
    :param interval_type: decription
    :param interval_count: description
    """

    if initial_date:
        if interval_type == 'year':
            return get_valid_date(
                year=initial_date.year + interval_count,
                month=initial_date.month,
                day=initial_date.day
            )
        elif interval_type == 'month':
            year = initial_date.year + \
                (initial_date.month + interval_count) / 12
            month = (initial_date.month + interval_count) % 12
            if month == 0:
                month = 12
                year -= 1
            return get_valid_date(year=year, month=month, day=initial_date.day)
        elif interval_type == 'week':
            return initial_date + datetime.timedelta(weeks=interval_count)
        elif interval_type == 'day':
            return initial_date + datetime.timedelta(days=interval_count)


def next_date_after_date(initial_date, day=None, depth=None):
    """
    What does it do.

    :param initial_date: description
    :param day: decription
    :param depth: description
    """

    if depth is None:
        depth = 0
    elif depth == 3:
        return None
    if initial_date:
        year = initial_date.year
        if day:
            if day <= initial_date.day:
                month = initial_date.month + 1
                if month == 13:
                    month = 1
                    year += 1
            else:
                month = initial_date.month

            date = get_valid_date(year=year, month=month, day=day)
        else:
            date = initial_date + datetime.timedelta(days=1)

        if date:
            if day:
                if date.day != day:
                    month = initial_date.month + 1
                    if month == 13:
                        month = 1
                        year = initial_date.year + 1
                    else:
                        year = initial_date.year
                    date = get_valid_date(year=year, month=month, day=1)
                    return next_date_after_date(initial_date=date, day=day,
                                                depth=depth + 1)

            return date

    return None
