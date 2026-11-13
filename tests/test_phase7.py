import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from phase7.real_data_pipeline import (
    convert_annotation_csv, DataValidationError, TOOLS, evaluate_predictions, fingerprint_data, ingest_sqlite,
    readiness_report, sha256_file, split_dataset, validate_dataset, write_jsonl,
)


class RealDataPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / 'records.jsonl'
        self.manifest = self.root / 'manifest.json'
        self.rows = []
        for label_index, label in enumerate(TOOLS):
            for item_index in range(3):
                record_id = f'REAL-{label.upper()}-{item_index + 1}'
                digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
                self.rows.append({
                    'record_id': record_id,
                    'domain': label,
                    'source_kind': 'engineering_request',
                    'source_system': 'AUTHORIZED_TEST_FIXTURE',
                    'source_record_id_hash': digest('source-' + record_id),
                    'event_timestamp': f'2026-10-{label_index + 1:02d}T09:00:00+05:30',
                    'site_group': f'SITE_{label_index % 3}',
                    'product_group': f'PRODUCT_{label_index}',
                    'machine_group': f'MACHINE_{label_index % 4}',
                    'split_group': f'GROUP_{label_index}',
                    'request_text': f'Unit-test request {item_index + 1} for {label} workflow group {label_index}',
                    'gold_tool': label,
                    'required_fields': ['fixture_field'],
                    'source_sha256': digest('document-' + record_id),
                    'permission_reference': 'UNIT-TEST-PERMISSION',
                    'deidentified': True,
                    'reviewer_1_id_hash': digest('reviewer-one'),
                    'reviewer_1_role': 'manufacturing_engineer',
                    'reviewer_1_label': label,
                    'reviewer_2_id_hash': digest('reviewer-two'),
                    'reviewer_2_role': 'quality_engineer',
                    'reviewer_2_label': label,
                    'adjudicated_label': label,
                })
        self._write(self.rows)

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, rows):
        write_jsonl(self.data, rows)
        manifest = {
            'dataset_id': 'UNIT-TEST-REAL-DATA-SCHEMA',
            'version': '1.0.0',
            'dataset_kind': 'real_authorized',
            'owner_role': 'test_data_owner',
            'permission_reference': 'UNIT-TEST-PERMISSION',
            'allowed_purpose': 'software unit testing only',
            'access_level': 'restricted',
            'ethics_review_status': 'not_human_subjects',
            'deidentification_method': 'generated non-industrial unit-test fixture',
            'created_at': '2026-11-13T09:00:00+05:30',
            'data_sha256': sha256_file(self.data),
            'record_count': len(rows),
        }
        self.manifest.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    def test_authorized_dataset_validation_and_agreement(self):
        report = validate_dataset(self.data, self.manifest)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['records'], 21)
        self.assertEqual(report['reviewer_exact_agreement'], 1.0)
        self.assertEqual(report['reviewer_cohen_kappa'], 1.0)

    def test_fingerprint_supplies_manifest_values(self):
        report = fingerprint_data(self.data)
        self.assertEqual(report['record_count'], 21)
        self.assertEqual(report['data_sha256'], sha256_file(self.data))

    def test_annotation_csv_conversion(self):
        source = self.root / 'annotations.csv'
        output = self.root / 'converted.jsonl'
        fieldnames = list(self.rows[0]) + ['adjudication_role']
        with source.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            row = dict(self.rows[0])
            row['required_fields'] = ';'.join(row['required_fields'])
            row['deidentified'] = 'true'
            row['adjudication_role'] = ''
            writer.writerow(row)
        report = convert_annotation_csv(source, output)
        self.assertEqual(report['records_converted'], 1)
        converted = json.loads(output.read_text(encoding='utf-8'))
        self.assertTrue(converted['deidentified'])
        self.assertEqual(converted['required_fields'], ['fixture_field'])

    def test_generated_source_is_rejected(self):
        rows = [dict(row) for row in self.rows]
        rows[0]['source_kind'] = 'generated_record'
        self._write(rows)
        with self.assertRaises(DataValidationError):
            validate_dataset(self.data, self.manifest)

    def test_direct_identifier_field_is_rejected(self):
        rows = [dict(row) for row in self.rows]
        rows[0]['email'] = 'person@example.com'
        self._write(rows)
        with self.assertRaises(DataValidationError):
            validate_dataset(self.data, self.manifest)

    def test_group_split_has_no_overlap(self):
        output = self.root / 'splits'
        report = split_dataset(self.data, self.manifest, output, seed=5)
        self.assertEqual(report['group_overlap'], 0)
        split_groups = []
        for split in ('train', 'validation', 'test'):
            rows = [json.loads(line) for line in (output / f'{split}.jsonl').read_text().splitlines()]
            split_groups.append({row['split_group'] for row in rows})
        self.assertFalse(split_groups[0] & split_groups[1])
        self.assertFalse(split_groups[0] & split_groups[2])
        self.assertFalse(split_groups[1] & split_groups[2])

    def test_validated_records_ingest_into_sqlite(self):
        database = self.root / 'research.sqlite3'
        report = ingest_sqlite(self.data, self.manifest, database)
        self.assertEqual(report['records_imported'], 21)
        self.assertTrue(database.is_file())

    def test_prediction_evaluation(self):
        predictions = self.root / 'predictions.jsonl'
        write_jsonl(predictions, ({'record_id': row['record_id'], 'predicted_tool': row['gold_tool']}
                                  for row in self.rows))
        report = evaluate_predictions(self.data, predictions)
        self.assertEqual(report['accuracy'], 1.0)
        self.assertEqual(report['macro_f1'], 1.0)
        self.assertEqual(report['abstentions'], 0)

    def test_readiness_fails_closed_without_real_records(self):
        report = readiness_report()
        self.assertEqual(report['status'], 'REAL_DATA_REQUIRED')
        self.assertFalse(report['ready_for_real_data_paper_claim'])

    def test_small_dataset_is_not_paper_ready(self):
        report = readiness_report(self.data, self.manifest)
        self.assertEqual(report['status'], 'MORE_DATA_REQUIRED')
        self.assertFalse(report['ready_for_real_data_paper_claim'])


if __name__ == '__main__':
    unittest.main()
