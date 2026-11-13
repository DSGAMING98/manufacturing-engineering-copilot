"""Fail-closed structural and provenance validation for router datasets."""
from __future__ import annotations

from collections import Counter
import hashlib
import json

from phase3.generate_router_data import DATA_DIR, LABELS
from phase3.shared import read_jsonl

EXPECTED = {
    'train': 1050,
    'validation': 140,
    'test': 210,
    'manual_challenge': 35,
    'holdout2': 49,
}
CHALLENGE_SHA256 = {
    'manual_challenge': '622543c2c4c451f19984876726eebad308c7e4d75b4ee9d1542733e7c6171d2c',
    'holdout2': '1b3e7e2016ec8abc7e4260df812726605f9c6eec8706a0e9527d88f6400faba5',
}


def validate() -> dict:
    manifest = json.loads((DATA_DIR / 'manifest.json').read_text(encoding='utf-8'))
    errors: list[str] = []
    prompts: dict[str, str] = {}
    total = 0
    per_file = {}
    for split, expected_count in EXPECTED.items():
        path = DATA_DIR / f'{split}.jsonl'
        rows = read_jsonl(path)
        per_file[split] = len(rows)
        total += len(rows)
        if len(rows) != expected_count:
            errors.append(f'{split}: expected {expected_count} rows, found {len(rows)}')
        counts = Counter()
        identities = set()
        for index, row in enumerate(rows, 1):
            where = f'{split}:{index}'
            required = {'id', 'source_kind', 'reviewed_by_engineer', 'gold_tool', 'messages'}
            if not required <= set(row):
                errors.append(f'{where}: missing required keys')
                continue
            label = row['gold_tool']
            if label not in LABELS:
                errors.append(f'{where}: invalid label {label!r}')
                continue
            counts[label] += 1
            identity = (label, row['id'])
            if identity in identities:
                errors.append(f'{where}: duplicate label/id identity {identity!r}')
            identities.add(identity)
            messages = row['messages']
            if (not isinstance(messages, list) or len(messages) != 3 or
                    [message.get('role') for message in messages] != ['system', 'user', 'assistant']):
                errors.append(f'{where}: messages must be system/user/assistant')
                continue
            if not all(isinstance(message.get('content'), str) and message['content'].strip()
                       for message in messages):
                errors.append(f'{where}: blank or non-string message content')
            if messages[2]['content'] != f'Tool: {label}':
                errors.append(f'{where}: completion does not match gold label')
            prompt = messages[1]['content'].strip().casefold()
            previous = prompts.get(prompt)
            if previous:
                errors.append(f'{where}: user prompt duplicates {previous}')
            else:
                prompts[prompt] = where
            if row['reviewed_by_engineer'] is not False:
                errors.append(f'{where}: synthetic/challenge row must not claim engineer review')
        expected_per_label = expected_count // len(LABELS)
        if set(counts) != set(LABELS) or any(counts[label] != expected_per_label for label in LABELS):
            errors.append(f'{split}: labels are not balanced: {dict(counts)}')
        if split in ('train', 'validation', 'test'):
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if manifest['sha256'].get(split) != actual_hash:
                errors.append(f'{split}: SHA-256 does not match manifest')
            if manifest['counts'].get(split, {}).get('total') != expected_count:
                errors.append(f'{split}: manifest count mismatch')
        elif split in CHALLENGE_SHA256:
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_hash != CHALLENGE_SHA256[split]:
                errors.append(f'{split}: frozen challenge SHA-256 mismatch')
    if errors:
        raise ValueError('Router data validation failed:\n- ' + '\n- '.join(errors))
    return {
        'status': 'PASS', 'records_valid': total, 'records_total': total,
        'record_validation_rate': 1.0, 'files': per_file,
        'labels': list(LABELS), 'cross_split_duplicate_prompts': 0,
        'claim_boundary': 'Structural/provenance validation only; not model or industrial accuracy.',
    }


if __name__ == '__main__':
    print(json.dumps(validate(), indent=2))
