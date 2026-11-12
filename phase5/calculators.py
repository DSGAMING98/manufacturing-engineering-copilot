"""Deterministic, limited-scope engineering calculators (stdlib only).

These are transparent example calculations, not machine setup recommendations,
shop-floor authority, or compliance determinations. No LLM-generated input is
accepted as a trusted value. Each function validates all numeric operands.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
import re

PI = Decimal('3.1415926535897932384626433832795028841971')
MAX_ABS = Decimal('1000000000000')
INTEGER = re.compile(r'(?:0|[1-9][0-9]{0,8})\Z')


class InputError(ValueError):
    """Refused inconsistent, missing or unsupported engineering inputs."""


def dec(value: object, label: str, *, minimum: str | None = None,
        strictly_positive: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise InputError(f'{label} must be a finite decimal number.')
    s = str(value).strip()
    if not s or len(s) > 48:
        raise InputError(f'{label} must be a finite decimal number.')
    try:
        n = Decimal(s)
    except (InvalidOperation, ValueError) as exc:
        raise InputError(f'{label} must be a finite decimal number.') from exc
    if not n.is_finite() or abs(n) > MAX_ABS:
        raise InputError(f'{label} must be finite and within the supported magnitude.')
    if minimum is not None and n < Decimal(minimum):
        raise InputError(f'{label} must be at least {minimum}.')
    if strictly_positive and n <= 0:
        raise InputError(f'{label} must be greater than zero.')
    return n


def count(value: object, label: str) -> int:
    if isinstance(value, bool) or value is None or not INTEGER.fullmatch(str(value).strip()):
        raise InputError(f'{label} must be a nonnegative whole number (up to 9 digits).')
    return int(str(value).strip())


def fmt(n: Decimal, decimal_places: int = 4) -> str:
    with localcontext() as ctx:
        ctx.prec = 42
        v = n.quantize(Decimal(1).scaleb(-decimal_places))
    return format(v, 'f')


def design_fit(p: dict) -> dict:
    """Worst-case hole/shaft clearance. mm only; no statistical fit analysis."""
    unit = p.get('unit', 'mm')
    if unit != 'mm':
        raise InputError('Design fit currently supports unit=mm only.')
    hmin, hmax = (dec(p.get('hole_min'), 'hole_min', strictly_positive=True),
                  dec(p.get('hole_max'), 'hole_max', strictly_positive=True))
    smin, smax = (dec(p.get('shaft_min'), 'shaft_min', strictly_positive=True),
                  dec(p.get('shaft_max'), 'shaft_max', strictly_positive=True))
    if hmin > hmax or smin > smax:
        raise InputError('Minimum size cannot exceed maximum size.')
    with localcontext() as ctx:
        ctx.prec = 42
        low, high = hmin - smax, hmax - smin
    # Zero-clearance boundary is classified as transition, conservatively.
    classification = 'CLEARANCE' if low > 0 else ('INTERFERENCE' if high < 0 else 'TRANSITION')
    return {
        'classification': classification,
        'min_clearance_mm': str(low), 'max_clearance_mm': str(high),
        'hole_interval_mm': [str(hmin), str(hmax)],
        'shaft_interval_mm': [str(smin), str(smax)],
        'note': 'Worst-case dimensional fit only; not an ISO fit designation, tolerance-stack study or design approval.',
    }


def turning_estimate(p: dict) -> dict:
    """Ideal turning estimate: rpm=(1000 Vc)/(pi D); feed=rpm*f; time=L/feed."""
    if p.get('unit', 'mm') != 'mm':
        raise InputError('Turning estimate supports metric inputs only.')
    diameter = dec(p.get('diameter_mm'), 'diameter_mm', strictly_positive=True)
    speed = dec(p.get('cutting_speed_m_per_min'), 'cutting_speed_m_per_min', strictly_positive=True)
    feed = dec(p.get('feed_mm_per_rev'), 'feed_mm_per_rev', strictly_positive=True)
    length = dec(p.get('length_mm'), 'length_mm', strictly_positive=True)
    with localcontext() as ctx:
        ctx.prec = 42
        rpm = Decimal(1000) * speed / (PI * diameter)
        feed_rate = rpm * feed
        duration = length / feed_rate
    return {
        'spindle_rpm_ideal': fmt(rpm),
        'feed_rate_mm_per_min_ideal': fmt(feed_rate),
        'cutting_time_min_ideal': fmt(duration, 6),
        'note': 'Idealized single-pass estimate only. Excludes approach, acceleration, depth/pass planning, material constraints, machine limits, wear and safety allowances. Engineer verification required.',
    }


def production_oee(p: dict) -> dict:
    """Availability * performance * quality; impossible >100% performance is refused."""
    planned = dec(p.get('planned_min'), 'planned_min', strictly_positive=True)
    run = dec(p.get('run_min'), 'run_min', strictly_positive=True)
    cycle = dec(p.get('ideal_cycle_min_per_part'), 'ideal_cycle_min_per_part', strictly_positive=True)
    total = count(p.get('total_parts'), 'total_parts')
    good = count(p.get('good_parts'), 'good_parts')
    if run > planned:
        raise InputError('run_min cannot exceed planned_min.')
    if total == 0 or good > total:
        raise InputError('total_parts must be positive and good_parts cannot exceed total_parts.')
    with localcontext() as ctx:
        ctx.prec = 42
        availability = run / planned
        performance = cycle * total / run
        quality = Decimal(good) / total
        if performance > 1:
            raise InputError('Reported ideal cycle and part count imply >100% performance; verify inputs/definitions.')
        oee = availability * performance * quality
    return {
        'availability_pct': fmt(availability * 100, 2),
        'performance_pct': fmt(performance * 100, 2),
        'quality_pct': fmt(quality * 100, 2),
        'oee_pct': fmt(oee * 100, 2),
        'note': 'Historical OEE estimate using operator-provided definitions. No production optimization or automated acceptance implied.',
    }


def maintenance_kpis(p: dict) -> dict:
    """Historical MTBF/MTTR, observed availability; NEVER failure prediction."""
    uptime = dec(p.get('operating_hours'), 'operating_hours', minimum='0')
    repair = dec(p.get('repair_hours'), 'repair_hours', minimum='0')
    failures = count(p.get('failures'), 'failures')
    if uptime + repair == 0:
        raise InputError('Provide a nonzero observation duration.')
    if failures == 0 and repair > 0:
        raise InputError('Repair hours are nonzero but failure count is zero; clarify event definitions.')
    with localcontext() as ctx:
        ctx.prec = 42
        mtbf = fmt(uptime / failures, 4) if failures else None
        mttr = fmt(repair / failures, 4) if failures else None
        availability = fmt(uptime / (uptime + repair) * 100, 2)
    return {
        'observed_mtbf_hours': mtbf,
        'observed_mttr_hours': mttr,
        'observed_availability_pct': availability,
        'failure_count': failures,
        'note': ('Retrospective indicators only. No remaining-life estimate, predictive maintenance, '
                 'safe-to-operate recommendation or replacement schedule can be inferred. '
                 'When no failures were observed, MTBF/MTTR are undefined for this sample.'),
    }
