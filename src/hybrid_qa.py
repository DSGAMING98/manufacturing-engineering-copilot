"""Safe, single-dimension hybrid QA orchestration (CPU-only core).

The SLM may select response presentation style; it NEVER sets the
measurement, limits, result, next action, or any standard reference.
Research demonstration only; not authorization for batch/product release.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Optional

from src.tolerance_engine import inspect

NUM = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
UNIT = r"mm|in"
# Deliberately narrow grammar. Unsupported engineering inputs are rejected.
FIELD_START = r"(?:^|(?<=[\s,;]))"
NOMINAL = re.compile(rf"\bnominal(?:\s+(?:diameter|dimension|size|value))?\s*(?:=|:|is|of)?\s*(?P<value>{NUM})\s*(?P<unit>{UNIT})?\b", re.I)
MEASURED = re.compile(rf"\bmeasured(?:\s+(?:diameter|dimension|size|value))?\s*(?:=|:|is|of)?\s*(?P<value>{NUM})\s*(?P<unit>{UNIT})?\b", re.I)
TOLERANCE = re.compile(rf"\btolerance\s*(?:=|:|is|of)?\s*(?:±|\+/-)\s*(?P<value>{NUM})\s*(?P<unit>{UNIT})?\b", re.I)
LOWER = re.compile(rf"\blower\s+(?:dev|deviation)\s*(?:=|:|is|of)?\s*(?P<value>{NUM})\s*(?P<unit>{UNIT})?\b", re.I)
UPPER = re.compile(rf"\bupper\s+(?:dev|deviation)\s*(?:=|:|is|of)?\s*(?P<value>{NUM})\s*(?P<unit>{UNIT})?\b", re.I)
# Scan number+unit expressions; unlike a bare word scan, this does not mistake
# English prepositions like 'in tolerance' for the inch unit.
NUMBER_WITH_UNIT = re.compile(rf'(?<![\w.]){NUM}\s*(?P<unit>mm|in|cm|um|µm|μm|m|ft|inch|inches)\b', re.I)
KEY_VALUE = re.compile(r"(?P<key>nominal|measured|tolerance|lower_dev|upper_dev|low_dev|high_dev|unit)\s*=\s*(?P<value>[^\s,;]+)", re.I)
ALLOWED_KEYS = frozenset(('nominal', 'measured', 'tolerance', 'lower_dev', 'upper_dev', 'unit'))
SUPPORTED_STYLES = ('technical', 'plain', 'operator')
STYLE_RE = re.compile(r"^STYLE:\s*(TECHNICAL|PLAIN|OPERATOR)\s*$", re.I)


@dataclass(frozen=True)
class ParseResult:
    fields: dict | None
    error: str | None


def _invalid(reason: str) -> ParseResult:
    return ParseResult(None, reason)


def _from_structured(question: str) -> ParseResult | None:
    """Only accept a pure set of key=value parameters, never silently ignore extras."""
    if not re.search(r"\b(?:nominal|measured|tolerance|lower_dev|upper_dev|low_dev|high_dev|unit)\s*=", question, re.I):
        return None
    matches = list(KEY_VALUE.finditer(question))
    remaining = KEY_VALUE.sub('', question)
    if remaining.strip(' \t\r\n,;'):
        return _invalid('Unrecognized structured text. Use only nominal, measured, tolerance OR lower_dev/upper_dev, and unit.')
    data = {}
    aliases = {'low_dev': 'lower_dev', 'high_dev': 'upper_dev'}
    for m in matches:
        key = aliases.get(m['key'].lower(), m['key'].lower())
        if key not in ALLOWED_KEYS or key in data:
            return _invalid('Duplicate or unsupported structured field.')
        data[key] = m['value']
    if not matches:
        return _invalid('No recognized fields.')
    if 'unit' not in data:
        return _invalid('Specify unit=mm or unit=in for structured input.')
    if data['unit'].lower() not in ('mm', 'in'):
        return _invalid('Only unit=mm and unit=in are supported.')
    data['unit'] = data['unit'].lower()
    return ParseResult(data, None)


def _unique(regex: re.Pattern, question: str, name: str):
    hits = list(regex.finditer(question))
    if len(hits) != 1:
        return None, f'Expected exactly one {name}; found {len(hits)}.'
    return hits[0], None


def parse_question(question: str) -> ParseResult:
    """Supported inputs: strict key=value or explicit nominal/measured and tolerances.

    Mixed units, duplicate fields, absent tolerance and multiple scenarios are
    rejected rather than relying on generative extraction.
    """
    question = (question or '').strip()
    if not question:
        return _invalid('Missing inspection scenario.')
    structured = _from_structured(question)
    if structured is not None:
        return structured

    n, err = _unique(NOMINAL, question, 'nominal value')
    if err:
        return _invalid(err)
    m, err = _unique(MEASURED, question, 'measured value')
    if err:
        return _invalid(err)
    t_matches = list(TOLERANCE.finditer(question))
    l_matches = list(LOWER.finditer(question))
    u_matches = list(UPPER.finditer(question))
    if len(t_matches) == 1 and not l_matches and not u_matches:
        selected = [('nominal', n), ('measured', m), ('tolerance', t_matches[0])]
    elif not t_matches and len(l_matches) == 1 and len(u_matches) == 1:
        selected = [('nominal', n), ('measured', m), ('lower_dev', l_matches[0]), ('upper_dev', u_matches[0])]
    else:
        return _invalid('Specify one symmetric tolerance (±) OR exactly one lower and upper deviation.')

    # Every explicit numeric unit must be consistent. Reject unsupported units
    # and extra numeric measurements, rather than ignoring a second dimension.
    units = {match['unit'].lower() for _, match in selected if match['unit']}
    numeric_units = list(NUMBER_WITH_UNIT.finditer(question))
    all_units = {match['unit'].lower() for match in numeric_units}
    if not units or len(units) != 1 or len(all_units) != 1 or units != all_units:
        return _invalid('Missing, unsupported or mixed measurement units. Use mm everywhere or in everywhere.')
    for unit_match in numeric_units:
        if not any(unit_match.start() >= match.start() and unit_match.end() <= match.end()
                   for _, match in selected):
            return _invalid('Additional unrecognized measurement(s); provide a single dimension.')
    # Catch an unsupported, duplicated tolerance token, or extra measured/nominal fields.
    if len(re.findall(r'\bnominal\b', question, re.I)) != 1 or len(re.findall(r'\bmeasured\b', question, re.I)) != 1:
        return _invalid('Ambiguous multiple dimensions.')
    fields = {name: match['value'] for name, match in selected}
    fields['unit'] = next(iter(units))
    return ParseResult(fields, None)


def calculate(question: str) -> dict:
    parsed = parse_question(question)
    if parsed.error:
        return {'decision': 'INSUFFICIENT_DATA', 'reason': parsed.error,
                'source': 'strict_hybrid_parser', 'unit': None}
    d = parsed.fields
    return inspect(d.get('nominal'), d.get('measured'),
                   tolerance=d.get('tolerance'),
                   lower_deviation=d.get('lower_dev'),
                   upper_deviation=d.get('upper_dev'), unit=d.get('unit'))


def verified_position(result: dict) -> str:
    """Position derived from the trusted calculator, not the SLM."""
    if result['decision'] == 'INSUFFICIENT_DATA':
        return 'UNKNOWN'
    from decimal import Decimal
    measurement = Decimal(result['measured'])
    lower = Decimal(result['lower_limit'])
    upper = Decimal(result['upper_limit'])
    if measurement < lower:
        return 'BELOW'
    if measurement > upper:
        return 'ABOVE'
    if measurement == lower or measurement == upper:
        return 'ON_BOUNDARY'
    return 'WITHIN'


def choose_style(model_response: str) -> str:
    """Never echo unchecked model text. Only an exact, allowlisted code passes."""
    match = STYLE_RE.fullmatch((model_response or '').strip())
    return match[1].lower() if match else 'technical'


def model_style_prompt(question: str, result: dict) -> str:
    # Do not request calculations or factual claims from the SLM.
    return (
        'Choose a writing style for a short manufacturing dimensional-inspection report. '
        'Allowed output is EXACTLY one line, one of: STYLE: TECHNICAL, STYLE: PLAIN, STYLE: OPERATOR. '
        'No other text. This is a style selection only, not an inspection decision. /no_think\n'
        f'Inspection request: {question[:500]}\n'
        f'Trusted calculation decision: {result["decision"]}\n'
        'Prefer TECHNICAL by default, PLAIN for beginner-friendly wording, '
        'OPERATOR for shop-floor instructions.'
    )


def render_report(result: dict, style: str = 'technical') -> str:
    """Every factual statement, decision and action comes from deterministic code."""
    if style not in SUPPORTED_STYLES:
        style = 'technical'
    decision = result['decision']
    if decision == 'INSUFFICIENT_DATA':
        return ('Decision: INSUFFICIENT_DATA\n'
                f'Reason: {result.get("reason", "Required data missing.")}\n'
                'Next step: Provide one verified nominal, measurement, tolerance/deviations, and consistent unit.\n'
                'Evidence: Input validation; no numerical conformity conclusion was made.\n'
                'Note: Research demonstration only. No product-release authorization.')

    pos = verified_position(result)
    low, high, value, unit = (result[k] for k in ('lower_limit', 'upper_limit', 'measured', 'unit'))
    noun = {'technical': 'Dimensional conformity', 'plain': 'This measurement',
            'operator': 'The recorded dimension'}[style]
    if decision == 'PASS':
        explanation = {
            'technical': f'{noun} is satisfied: {value} {unit} is inside the inclusive specification interval [{low}, {high}] {unit}.',
            'plain': f'{noun} is within the allowed range of {low} to {high} {unit}.',
            'operator': f'{noun} is within the specified limits, including the boundaries.',
        }[style]
        next_step = 'Record the inspection result and refer it to authorized QA personnel; other acceptance criteria still apply.'
    else:
        rel = 'below the lower' if pos == 'BELOW' else 'above the upper'
        explanation = {
            'technical': f'{noun} is not satisfied: {value} {unit} is {rel} specification limit [{low}, {high}] {unit}.',
            'plain': f'{noun} is outside the allowed range of {low} to {high} {unit}.',
            'operator': 'The recorded dimension is outside the specified limits; flag the discrepancy.',
        }[style]
        next_step = 'Flag the discrepancy, verify the measurement record, and refer it to authorized QA personnel.'
    return ('Decision: ' + decision + '\n'
            + 'Allowed limits: ' + low + ' to ' + high + ' ' + unit + ' (inclusive)\n'
            + 'Measurement: ' + value + ' ' + unit + '\n'
            + 'Explanation: ' + explanation + '\n'
            + 'Next step: ' + next_step + '\n'
            + 'Evidence: Calculated from user-supplied values using Python Decimal; no external standards asserted.\n'
            + 'Note: Research demonstration only. No product-release authorization.')


def respond(question: str, style_selector: Optional[Callable[[str, dict], str]] = None,
            forced_style: str | None = None) -> tuple[str, dict]:
    """Pure orchestration, allowing GPU-free testing with stubbed SLM responses."""
    result = calculate(question)
    style = 'technical'
    if result['decision'] != 'INSUFFICIENT_DATA':
        if forced_style in SUPPORTED_STYLES:
            style = forced_style
        elif style_selector is not None:
            try:
                style = choose_style(style_selector(question, result))
            except Exception:
                # Presentation failure cannot affect the engineering result.
                style = 'technical'
    return render_report(result, style), result
