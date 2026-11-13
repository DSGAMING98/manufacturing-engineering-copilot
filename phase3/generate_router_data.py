"""Build balanced synthetic intent-routing data for the six-domain copilot."""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

from phase3.shared import ROOT, atomic_json, write_jsonl

DATA_DIR = ROOT / 'phase3' / 'router_data'
LABELS = ('design', 'process', 'production', 'quality', 'maintenance', 'documentation', 'knowledge')
SYSTEM = (
    'Route one manufacturing-engineering request to exactly one tool. Return exactly one line using '
    'Tool: design, Tool: process, Tool: production, Tool: quality, Tool: maintenance, '
    'Tool: documentation, or Tool: knowledge. Do not calculate or explain. /no_think'
)

SUBJECTS = {
    'design': ('hole and shaft fit', 'worst-case clearance', 'interference between mating diameters', 'dimensional fit limits'),
    'process': ('turning spindle speed', 'ideal cutting time', 'feed rate for a lathe pass', 'turning process estimate'),
    'production': ('overall equipment effectiveness', 'availability performance and quality', 'shift OEE', 'production effectiveness'),
    'quality': ('single dimensional tolerance check', 'measured feature conformity', 'inspection pass or fail', 'inclusive tolerance limits'),
    'maintenance': ('MTBF and MTTR', 'historical failure and repair indicators', 'observed equipment availability', 'maintenance reliability metrics'),
    'documentation': ('draft inspection record', 'traceable measurement record', 'drawing revision inspection form', 'review-required QA record'),
    'knowledge': ('find the relevant procedure excerpt', 'search registered manufacturing documents', 'show source lines about traceability', 'retrieve cited document evidence'),
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


def build(force: bool = False) -> dict:
    counts = {'train': 700, 'validation': 140, 'test': 210}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not force and any((DATA_DIR / f'{split}.jsonl').exists() for split in counts):
        raise FileExistsError('Router data already exists; pass --force to regenerate.')
    manifest = {
        'purpose': 'Synthetic seven-way tool-routing research data; not industrial validation',
        'seed': 20261113, 'labels': list(LABELS), 'counts': {}, 'sha256': {},
        'split_policy': 'Disjoint instruction templates; balanced labels; deterministic generation',
    }
    for split_index, (split, total) in enumerate(counts.items()):
        rng = random.Random(20261113 + split_index * 104729)
        rows = []
        per_label = total // len(LABELS)
        for label in LABELS:
            for index in range(per_label):
                subject = SUBJECTS[label][index % len(SUBJECTS[label])]
                context = CONTEXT[(index * 3 + split_index) % len(CONTEXT)]
                template = TEMPLATES[split][index % len(TEMPLATES[split])]
                request = template.format(subject=subject, context=context)
                rows.append({
                    'id': f'R-{split[:2].upper()}-{label[:3].upper()}-{index + 1:03d}',
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
    args = parser.parse_args()
    print(build(force=args.force))
