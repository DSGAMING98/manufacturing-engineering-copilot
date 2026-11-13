"""Natural-language request routing for the six-domain engineering workbench.

The router is deliberately conservative: it extracts only values explicitly
present in the request and delegates calculations to ``phase5.copilot``.
It never treats an LLM-generated number as an engineering input.
"""
from __future__ import annotations

import re

from phase5.copilot import REQUIRED, run

DOMAIN_TERMS = {
    'design': ('fit', 'clearance', 'interference', 'hole', 'shaft', 'mating diameters',
               'fit envelope', 'cylindrical features', 'assembly review'),
    'process': ('turning', 'lathe', 'spindle', 'rpm', 'cutting speed', 'feed rate',
                'feed per revolution', 'cutting time', 'machining time', 'single-pass'),
    'production': ('oee', 'oee figure', 'shift', 'production run', 'line effectiveness',
                   'production effectiveness', 'availability, performance', 'yield',
                   'availability performance', 'good parts', 'good count', 'planned time',
                   'planned minutes', 'run time', 'runtime', 'cycle time', 'part-count'),
    'quality': ('tolerance', 'specification limits', 'inspection pass', 'measured diameter',
                'measured feature', 'measurement', 'gauge reads', 'conforming', 'conformity',
                'asymmetric tolerance', 'pass, fail', 'pass or fail', 'one dimension',
                'single-characteristic', 'acceptance check', 'whole-lot release'),
    'maintenance': ('mtbf', 'mttr', 'breakdown', 'failure', 'repair hours', 'repair duration',
                    'restoration time', 'operating hours', 'uptime', 'reliability indicators',
                    'remaining-life', 'remaining useful life'),
    'documentation': ('inspection record', 'inspection sheet', 'draft measurement record',
                      'traceable draft', 'drawing revision', 'record id', 'drawing id',
                      'equipment id', 'gauge id', 'final sign-off', 'controlled draft'),
    'knowledge': ('procedure excerpt', 'approved documents', 'registered source',
                  'registered work instructions', 'procedure library', 'indexed evidence',
                  'source lines', 'local procedure', 'document evidence', 'citation',
                  'traceability identifiers', 'what does'),
}

ALIASES = {
    'design': {
        'hole_min': ('hole min', 'minimum hole', 'hole minimum'),
        'hole_max': ('hole max', 'maximum hole', 'hole maximum'),
        'shaft_min': ('shaft min', 'minimum shaft', 'shaft minimum'),
        'shaft_max': ('shaft max', 'maximum shaft', 'shaft maximum'),
        'unit': ('unit',),
    },
    'process': {
        'diameter_mm': ('diameter', 'workpiece diameter'),
        'cutting_speed_m_per_min': ('cutting speed', 'surface speed'),
        'feed_mm_per_rev': ('feed', 'feed per rev', 'feed per revolution'),
        'length_mm': ('length', 'cut length', 'cutting length'),
    },
    'production': {
        'planned_min': ('planned', 'planned time', 'planned minutes'),
        'run_min': ('run', 'run time', 'operating minutes'),
        'ideal_cycle_min_per_part': ('ideal cycle', 'cycle time'),
        'total_parts': ('total', 'total parts', 'pieces produced'),
        'good_parts': ('good', 'good parts', 'accepted parts'),
    },
    'quality': {
        'nominal': ('nominal', 'target'), 'measured': ('measured', 'measurement', 'observed'),
        'tolerance': ('tolerance', 'tol'), 'lower_dev': ('lower deviation', 'lower dev'),
        'upper_dev': ('upper deviation', 'upper dev'), 'unit': ('unit',),
    },
    'maintenance': {
        'operating_hours': ('operating hours', 'uptime hours', 'operating'),
        'repair_hours': ('repair hours', 'downtime hours', 'repair'),
        'failures': ('failures', 'failure count', 'breakdowns'),
    },
    'documentation': {
        'record_id': ('record id',), 'feature_id': ('feature id',),
        'drawing_id': ('drawing id',), 'revision': ('revision', 'rev'),
        'nominal': ('nominal',), 'measured': ('measured',), 'tolerance': ('tolerance', 'tol'),
        'unit': ('unit',), 'equipment_id': ('equipment id', 'gauge id'),
        'timestamp': ('timestamp', 'time'), 'operator_id': ('operator id',),
    },
}

