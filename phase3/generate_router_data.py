"""Build balanced synthetic intent-routing data for the six-domain copilot."""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

from phase3.shared import ROOT, atomic_json, write_jsonl

DATA_DIR = ROOT / 'phase3' / 'router_data'
LABELS = ('design', 'process', 'production', 'quality', 'maintenance', 'documentation', 'knowledge')
SYSTEM = (
    'Route one manufacturing-engineering request to exactly one tool. '
    'Use design for hole/shaft fit, clearance, interference, or transition. '
    'Use process for turning RPM, feed, cutting speed, or ideal machining time. '
    'Use production for OEE, shift availability, performance, yield, or part counts. '
    'Use quality for one measured dimension against tolerance or specification limits. '
    'Use maintenance for failures, repairs, MTBF, MTTR, or historical equipment reliability. '
    'Use documentation when the user wants to create or format a draft inspection record. '
    'Use knowledge when the user wants to search, quote, cite, or answer from registered documents. '
    'Return exactly one line using '
    'Tool: design, Tool: process, Tool: production, Tool: quality, Tool: maintenance, '
    'Tool: documentation, or Tool: knowledge. Do not calculate or explain. /no_think'
)

SUBJECTS = {
    'design': ('hole and shaft fit', 'worst-case clearance', 'interference between mating diameters',
               'dimensional fit limits', 'transition fit between cylindrical features',
               'assembly clearance envelope', 'minimum bore versus maximum pin',
               'classify clearance interference or transition'),
    'process': ('turning spindle speed', 'ideal cutting time', 'feed rate for a lathe pass',
                'turning process estimate', 'surface speed to lathe RPM',
                'single-pass machining duration', 'feed travel per minute',
                'preliminary cutting parameter calculation'),
    'production': ('overall equipment effectiveness', 'availability performance and quality',
                   'shift OEE', 'production effectiveness', 'planned time versus runtime',
                   'ideal cycle output and good count', 'line utilization and yield',
                   'equipment effectiveness from part counts'),
    'quality': ('single dimensional tolerance check', 'measured feature conformity',
                'inspection pass or fail', 'inclusive tolerance limits',
                'gauge reading against specification limits', 'asymmetric deviation check',
                'one characteristic acceptance result', 'missing inspection evidence status'),
    'maintenance': ('MTBF and MTTR', 'historical failure and repair indicators',
                    'observed equipment availability', 'maintenance reliability metrics',
                    'breakdown frequency and restoration duration', 'uptime per recorded failure',
                    'retrospective repair performance', 'historical reliability not remaining life'),
    'documentation': ('draft inspection record', 'traceable measurement record',
                      'drawing revision inspection form', 'review-required QA record',
                      'format supplied evidence into a controlled draft',
                      'create a not-approved measurement sheet',
                      'inspection record with gauge and operator identifiers',
                      'prepare a human-signoff document'),
    'knowledge': ('find the relevant procedure excerpt', 'search registered manufacturing documents',
                  'show source lines about traceability', 'retrieve cited document evidence',
                  'check what approved work instructions say',
                  'find a nonconformance requirement in indexed sources',
                  'locate record-retention wording in the procedure library',
                  'abstain when registered evidence is absent',
                  'cite the exact passage from an approved document',
                  'answer only from source-backed excerpts'),
}

TEMPLATES = {
    'train': (
        'Please help with {subject}{context}.',
        'Engineering request: {subject}{context}.',
        'Which workspace handles {subject}{context}?',
        'I need support for {subject}{context}.',
        'Shop-floor question about {subject}{context}.',
        'Send this question to the correct engineering workspace: {subject}{context}.',
        'Route the user request concerning {subject}{context}.',
    ),
    'validation': (
        'A technician wants to work out {subject}{context}. Route this request.',
        'Select the engineering capability for {subject}{context}.',
        'Where should the copilot send a question concerning {subject}{context}?',
    ),
    'test': (
        'Incoming manufacturing task — {subject}{context}. Choose one available tool.',
        'The user is asking for assistance with {subject}{context}. Identify the right function.',
        'For this work item, determine the intended workspace: {subject}{context}.',
        'Classify the following practical request without solving it: {subject}{context}.',
    ),
}

CONTEXT = (
    '', ' for one component', ' using supplied shop-floor values', ' without approving product release',
    ' and needs a traceable result', ' for a prototype review', ' with missing inputs to be requested',
)


def build(force: bool = False, train_only: bool = False) -> dict:
    counts = {'train': 1050, 'validation': 140, 'test': 210}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    selected = ('train',) if train_only else tuple(counts)
    if not force and any((DATA_DIR / f'{split}.jsonl').exists() for split in selected):
        raise FileExistsError('Router data already exists; pass --force to regenerate.')
    manifest = {
        'purpose': 'Synthetic seven-way tool-routing research data; not industrial validation',
        'seed': 20261113, 'labels': list(LABELS), 'counts': {}, 'sha256': {},
        'split_policy': 'Disjoint instruction templates; balanced labels; deterministic generation',
    }
    if train_only and (DATA_DIR / 'manifest.json').exists():
        import json
        previous = json.loads((DATA_DIR / 'manifest.json').read_text(encoding='utf-8'))
        for split in ('validation', 'test'):
            manifest['counts'][split] = previous['counts'][split]
            manifest['sha256'][split] = previous['sha256'][split]
    for split_index, (split, total) in enumerate(counts.items()):
        if split not in selected:
            continue
        rng = random.Random(20261113 + split_index * 104729)
        rows = []
        per_label = total // len(LABELS)
        for label in LABELS:
            combinations = [(subject, context, template)
                            for subject in SUBJECTS[label]
                            for context in CONTEXT
                            for template in TEMPLATES[split]]
            rng.shuffle(combinations)
            if len(combinations) < per_label:
                raise ValueError(f'Not enough unique prompt combinations for {split}/{label}')
            for index, (subject, context, template) in enumerate(combinations[:per_label]):
                request = template.format(subject=subject, context=context)
                rows.append({
                    'id': f'R-{split[:2].upper()}-{label.upper()}-{index + 1:03d}',
                    'source_kind': 'synthetic_intent_template', 'reviewed_by_engineer': False,
                    'gold_tool': label,
                    'messages': [
                        {'role': 'system', 'content': SYSTEM},
                        {'role': 'user', 'content': request},
                        {'role': 'assistant', 'content': f'Tool: {label}'},
                    ],
                })
        rng.shuffle(rows)
        path = DATA_DIR / f'{split}.jsonl'
        write_jsonl(path, rows)
        manifest['counts'][split] = {'total': len(rows), 'per_label': per_label}
        manifest['sha256'][split] = hashlib.sha256(path.read_bytes()).hexdigest()
    atomic_json(DATA_DIR / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--train-only', action='store_true',
                        help='Regenerate training rows while preserving frozen validation and test files')
    args = parser.parse_args()
    print(build(force=args.force, train_only=args.train_only))
