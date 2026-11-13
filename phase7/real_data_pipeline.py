"""Fail-closed real manufacturing data pipeline using only the Python standard library.

The pipeline validates authorization/provenance, de-identification, independent
annotations, group-isolated splits, local SQLite ingestion, and routing metrics.
It never creates or labels manufacturing research records automatically.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
from datetime import datetime
import hashlib
import json
from math import sqrt
from pathlib import Path
import random
import re
import sqlite3
from typing import Iterable

TOOLS = ('design', 'process', 'production', 'quality', 'maintenance', 'documentation', 'knowledge')
REAL_SOURCE_KINDS = {
    'engineering_request', 'drawing_review', 'process_plan', 'mes_export',
    'inspection_record', 'cmm_export', 'ncr_record', 'cmms_work_order',
    'maintenance_event', 'approved_document_query', 'operator_request',
}
ETHICS_STATUSES = {'not_human_subjects', 'approved', 'exempt', 'pending'}
ACCESS_LEVELS = {'restricted', 'controlled', 'open'}
HEX64 = re.compile(r'^[0-9a-f]{64}$')
EMAIL = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I)
DIRECT_IDENTIFIER_KEYS = {
    'name', 'email', 'phone', 'address', 'employee_name', 'customer_name',
    'supplier_name', 'serial_number', 'raw_operator_id',
}
REQUIRED_RECORD_FIELDS = {
    'record_id', 'domain', 'source_kind', 'source_system', 'source_record_id_hash',
    'event_timestamp', 'site_group', 'product_group', 'machine_group', 'split_group',
    'request_text', 'gold_tool', 'required_fields', 'source_sha256',
    'permission_reference', 'deidentified', 'reviewer_1_id_hash', 'reviewer_1_role',
    'reviewer_1_label', 'reviewer_2_id_hash', 'reviewer_2_role', 'reviewer_2_label',
    'adjudicated_label',
}
REQUIRED_MANIFEST_FIELDS = {
    'dataset_id', 'version', 'dataset_kind', 'owner_role', 'permission_reference',
    'allowed_purpose', 'access_level', 'ethics_review_status',
    'deidentification_method', 'created_at', 'data_sha256', 'record_count',
}


class DataValidationError(ValueError):
    """Raised when a real-data requirement is not satisfied."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding='utf-8') as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DataValidationError(f'{path}:{line_number}: invalid JSON: {exc.msg}') from exc
            if not isinstance(item, dict):
                raise DataValidationError(f'{path}:{line_number}: each line must be a JSON object')
            rows.append(item)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def convert_annotation_csv(csv_path: Path, jsonl_path: Path) -> dict:
    """Convert the controlled annotation sheet into the validated JSONL shape."""
    with csv_path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DataValidationError('annotation CSV requires a header row')
        missing = REQUIRED_RECORD_FIELDS - set(reader.fieldnames)
        if missing:
            raise DataValidationError(f'annotation CSV is missing columns {sorted(missing)}')
        rows = []
        for line_number, raw in enumerate(reader, 2):
            row = {key: value.strip() if isinstance(value, str) else value for key, value in raw.items()}
            row['required_fields'] = [item.strip() for item in row['required_fields'].split(';') if item.strip()]
            normalized = str(row['deidentified']).casefold()
            if normalized not in ('true', 'false'):
                raise DataValidationError(f'{csv_path}:{line_number}: deidentified must be true or false')
            row['deidentified'] = normalized == 'true'
            if not row.get('adjudication_role'):
                row.pop('adjudication_role', None)
            rows.append(row)
    write_jsonl(jsonl_path, rows)
    return {'status': 'PASS', 'source': str(csv_path), 'output': str(jsonl_path),
            'records_converted': len(rows), 'data_sha256': sha256_file(jsonl_path)}


