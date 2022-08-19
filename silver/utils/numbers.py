from decimal import Decimal
from fractions import Fraction


def quantize_fraction(f: Fraction, decimals=4) -> Decimal:
    return (Decimal(f.numerator) / Decimal(f.denominator)).quantize(Decimal(f".{'0'*decimals}"))