EXPLICIT_DOMAIN = re.compile(
    r'\b(?:domain|workspace|tool)\s*[:=]\s*'
    r'(design|process|production|quality|maintenance|documentation|knowledge)\b', re.I)
PAIR = re.compile(r'\b([a-z][a-z0-9_ ]{1,35})\s*(?:=|:)\s*([^,;\n]+)', re.I)
VALUE = r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[A-Za-z][A-Za-z0-9_.:+\-]*)'


def route_domain(prompt: str) -> tuple[str | None, dict[str, int]]:
    """Return a domain only when the request has a unique positive winner."""
    explicit = EXPLICIT_DOMAIN.search(prompt)
    if explicit:
        return explicit.group(1).lower(), {explicit.group(1).lower(): 100}
    lowered = prompt.lower()
    scores = {domain: sum(2 if ' ' in term else 1 for term in terms if term in lowered)
              for domain, terms in DOMAIN_TERMS.items()}
    best = max(scores.values(), default=0)
    winners = [domain for domain, score in scores.items() if score == best and score > 0]
    return (winners[0] if len(winners) == 1 else None), scores


def _normalise_label(label: str) -> str:
    return re.sub(r'\s+', ' ', label.lower().replace('_', ' ')).strip()


def extract_fields(domain: str, prompt: str) -> dict[str, str]:
    """Extract explicit labelled values; no positional-number guessing."""
    aliases = ALIASES.get(domain, {})
    lookup = {_normalise_label(alias): key for key, names in aliases.items()
              for alias in (key, *names)}
    fields: dict[str, str] = {}
    for match in PAIR.finditer(prompt):
        key = lookup.get(_normalise_label(match.group(1)))
        if key:
            fields[key] = match.group(2).strip().strip('.,')
    # Natural prose such as "nominal 20 mm" is accepted only with a known label.
    for key, names in aliases.items():
        if key in fields:
            continue
        for name in sorted((key.replace('_', ' '), *names), key=len, reverse=True):
            found = re.search(rf'\b{re.escape(name)}\b\s*(?:is|of|=|:)?\s*{VALUE}', prompt, re.I)
            if found:
                fields[key] = found.group(1).strip('.,')
                break
    if domain in ('design', 'quality') and 'unit' not in fields:
        units = re.findall(r'(?<![A-Za-z])(mm|in)(?![A-Za-z])', prompt, re.I)
        if units:
            fields['unit'] = units[-1].lower()
    return fields


def assist(prompt: object, *, include_demo: bool = False, chunks=None) -> dict:
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        return _clarify('Provide one manufacturing request of at most 2,000 characters.')
    prompt = prompt.strip()
    domain, scores = route_domain(prompt)
    if domain is None:
        return _clarify(
            'I could not select one workspace confidently. Mention design fit, turning process, OEE, '
            'dimensional quality, maintenance KPIs, inspection-record documentation, or document evidence.',
            scores=scores,
        )
    if domain == 'knowledge':
        result = run('knowledge', {}, question=prompt, include_demo=include_demo, chunks=chunks)
    else:
        fields = extract_fields(domain, prompt)
        missing = sorted(key for key in REQUIRED[domain] if not fields.get(key))
        if domain == 'quality' and not ({'tolerance'} <= fields.keys() or
                                        {'lower_dev', 'upper_dev'} <= fields.keys()):
            missing.append('tolerance OR lower_dev + upper_dev')
        if missing:
            return _clarify(
                f'I selected the {domain} workspace. Please supply: {", ".join(missing)}. '
                'Use labelled values such as nominal=20, measured=20.03.',
                domain=domain, extracted_fields=fields, missing_fields=missing,
            )
        result = run(domain, fields)
    result['assistant'] = {
        'routed_domain': domain,
        'routing_mode': 'conservative_label_and_keyword_router',
        'model_arithmetic': False,
    }
    return result


def _clarify(message: str, **extra) -> dict:
    payload = {
        'domain': extra.pop('domain', 'assistant'), 'status': 'NEEDS_INPUT',
        'mode': 'assistant_clarification', 'data': {}, 'report': message,
        'citations': [], 'verified_source': False,
    }
    payload['assistant'] = extra
    return payload
