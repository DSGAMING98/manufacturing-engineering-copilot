"""Generate reproducible, labeled SYNTHETIC training data; never claim industrial provenance.

Training/validation/test split phrasings and numeric ranges differ on purpose.
This remains synthetic template data, NOT an independent real-world benchmark.
"""
from __future__ import annotations
from collections import Counter
from decimal import Decimal as D
import hashlib
import random

from phase3.shared import DATA_DIR, atomic_json, settings, write_jsonl
from src.tolerance_engine import inspect

SYSTEM = (
    'You are a manufacturing quality-assurance research assistant for ONE scalar dimensional inspection. '
    'Use only supplied dimensions and inclusive tolerance bounds. Do not invent standards, measured values, '
    'calibration evidence or product-release authorization. Reply with exactly four lines starting with: '
    'Decision:, Rationale:, Next step:, Evidence:. Decision must be PASS, FAIL or INSUFFICIENT_DATA. '
    'Treat the dimensional decision as one check, not an entire part-release verdict. /no_think'
)

# Held-out templates use different phrasing, not just a new random seed.
TEMPLATES = {
    'train': [
        'Dimensional QA request for a single feature. Fields: {fields}. State the decision and one QA next action.',
        'Shop-floor dimensional record: {fields}. Evaluate only this measured dimension.',
        'Check the supplied scalar inspection: {fields}. No part or lot release is requested.',
        'Manufacturing quality worksheet fields are {fields}. Return an auditable one-dimension result.',
    ],
    'validation': [
        'A technician recorded one feature as {fields}. Is this single dimensional reading in specification?',
        'Quality review note for one characteristic: {fields}. Explain the dimensional decision.',
    ],
    'test': [
        'Metrology handover: {fields}. Classify only the specified dimension, not the whole part.',
        'Inspection finding submitted for review, {fields}. What does this single check show?',
        'The operator supplied {fields}. Flag any missing or invalid evidence before deciding.',
        'Do an individual tolerance-limit check using these input fields: {fields}.',
    ],
}

KINDS = ('PASS', 'FAIL', 'INSUFFICIENT_DATA')


def fmt(number: D) -> str:
    """Keep decimal precision visible, without binary float arithmetic."""
    return format(number, 'f')


