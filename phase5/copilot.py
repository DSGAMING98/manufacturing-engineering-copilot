"""Strict six-domain orchestration and Phase 4 evidence lookup.

The model (when enabled) may choose a retrieved citation only. It does not
calculate, operate equipment, approve manufacturing steps or author source facts.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from phase5.calculators import InputError, design_fit, turning_estimate, production_oee, maintenance_kpis
from src.hybrid_qa import render_report
from src.tolerance_engine import inspect
from phase4.rag_core import answer as document_answer
from phase4.retrieval import load_corpus, Chunk

DOMAINS = ('design', 'process', 'production', 'quality', 'maintenance', 'documentation')
REQUIRED = {
    'design': {'hole_min', 'hole_max', 'shaft_min', 'shaft_max'},
    'process': {'diameter_mm', 'cutting_speed_m_per_min', 'feed_mm_per_rev', 'length_mm'},
    'production': {'planned_min', 'run_min', 'ideal_cycle_min_per_part', 'total_parts', 'good_parts'},
    'quality': {'nominal', 'measured', 'unit'},
    'maintenance': {'operating_hours', 'repair_hours', 'failures'},
    'documentation': {'record_id', 'feature_id', 'drawing_id', 'revision', 'nominal',
                      'measured', 'tolerance', 'unit', 'equipment_id', 'timestamp'},
}
OPTIONAL = {
    'design': {'unit'},
    'process': {'unit'},
    'production': set(),
    'quality': {'tolerance', 'lower_dev', 'upper_dev'},
    'maintenance': set(),
    'documentation': {'operator_id'},
}
IDENTIFIER = re.compile(r'[A-Za-z0-9_.:\-]{1,64}\Z')


def _validate_fields(domain: str, fields: dict):
    if not isinstance(fields, dict) or len(fields) > 20:
        raise InputError('Expected one small object of named input fields.')
    required = REQUIRED[domain]
    unknown = set(fields) - required - OPTIONAL[domain]
    if unknown:
        raise InputError('Unsupported field(s): ' + ', '.join(sorted(map(str, unknown))))
    absent = sorted(k for k in required if k not in fields or fields[k] in (None, ''))
    if absent:
        raise InputError('Missing required field(s): ' + ', '.join(absent))
    for key, value in fields.items():
        if not isinstance(key, str) or not isinstance(value, (str, int, float)) or isinstance(value, bool):
            raise InputError('Input fields must be simple strings or numbers.')
        if len(str(value)) > 120:
            raise InputError('Input value too long: ' + key)
    if domain == 'quality':
        sym = 'tolerance' in fields
        deviations = 'lower_dev' in fields or 'upper_dev' in fields
        if sym == deviations:
            raise InputError('Specify either tolerance OR both lower_dev and upper_dev.')
        if deviations and not {'lower_dev', 'upper_dev'} <= set(fields):
            raise InputError('Both lower_dev and upper_dev are needed.')


def _quality(fields: dict) -> tuple[dict, str]:
    result = inspect(
        fields.get('nominal'), fields.get('measured'),
        tolerance=fields.get('tolerance'),
        lower_deviation=fields.get('lower_dev'),
        upper_deviation=fields.get('upper_dev'),
        unit=fields.get('unit', 'mm'),
    )
    if result['decision'] == 'INSUFFICIENT_DATA':
        raise InputError(result['reason'])
    return result, render_report(result)


def _draft_record(p: dict) -> tuple[dict, str]:
    for key in ('record_id', 'feature_id', 'drawing_id', 'revision', 'equipment_id'):
        if not IDENTIFIER.fullmatch(str(p[key])):
            raise InputError(f'{key} must be a simple 1–64 character identifier (no spaces).')
    if 'operator_id' in p and not IDENTIFIER.fullmatch(str(p['operator_id'])):
        raise InputError('operator_id must be a simple identifier.')
    try:
        timestamp = datetime.fromisoformat(str(p['timestamp']).replace('Z', '+00:00'))
    except ValueError as exc:
        raise InputError('timestamp must be ISO-8601 with timezone, such as 2026-11-13T09:30:00+05:30.') from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise InputError('timestamp requires a timezone.')
    result, _ = _quality({k: p[k] for k in ('nominal', 'measured', 'tolerance', 'unit')})
    record = {
        'document_status': 'DRAFT',
        'record_id': str(p['record_id']), 'feature_id': str(p['feature_id']),
        'drawing_id': str(p['drawing_id']), 'revision': str(p['revision']),
        'equipment_id': str(p['equipment_id']), 'timestamp': timestamp.isoformat(),
        'operator_id': str(p.get('operator_id', 'NOT_PROVIDED')),
        'nominal': result['nominal'], 'measured': result['measured'],
        'lower_limit': result['lower_limit'], 'upper_limit': result['upper_limit'],
        'unit': result['unit'], 'dimensional_check': result['decision'],
        'workflow_status': 'PENDING_COMPLETION',
    }
    report = '\n'.join([
        'DRAFT INSPECTION RECORD',
        f"Record: {record['record_id']} | feature: {record['feature_id']} | drawing: {record['drawing_id']} rev {record['revision']}",
        f"Time: {record['timestamp']} | equipment: {record['equipment_id']} | operator: {record['operator_id']}",
        f"Nominal: {record['nominal']} {record['unit']} | observed: {record['measured']} {record['unit']}",
        f"Permitted range: [{record['lower_limit']}, {record['upper_limit']}] {record['unit']}",
        f"Dimensional check only: {record['dimensional_check']}",
        'Status: PENDING_COMPLETION. Save, sign, and release controls are outside this prototype.',
    ])
    return record, report


def _render_generic(title: str, data: dict) -> str:
    rows = [title]
    for key, value in data.items():
        if key != 'note':
            rows.append(f'{key.replace("_", " ").capitalize()}: {value}')
    if 'note' in data:
        rows.append('Limitations: ' + data['note'])
    return '\n'.join(rows)


def run(domain: str, fields: dict | None = None, *, question: str | None = None,
        include_demo: bool = False, chunks: list[Chunk] | None = None, selector=None) -> dict:
    """Return a JSON-serializable report. Bad input fails closed, never guesses.

    `knowledge` is a cross-domain retrieval service, not a seventh engineered tool.
    """
    if not isinstance(domain, str):
        domain = ''
    domain = domain.lower().strip()
    if domain in ('knowledge', 'docs', 'search'):
        if fields not in (None, {}):
            return _refusal('knowledge', 'Document search accepts question only.')
        if not isinstance(question, str) or not question.strip() or len(question) > 1500:
            return _refusal('knowledge', 'Provide a document question of at most 1,500 characters.')
        try:
            evidence = document_answer(
                question, chunks=chunks if chunks is not None else load_corpus(include_demo=include_demo),
                selector=selector,
            )
        except Exception as exc:
            # Source integrity errors are displayed as refusals, not a fallback to hallucination.
            return _refusal('knowledge', f'Document index unavailable or invalid: {type(exc).__name__}: {exc}')
        cited = set(evidence.citations)
        source_index = chunks if chunks is not None else None
        if source_index is None:
            source_index = load_corpus(include_demo=include_demo)
        statuses = {c.status for c in source_index if c.citation in cited}
        provenance = ('none' if not cited else
                      'fictional_demo' if 'demo' in statuses else
                      'operator_labelled_approved_not_independently_verified')
        return {
            'domain': 'knowledge', 'status': 'NO_VERIFIED_SOURCE' if evidence.abstained else 'EXCERPTS_ONLY',
            'mode': evidence.mode, 'data': {}, 'report': evidence.text,
            'citations': list(evidence.citations), 'source_provenance': provenance,
        }
    if domain not in DOMAINS:
        return _refusal(domain or 'unknown', 'Choose one of: ' + ', '.join(DOMAINS) + '. Cross-domain document search: knowledge.')
    try:
        fields = fields if fields is not None else {}
        _validate_fields(domain, fields)
        if domain == 'design':
            data = design_fit(fields)
            report = _render_generic('DESIGN: WORST-CASE HOLE/SHAFT FIT', data)
        elif domain == 'process':
            data = turning_estimate(fields)
            report = _render_generic('PROCESS PLANNING: IDEAL TURNING ESTIMATE', data)
        elif domain == 'production':
            data = production_oee(fields)
            report = _render_generic('PRODUCTION: OEE ESTIMATE', data)
        elif domain == 'quality':
            data, report = _quality(fields)
        elif domain == 'maintenance':
            data = maintenance_kpis(fields)
            report = _render_generic('MAINTENANCE: OBSERVED RELIABILITY INDICATORS', data)
        else:
            data, report = _draft_record(fields)
    except (InputError, ValueError, TypeError, ArithmeticError) as exc:
        return _refusal(domain, str(exc))
    return {
        'domain': domain, 'status': 'CALCULATED',
        'mode': 'deterministic_python', 'data': data, 'report': report,
        'citations': [], 'verified_source': False,
    }


def _refusal(domain: str, reason: str) -> dict:
    return {
        'domain': domain, 'status': 'INSUFFICIENT_DATA', 'mode': 'input_refusal',
        'data': {}, 'report': 'INSUFFICIENT_DATA: ' + reason + '\nNo engineering decision or source claim was made.',
        'citations': [], 'verified_source': False,
    }
