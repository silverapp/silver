import datetime


def get_valid_date(year, month, day):
    """
    Returns a valid date <= date(year, month, day) if all arguments are provided
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
    Returns the end date of the last sub-interval (defined by interval_type and
    interval_count) that fits into an interval (defined by initial_date and
    end_date)

     __main interval__
    |                 |
    <----|----|----|-->
         |____|    ^
           ^    returned date
      sub-interval

    :param initial_date: the start date of the main interval
    :param end_date: the end date of the the main interval
    :param interval_type: the sub-interval type ('year, 'month', 'week', 'day')
    :param interval_count: the sub-interval length (e.g.: 2 (months, weeks ...))
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
    Returns the relative date obtained by adding a period (defined by
    interval_type and interval_count) to an initial_date
    e.g.: initial_date='2015-01-01', interval_type='month', interval_count=2
          returned date: '2015-02-28'

    :param initial_date: the initial date to which the period is added
    :param interval_type: the interval type ('year, 'month', 'week', 'day')
    :param interval_count: the interval length (e.g.: 2 (months, weeks ...))
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


def next_date_after_date(initial_date, day=None, _depth=None):
    """
    Returns the next date after an initial date with various constraints:
        - for the moment being the only constraint is the day of the month

    e.g.: initial_date='2015-02-01', day=31
          returned date: '2015-03-31'

    :param initial_date: the initial date
    :param day: the desired day of the returned date
    """

    if _depth is None:
        _depth = 0
    elif _depth == 3:
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
                                                _depth=_depth + 1)

            return date

    return None
