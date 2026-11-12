"""Deterministic, single-dimension dimensional-inspection calculations.

Research prototype only. Not a product-release or metrology authorization.
"""
from decimal import Decimal, InvalidOperation
from typing import Optional


def _number(value):
    if value is None or str(value).strip() == '':
        raise ValueError('Missing numeric value')
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError('Invalid numeric value') from exc
    if not number.is_finite():
        raise ValueError('Non-finite numeric value')
    return number


def inspect(nominal, measured, lower_deviation=None, upper_deviation=None, tolerance=None, unit='mm'):
    """Inclusive limits; deviations are signed offsets from nominal.

    Provide either a nonnegative symmetric tolerance OR both signed deviations.
    All input dimensions must use the same unit.
    """
    try:
        if unit not in ('mm', 'in'):
            raise ValueError('Only mm and in units are supported')
        n = _number(nominal)
        m = _number(measured)
        if tolerance is not None:
            if lower_deviation is not None or upper_deviation is not None:
                raise ValueError('Specify symmetric tolerance OR signed deviations, not both')
            t = _number(tolerance)
            if t < 0:
                raise ValueError('Tolerance must be nonnegative')
            ld, ud = -t, t
        else:
            ld, ud = _number(lower_deviation), _number(upper_deviation)
        if ld > ud:
            raise ValueError('Lower deviation exceeds upper deviation')
        low, high = n + ld, n + ud
        result = 'PASS' if low <= m <= high else 'FAIL'
        return {
            'decision': result, 'nominal': str(n), 'measured': str(m),
            'lower_limit': str(low), 'upper_limit': str(high),
            'lower_deviation': str(ld), 'upper_deviation': str(ud),
            'unit': unit, 'boundary_rule': 'inclusive',
            'reason': f'Measured {m} {unit}; allowed interval [{low}, {high}] {unit} (inclusive).',
            'source': 'deterministic_decimal_calculation',
            'note': 'No standards compliance or product release is implied.'
        }
    except (ValueError, TypeError) as exc:
        return {'decision': 'INSUFFICIENT_DATA', 'reason': str(exc), 'source': 'deterministic_decimal_calculation'}
