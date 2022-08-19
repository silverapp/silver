from datetime import date
from decimal import Decimal

from silver.utils.dates import monthdiff, ONE_MONTH


def test_monthdiff_same_date():
    assert monthdiff(date(2023, 5, 5), date(2023, 5, 5)) == Decimal(0)


def test_monthdiff_month_beginnings():
    assert date(2022, 1, 1) + ONE_MONTH == date(2022, 2, 1)
    assert monthdiff(date(2022, 2, 1), date(2022, 1, 1)) == Decimal(1)


def test_monthdiff_month_beginning_to_middle_of_month():
    assert monthdiff(date(2022, 3, 14), date(2022, 3, 1)) == Decimal(14.0 - 1.0) / Decimal(31.0)


def test_monthdiff_month_beginning_to_middle_of_next_month():
    assert monthdiff(date(2022, 2, 15), date(2022, 1, 1)) == Decimal(1.5)


def test_monthdiff_quarter_of_month_to_end_of_month():
    assert monthdiff(date(2022, 2, 28), date(2022, 1, 7)) == Decimal(1) + Decimal(28 - 7) / Decimal(28)


def test_monthdiff_quarter_of_month_to_end_of_over_6_months_different_years_same_day():
    assert monthdiff(date(2025, 6, 7), date(2024, 12, 7)) == Decimal(6)


def test_monthdiff_quarter_of_month_to_end_of_over_3_months_different_years():
    assert monthdiff(date(2025, 2, 28), date(2024, 12, 8)) == Decimal(2) + Decimal(28 - 8) / Decimal(28.0)


def test_monthdiff_random_date_to_start_of_next_month():
    assert monthdiff(date(2015, 2, 1), date(2015, 1, 23)) == Decimal(9) / Decimal(31)


def test_monthdiff_to_longer_month():
    assert date(2022, 2, 28) + ONE_MONTH == date(2022, 3, 28)
    assert monthdiff(date(2022, 3, 28), date(2022, 2, 28)) == Decimal(1)

    assert monthdiff(date(2022, 3, 31), date(2022, 2, 28)) == Decimal(1) + Decimal(3) / Decimal(31)