def _timestamp(value: object, where: str) -> datetime:
    if not isinstance(value, str):
        raise DataValidationError(f'{where}: timestamp must be a string')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise DataValidationError(f'{where}: invalid ISO-8601 timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DataValidationError(f'{where}: timestamp requires a timezone')
    return parsed


def _nonempty_string(row: dict, key: str, where: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DataValidationError(f'{where}: {key} must be a non-empty string')
    return value.strip()


def _validate_manifest(manifest: dict, data_path: Path, row_count: int) -> None:
    missing = REQUIRED_MANIFEST_FIELDS - set(manifest)
    if missing:
        raise DataValidationError(f'manifest: missing fields {sorted(missing)}')
    if manifest['dataset_kind'] != 'real_authorized':
        raise DataValidationError('manifest: dataset_kind must be real_authorized')
    if manifest['access_level'] not in ACCESS_LEVELS:
        raise DataValidationError('manifest: invalid access_level')
    if manifest['ethics_review_status'] not in ETHICS_STATUSES:
        raise DataValidationError('manifest: invalid ethics_review_status')
    if manifest['ethics_review_status'] == 'pending':
        raise DataValidationError('manifest: ethics determination is still pending')
    if manifest['record_count'] != row_count:
        raise DataValidationError('manifest: record_count does not match data')
    if manifest['data_sha256'] != sha256_file(data_path):
        raise DataValidationError('manifest: data_sha256 does not match data file')
    _timestamp(manifest['created_at'], 'manifest.created_at')
    for key in ('dataset_id', 'version', 'owner_role', 'permission_reference',
                'allowed_purpose', 'deidentification_method'):
        _nonempty_string(manifest, key, 'manifest')


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    observed = sum(a == b for a, b in pairs) / len(pairs)
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum((left[label] / len(pairs)) * (right[label] / len(pairs)) for label in TOOLS)
    return 1.0 if expected == 1.0 and observed == 1.0 else (observed - expected) / (1 - expected)


def validate_dataset(data_path: Path, manifest_path: Path) -> dict:
    rows = read_jsonl(data_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict):
        raise DataValidationError('manifest must be a JSON object')
    _validate_manifest(manifest, data_path, len(rows))
    if not rows:
        raise DataValidationError('dataset must contain at least one real record')

    ids: set[str] = set()
    prompt_hashes: set[str] = set()
    label_counts = Counter()
    source_counts = Counter()
    groups = set()
    annotation_pairs: list[tuple[str, str]] = []
    disagreements = 0

    for index, row in enumerate(rows, 1):
        where = f'{data_path.name}:{index}'
        missing = REQUIRED_RECORD_FIELDS - set(row)
        if missing:
            raise DataValidationError(f'{where}: missing fields {sorted(missing)}')
        forbidden = DIRECT_IDENTIFIER_KEYS & set(row)
        if forbidden:
            raise DataValidationError(f'{where}: direct identifier fields are prohibited: {sorted(forbidden)}')
        record_id = _nonempty_string(row, 'record_id', where)
        if record_id in ids:
            raise DataValidationError(f'{where}: duplicate record_id {record_id}')
        ids.add(record_id)
        domain = _nonempty_string(row, 'domain', where)
        gold = _nonempty_string(row, 'gold_tool', where)
        if domain not in TOOLS or gold not in TOOLS or domain != gold:
            raise DataValidationError(f'{where}: domain and gold_tool must match an allowlisted tool')
        source_kind = _nonempty_string(row, 'source_kind', where)
        if source_kind not in REAL_SOURCE_KINDS:
            raise DataValidationError(f'{where}: source_kind is not an allowlisted real source')
        if row['deidentified'] is not True:
            raise DataValidationError(f'{where}: deidentified must be true')
        if row['permission_reference'] != manifest['permission_reference']:
            raise DataValidationError(f'{where}: permission_reference does not match manifest')
        for key in ('source_record_id_hash', 'source_sha256', 'reviewer_1_id_hash', 'reviewer_2_id_hash'):
            value = _nonempty_string(row, key, where).lower()
            if not HEX64.fullmatch(value):
                raise DataValidationError(f'{where}: {key} must be a lowercase SHA-256 value')
        if row['reviewer_1_id_hash'] == row['reviewer_2_id_hash']:
            raise DataValidationError(f'{where}: two independent reviewer identifiers are required')
        request = _nonempty_string(row, 'request_text', where)
        if EMAIL.search(request):
            raise DataValidationError(f'{where}: possible email address found in request_text')
        prompt_hash = hashlib.sha256(request.casefold().strip().encode()).hexdigest()
        if prompt_hash in prompt_hashes:
            raise DataValidationError(f'{where}: duplicate normalized request_text')
        prompt_hashes.add(prompt_hash)
        if not isinstance(row['required_fields'], list) or not all(
                isinstance(item, str) and item.strip() for item in row['required_fields']):
            raise DataValidationError(f'{where}: required_fields must be a list of strings')
        _timestamp(row['event_timestamp'], f'{where}.event_timestamp')
        for key in ('source_system', 'site_group', 'product_group', 'machine_group',
                    'split_group', 'reviewer_1_role', 'reviewer_2_role'):
            _nonempty_string(row, key, where)
        r1, r2 = row['reviewer_1_label'], row['reviewer_2_label']
        final = row['adjudicated_label']
        if r1 not in TOOLS or r2 not in TOOLS or final not in TOOLS:
            raise DataValidationError(f'{where}: annotation labels must be allowlisted tools')
        if final != gold:
            raise DataValidationError(f'{where}: adjudicated_label must equal gold_tool')
        if r1 != r2:
            disagreements += 1
            _nonempty_string(row, 'adjudication_role', where)
        annotation_pairs.append((r1, r2))
        label_counts[gold] += 1
        source_counts[source_kind] += 1
        groups.add(row['split_group'])

    agreement = sum(a == b for a, b in annotation_pairs) / len(annotation_pairs)
    return {
        'status': 'PASS',
        'dataset_id': manifest['dataset_id'],
        'dataset_version': manifest['version'],
        'dataset_sha256': manifest['data_sha256'],
        'records': len(rows),
        'unique_records': len(ids),
        'duplicate_requests': 0,
        'split_groups': len(groups),
        'label_counts': dict(sorted(label_counts.items())),
        'source_kind_counts': dict(sorted(source_counts.items())),
        'reviewer_exact_agreement': agreement,
        'reviewer_cohen_kappa': cohen_kappa(annotation_pairs),
        'annotation_disagreements': disagreements,
        'ethics_review_status': manifest['ethics_review_status'],
        'access_level': manifest['access_level'],
    }


def split_dataset(data_path: Path, manifest_path: Path, output_dir: Path, seed: int = 20261113) -> dict:
    validation = validate_dataset(data_path, manifest_path)
    rows = read_jsonl(data_path)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row['split_group']].append(row)
    groups = sorted(grouped)
    if len(groups) < 3:
        raise DataValidationError('at least three distinct split_group values are required')
    random.Random(seed).shuffle(groups)
    n_test = max(1, round(len(groups) * 0.15))
    n_validation = max(1, round(len(groups) * 0.15))
    if n_test + n_validation >= len(groups):
        n_test = n_validation = 1
    group_sets = {
        'test': set(groups[:n_test]),
        'validation': set(groups[n_test:n_test + n_validation]),
        'train': set(groups[n_test + n_validation:]),
    }
    result = {}
    for split, selected in group_sets.items():
        split_rows = [row for group in groups if group in selected for row in grouped[group]]
        write_jsonl(output_dir / f'{split}.jsonl', split_rows)
        result[split] = {
            'records': len(split_rows), 'groups': len(selected),
            'label_counts': dict(sorted(Counter(row['gold_tool'] for row in split_rows).items())),
            'sha256': sha256_file(output_dir / f'{split}.jsonl'),
        }
    if set.union(*group_sets.values()) != set(groups):
        raise AssertionError('split assignment lost a group')
    if any(group_sets[a] & group_sets[b] for a in group_sets for b in group_sets if a < b):
        raise AssertionError('split group leakage detected')
    report = {'status': 'PASS', 'source_validation': validation, 'seed': seed,
              'group_field': 'split_group', 'splits': result, 'group_overlap': 0}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'split_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


DATABASE_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS datasets (
  dataset_id TEXT NOT NULL, version TEXT NOT NULL, sha256 TEXT NOT NULL,
  access_level TEXT NOT NULL, permission_reference TEXT NOT NULL,
  imported_at TEXT NOT NULL, PRIMARY KEY (dataset_id, version)
);
CREATE TABLE IF NOT EXISTS records (
  record_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, dataset_version TEXT NOT NULL,
  domain TEXT NOT NULL, source_kind TEXT NOT NULL, source_system TEXT NOT NULL,
  event_timestamp TEXT NOT NULL, site_group TEXT NOT NULL, product_group TEXT NOT NULL,
  machine_group TEXT NOT NULL, split_group TEXT NOT NULL, request_text TEXT NOT NULL,
  gold_tool TEXT NOT NULL, source_sha256 TEXT NOT NULL,
  FOREIGN KEY(dataset_id, dataset_version) REFERENCES datasets(dataset_id, version)
);
CREATE TABLE IF NOT EXISTS annotations (
  record_id TEXT NOT NULL, reviewer_id_hash TEXT NOT NULL, reviewer_role TEXT NOT NULL,
  label TEXT NOT NULL, reviewer_index INTEGER NOT NULL,
  PRIMARY KEY(record_id, reviewer_index), FOREIGN KEY(record_id) REFERENCES records(record_id)
);
"""


def ingest_sqlite(data_path: Path, manifest_path: Path, database_path: Path) -> dict:
    report = validate_dataset(data_path, manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    rows = read_jsonl(data_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path)) as connection:
        connection.executescript(DATABASE_SCHEMA)
        connection.execute(
            'INSERT OR REPLACE INTO datasets VALUES (?,?,?,?,?,?)',
            (manifest['dataset_id'], manifest['version'], manifest['data_sha256'],
             manifest['access_level'], manifest['permission_reference'],
             datetime.now().astimezone().isoformat()),
        )
        for row in rows:
            connection.execute(
                'INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (row['record_id'], manifest['dataset_id'], manifest['version'], row['domain'],
                 row['source_kind'], row['source_system'], row['event_timestamp'],
                 row['site_group'], row['product_group'], row['machine_group'],
                 row['split_group'], row['request_text'], row['gold_tool'], row['source_sha256']),
            )
            for reviewer_index in (1, 2):
                connection.execute(
                    'INSERT OR REPLACE INTO annotations VALUES (?,?,?,?,?)',
                    (row['record_id'], row[f'reviewer_{reviewer_index}_id_hash'],
                     row[f'reviewer_{reviewer_index}_role'], row[f'reviewer_{reviewer_index}_label'],
                     reviewer_index),
                )
        connection.commit()
    return {'status': 'PASS', 'database': str(database_path), 'records_imported': len(rows),
            'dataset_validation': report}


def _wilson(correct: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    p = correct / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def evaluate_predictions(gold_path: Path, predictions_path: Path) -> dict:
    gold_rows = read_jsonl(gold_path)
    predictions = read_jsonl(predictions_path)
    gold = {row['record_id']: row['gold_tool'] for row in gold_rows}
    predicted = {}
    for index, row in enumerate(predictions, 1):
        record_id = row.get('record_id')
        label = row.get('predicted_tool')
        if record_id in predicted:
            raise DataValidationError(f'predictions:{index}: duplicate record_id')
        if label not in (*TOOLS, 'ABSTAIN'):
            raise DataValidationError(f'predictions:{index}: invalid predicted_tool')
        predicted[record_id] = label
    if set(predicted) != set(gold):
        raise DataValidationError('prediction record IDs must exactly match the gold dataset')
    confusion = {label: {other: 0 for other in (*TOOLS, 'ABSTAIN')} for label in TOOLS}
    for record_id, truth in gold.items():
        confusion[truth][predicted[record_id]] += 1
    correct = sum(predicted[key] == value for key, value in gold.items())
    per_class = {}
    f1_values = []
    for label in TOOLS:
        tp = confusion[label][label]
        fn = sum(confusion[label].values()) - tp
        fp = sum(confusion[other][label] for other in TOOLS if other != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {'support': sum(confusion[label].values()), 'precision': precision,
                            'recall': recall, 'f1': f1}
        if per_class[label]['support']:
            f1_values.append(f1)
    return {
        'status': 'PASS', 'total': len(gold), 'correct': correct,
        'accuracy': correct / len(gold) if gold else 0.0,
        'accuracy_wilson_95': _wilson(correct, len(gold)),
        'macro_f1': sum(f1_values) / len(f1_values) if f1_values else 0.0,
        'abstentions': sum(label == 'ABSTAIN' for label in predicted.values()),
        'per_class': per_class, 'confusion_matrix': confusion,
    }


def readiness_report(data_path: Path | None = None, manifest_path: Path | None = None) -> dict:
    if data_path is None or manifest_path is None or not data_path.exists() or not manifest_path.exists():
        return {
            'status': 'REAL_DATA_REQUIRED', 'ready_for_real_data_paper_claim': False,
            'real_records': 0,
            'blocking_requirements': [
                'authorized real manufacturing records',
                'documented ethics or human-subjects determination',
                'de-identification and provenance manifest',
                'two independent domain-reviewer annotations',
                'three or more independent split groups',
                'frozen external or prospective test set',
            ],
        }
    validation = validate_dataset(data_path, manifest_path)
    requirements = {
        'at_least_500_records': validation['records'] >= 500,
        'at_least_5_split_groups': validation['split_groups'] >= 5,
        'all_7_domains_present': set(validation['label_counts']) == set(TOOLS),
        'at_least_50_per_domain': all(validation['label_counts'].get(label, 0) >= 50 for label in TOOLS),
        'reviewer_kappa_at_least_0_8': validation['reviewer_cohen_kappa'] >= 0.8,
        'ethics_determination_complete': validation['ethics_review_status'] != 'pending',
    }
    return {'status': 'READY_FOR_GROUPED_EVALUATION' if all(requirements.values()) else 'MORE_DATA_REQUIRED',
            'ready_for_real_data_paper_claim': all(requirements.values()),
            'validation': validation, 'pilot_thresholds': requirements}


def fingerprint_data(data_path: Path) -> dict:
    rows = read_jsonl(data_path)
    return {'file': str(data_path), 'record_count': len(rows), 'data_sha256': sha256_file(data_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description='Authorized real manufacturing data pipeline')
    subparsers = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'readiness'):
        sub = subparsers.add_parser(name)
        sub.add_argument('--data', type=Path)
        sub.add_argument('--manifest', type=Path)
    fingerprint = subparsers.add_parser('fingerprint')
    fingerprint.add_argument('--data', type=Path, required=True)
    convert = subparsers.add_parser('convert-csv')
    convert.add_argument('--csv', type=Path, required=True)
    convert.add_argument('--output', type=Path, required=True)
    split = subparsers.add_parser('split')
    split.add_argument('--data', type=Path, required=True)
    split.add_argument('--manifest', type=Path, required=True)
    split.add_argument('--output-dir', type=Path, required=True)
    split.add_argument('--seed', type=int, default=20261113)
    ingest = subparsers.add_parser('ingest')
    ingest.add_argument('--data', type=Path, required=True)
    ingest.add_argument('--manifest', type=Path, required=True)
    ingest.add_argument('--database', type=Path, required=True)
    evaluate = subparsers.add_parser('evaluate')
    evaluate.add_argument('--gold', type=Path, required=True)
    evaluate.add_argument('--predictions', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'validate':
        if not args.data or not args.manifest:
            parser.error('validate requires --data and --manifest')
        result = validate_dataset(args.data, args.manifest)
    elif args.command == 'readiness':
        result = readiness_report(args.data, args.manifest)
    elif args.command == 'fingerprint':
        result = fingerprint_data(args.data)
    elif args.command == 'convert-csv':
        result = convert_annotation_csv(args.csv, args.output)
    elif args.command == 'split':
        result = split_dataset(args.data, args.manifest, args.output_dir, args.seed)
    elif args.command == 'ingest':
        result = ingest_sqlite(args.data, args.manifest, args.database)
    else:
        result = evaluate_predictions(args.gold, args.predictions)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
