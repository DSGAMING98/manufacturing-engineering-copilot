"""Synthetic dataset integrity, contamination checks, reproducibility manifest audit."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path

from phase3.shared import DATA_DIR, read_jsonl, settings
from src.tolerance_engine import inspect

LABELS = {'PASS', 'FAIL', 'INSUFFICIENT_DATA'}


def validate(data_dir: Path = DATA_DIR, check_manifest: bool = True):
    data_dir = Path(data_dir)
    ids, groups, questions, canonical_inputs = set(), set(), set(), set()
    counts = {}
    for split in ('train', 'validation', 'test'):
        path = data_dir / f'{split}.jsonl'
        records = read_jsonl(path)
        if not records:
            raise ValueError(f'Empty or missing dataset: {path}')
        labels = Counter()
        for line, row in enumerate(records, 1):
            where = f'{path.name} record {line}'
            required = ('id', 'case_group', 'source_kind', 'reviewed_by_engineer', 'gold_decision',
                        'structured_input', 'reference_input', 'messages', 'provenance')
            missing = [key for key in required if key not in row]
            if missing:
                raise ValueError(f'{where}: missing keys {missing}')
            if row['gold_decision'] not in LABELS:
                raise ValueError(f'{where}: invalid label')
            if row['source_kind'] != 'synthetic_rule_generated_phase3' or row['reviewed_by_engineer'] is not False:
                raise ValueError(f'{where}: misleading data provenance')
            if row['id'] in ids or row['case_group'] in groups:
                raise ValueError(f'{where}: duplicate record ID / leakage group')
            ids.add(row['id']); groups.add(row['case_group'])
            messages = row['messages']
            if not isinstance(messages, list) or [m.get('role') for m in messages] != ['system', 'user', 'assistant']:
                raise ValueError(f'{where}: invalid chat format')
            if any(not isinstance(m.get('content'), str) or not m['content'].strip() for m in messages):
                raise ValueError(f'{where}: empty chat content')
            question_key = hashlib.sha256(messages[1]['content'].strip().casefold().encode('utf-8')).hexdigest()
            if question_key in questions:
                raise ValueError(f'{where}: duplicated model prompt across splits')
            questions.add(question_key)
            canonical_key = tuple(sorted(row['reference_input'].items()))
            if canonical_key in canonical_inputs:
                raise ValueError(f'{where}: identical canonical scenario across splits')
            canonical_inputs.add(canonical_key)
            if row['structured_input'] not in messages[1]['content']:
                raise ValueError(f'{where}: user question missing structured input')
            gold = row['gold_decision']
            if not messages[2]['content'].startswith(f'Decision: {gold}\n'):
                raise ValueError(f'{where}: answer contradicts gold decision')
            if 'ISO ' in messages[2]['content'] or 'release authorized' in messages[2]['content'].lower():
                raise ValueError(f'{where}: ungrounded standards or authorization claim')
            args = row['reference_input']
            result = inspect(args.get('nominal'), args.get('measured'),
                             lower_deviation=args.get('lower_dev'), upper_deviation=args.get('upper_dev'),
                             tolerance=args.get('tolerance'), unit=args.get('unit'))
            if result['decision'] != gold:
                raise ValueError(f'{where}: synthetic arithmetic/label mismatch')
            if result['decision'] != 'INSUFFICIENT_DATA':
                expected_bounds = f'[{result["lower_limit"]}, {result["upper_limit"]}]'
                if expected_bounds not in messages[2]['content']:
                    raise ValueError(f'{where}: incorrect or missing computed bounds')
            labels[gold] += 1
        counts[split] = {'rows': len(records), 'labels': dict(labels),
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if check_manifest:
        manifest = json.loads((data_dir / 'manifest.json').read_text(encoding='utf-8'))
        for split in counts:
            if manifest['files_sha256'][split] != counts[split]['sha256']:
                raise ValueError(f'Manifest fingerprint mismatch for {split}; data changed since generation')
            if manifest['counts'][split] != counts[split]['labels']:
                raise ValueError(f'Manifest counts do not match {split}')
            if len(read_jsonl(data_dir / f'{split}.jsonl')) != settings()['counts'][split]:
                raise ValueError(f'Split {split} count differs from configured count')
    return counts


def main():
    counts = validate()
    print(json.dumps(counts, indent=2))
    print('PASS: schema, provenance, labels, computed limits, split isolation, SHA256 manifest')
    print('WARNING: this is a synthetic template dataset, NOT industrial validation.')


if __name__ == '__main__':
    main()
