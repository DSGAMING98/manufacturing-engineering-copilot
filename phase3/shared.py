"""Small standard-library utilities for Phase 3. No GPU dependencies at import."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'phase3' / 'data'
RESULTS_DIR = ROOT / 'results' / 'phase3'

CLASSIFIER_SYSTEM = (
    'Classify one scalar dimensional-inspection request. Use only supplied fields and inclusive bounds. '
    'Return exactly one line: Decision: PASS, Decision: FAIL, or Decision: INSUFFICIENT_DATA. '
    'Do not explain, invent evidence, cite standards, or authorize product release. /no_think'
)


def settings():
    return json.loads((ROOT / 'configs' / 'phase3_v2.json').read_text(encoding='utf-8'))


def read_jsonl(path: Path):
    result = []
    with path.open(encoding='utf-8') as f:
        for index, line in enumerate(f, 1):
            if line.strip():
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f'{path}:{index}: invalid JSON') from exc
    return result


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)