def scenario(split: str, index: int, kind: str, rng: random.Random) -> dict:
    """Construct one case. Each split uses disjoint nominal ranges & phrase templates."""
    offset = {'train': D('5'), 'validation': D('85'), 'test': D('125')}[split]
    nominal = offset + D(index) * D('0.137') + D(rng.randrange(0, 10)) / D('10000')
    unit = 'in' if index % 11 == 0 else 'mm'
    # Do not silently convert dimensions. All values share the declared unit.
    tol = D(rng.choice(('0.01', '0.015', '0.025', '0.05', '0.075', '0.1')))
    asymmetric = index % 4 == 0
    if asymmetric:
        low_dev = -tol
        high_dev = tol * D(rng.choice(('0.5', '1', '2')))
        fields = {'nominal': fmt(nominal), 'lower_dev': fmt(low_dev),
                  'upper_dev': fmt(high_dev), 'unit': unit}
    else:
        low_dev, high_dev = -tol, tol
        fields = {'nominal': fmt(nominal), 'tolerance': fmt(tol), 'unit': unit}
    lower, upper = nominal + low_dev, nominal + high_dev
    epsilon = D('0.0001')
    if kind == 'PASS':
        measurement = rng.choice((lower, upper, nominal, (lower + upper) / 2,
                                  lower + epsilon, upper - epsilon))
        fields['measured'] = fmt(measurement)
    elif kind == 'FAIL':
        measurement = rng.choice((lower - epsilon, upper + epsilon,
                                  lower - D('0.01'), upper + D('0.01'),
                                  lower - D('0.1'), upper + D('0.1')))
        fields['measured'] = fmt(measurement)
    else:
        # Explicitly represent missing, unsupported or self-contradictory data.
        choice = index % 8
        fields['measured'] = fmt(nominal)
        if choice == 0:
            fields['measured'] = 'missing'
        elif choice == 1:
            fields['measured'] = 'abc'
        elif choice == 2:
            fields['unit'] = 'cm'
        elif choice == 3:
            fields['nominal'] = 'NaN'
        elif choice == 4:
            fields.pop('tolerance', None)
            fields.pop('lower_dev', None)
            fields.pop('upper_dev', None)
        elif choice == 5:
            fields.pop('tolerance', None)
            fields['lower_dev'] = '0.02'
            fields['upper_dev'] = '-0.01'
        elif choice == 6:
            fields.pop('lower_dev', None)
            fields.pop('upper_dev', None)
            fields['tolerance'] = '-0.05'
        else:
            fields['measured'] = 'Infinity'
    # Vary key order without violating the strict Phase 2 hybrid parser.
    pairs = list(fields.items())
    rng.shuffle(pairs)
    structured = ' '.join(f'{key}={value}' for key, value in pairs)
    result = inspect(fields.get('nominal'), fields.get('measured'),
                     lower_deviation=fields.get('lower_dev'), upper_deviation=fields.get('upper_dev'),
                     tolerance=fields.get('tolerance'), unit=fields.get('unit'))
    if result['decision'] != kind:
        raise AssertionError(f'{split} {index} expected {kind}, got {result}')

    if kind == 'INSUFFICIENT_DATA':
        rationale = 'The supplied dimensional fields are missing, invalid or internally inconsistent; conformity cannot be established.'
        next_action = 'Obtain valid and complete evidence and route the record to authorized QA personnel.'
    else:
        rationale = (f'Measurement {fields["measured"]} {unit}; inclusive limits '
                     f'[{fmt(lower)}, {fmt(upper)}] {unit}. '
                     + ('This dimension meets its stated limits.' if kind == 'PASS' else
                        'This dimension is outside its stated limits.'))
        next_action = ('Record this single-dimensional finding for authorized QA review; other acceptance criteria apply.'
                       if kind == 'PASS' else
                       'Flag the nonconforming measurement, verify the record and request authorized QA review.')
    prefix = {'train': 'TR', 'validation': 'VA', 'test': 'TE'}[split]
    pid = f'P3-{prefix}-{index:04d}'
    expected = ('Decision: ' + kind + '\nRationale: ' + rationale + '\nNext step: '
                + next_action + '\nEvidence: ' + pid + ' (synthetic computed scenario; no standard asserted).')
    question = TEMPLATES[split][index % len(TEMPLATES[split])].format(fields=structured)
    return {
        'id': pid, 'case_group': f'feature-{pid}', 'domain': 'quality_assurance',
        'source_kind': 'synthetic_rule_generated_phase3', 'reviewed_by_engineer': False,
        'provenance': 'Synthetic: programmatically generated and checked with src.tolerance_engine.inspect; not measured industrial data.',
        'gold_decision': kind, 'structured_input': structured,
        'reference_input': fields, 'case_family': ('asymmetric' if asymmetric else 'symmetric'),
        'messages': [{'role': 'system', 'content': SYSTEM},
                     {'role': 'user', 'content': question},
                     {'role': 'assistant', 'content': expected}],
    }


def build(force: bool = False):
    cfg = settings()
    counts = cfg['counts']
    if any(n % 3 for n in counts.values()):
        raise ValueError('All counts must be multiples of three for balance.')
    targets = [DATA_DIR / f'{split}.jsonl' for split in ('train', 'validation', 'test')]
    if not force and any(p.exists() for p in targets):
        raise FileExistsError('Phase 3 data already exists. Refusing to overwrite; use --force to regenerate deterministically.')
    manifest = {'purpose': 'SYNTHETIC QA research only; not real manufacturing evidence',
                'seed': cfg['data_seed'], 'split_separation': 'Distinct numeric ranges and prompt templates',
                'counts': {}, 'files_sha256': {}}
    for j, split in enumerate(('train', 'validation', 'test')):
        rng = random.Random(cfg['data_seed'] + j * 7919)
        total = counts[split]
        records = [scenario(split, idx, KINDS[idx % 3], rng) for idx in range(1, total + 1)]
        rng.shuffle(records)
        path = DATA_DIR / f'{split}.jsonl'
        write_jsonl(path, records)
        manifest['counts'][split] = dict(Counter(x['gold_decision'] for x in records))
        manifest['files_sha256'][split] = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f'{split}: {total} SYNTHETIC records, balanced PASS/FAIL/INSUFFICIENT_DATA')
    atomic_json(DATA_DIR / 'manifest.json', manifest)
    return manifest


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Regenerate deterministic synthetic data')
    args = parser.parse_args()
    build(force=args.force)
    print('Prepared:', DATA_DIR)
    print('Warning: synthetic data only; real industrial validation remains outstanding.')


if __name__ == '__main__':
    main()
