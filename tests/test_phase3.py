"""Offline Phase 3 regression tests. No network or CUDA needed."""
import json
from pathlib import Path
import tempfile
import unittest

from phase3.benchmark import benchmark, compute_metrics
from phase3.evaluate_model import parse_decision, scores
from phase3.generate_data import scenario, SYSTEM
from phase3.shared import DATA_DIR, read_jsonl
from phase3.validate_data import validate
from src.hybrid_qa import calculate
from src.tolerance_engine import inspect


class Phase3Test(unittest.TestCase):
    def test_data_complete_and_balanced(self):
        summary = validate()
        self.assertEqual(summary['train']['rows'], 480)
        self.assertEqual(summary['validation']['rows'], 90)
        self.assertEqual(summary['test']['rows'], 120)
        for name, n in (('train', 480), ('validation', 90), ('test', 120)):
            self.assertEqual(set(summary[name]['labels']), {'PASS', 'FAIL', 'INSUFFICIENT_DATA'})
            self.assertEqual(set(summary[name]['labels'].values()), {n//3})

    def test_source_provenance_never_real(self):
        for split in ('train', 'validation', 'test'):
            for row in read_jsonl(DATA_DIR / f'{split}.jsonl'):
                self.assertEqual(row['source_kind'], 'synthetic_rule_generated_phase3')
                self.assertFalse(row['reviewed_by_engineer'])
                self.assertIn('synthetic', row['provenance'].lower())

    def test_hybrid_consistency_on_all_synthetic_structured_inputs(self):
        for split in ('train', 'validation', 'test'):
            for row in read_jsonl(DATA_DIR / f'{split}.jsonl'):
                actual = calculate(row['structured_input'])
                self.assertEqual(actual['decision'], row['gold_decision'], row['id'])

    def test_manual_challenge_hybrid(self):
        rows = read_jsonl(DATA_DIR / 'manual_challenge.jsonl')
        self.assertEqual(len(rows), 36)
        output, metric = benchmark(rows)
        self.assertEqual(metric['count'], 36)
        self.assertEqual(metric['false_acceptances'], 0)
        self.assertEqual(metric['false_rejections'], 0)
        self.assertEqual(metric['misclassified_missing_evidence_as_pass_or_fail'], 0)
        self.assertTrue(all(item['correct'] for item in output), [x for x in output if not x['correct']])

    def test_regression_shaft(self):
        self.assertEqual(calculate('nominal=20.00 measured=20.03 tolerance=0.05 unit=mm')['decision'], 'PASS')
        self.assertEqual(calculate('nominal=20.00 measured=20.09 tolerance=0.05 unit=mm')['decision'], 'FAIL')

    def test_model_decision_extraction(self):
        self.assertEqual(parse_decision('Decision: pass\nRationale: ok'), 'PASS')
        self.assertEqual(parse_decision('Decision: INSUFFICIENT_DATA\nRationale: missing'), 'INSUFFICIENT_DATA')
        self.assertIsNone(parse_decision('Unsupported text'))

    def test_score_false_accept_and_reject(self):
        rows = [dict(gold='FAIL', prediction='PASS', correct=False),
                dict(gold='PASS', prediction='FAIL', correct=False),
                dict(gold='INSUFFICIENT_DATA', prediction=None, correct=False)]
        result = scores(rows)
        self.assertEqual(result['false_acceptances'], 1)
        self.assertEqual(result['false_rejections'], 1)
        self.assertEqual(result['format_parse_rate'], 2/3)

    def test_empty_benchmark_not_valid(self):
        with self.assertRaises(ValueError):
            compute_metrics([])

    def test_mutated_dataset_wrong_label_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            for name in ('train', 'validation', 'test'):
                (folder / f'{name}.jsonl').write_bytes((DATA_DIR / f'{name}.jsonl').read_bytes())
            records = read_jsonl(folder / 'validation.jsonl')
            records[0]['gold_decision'] = 'FAIL' if records[0]['gold_decision'] != 'FAIL' else 'PASS'
            with (folder / 'validation.jsonl').open('w', encoding='utf-8') as f:
                for row in records: f.write(json.dumps(row) + '\n')
            with self.assertRaises(ValueError):
                validate(folder, check_manifest=False)

    def test_nonfinite_arithmetic_refused(self):
        for bad in ('NaN', 'Infinity', 'missing'):
            result = inspect('20', bad, tolerance='0.05', unit='mm')
            self.assertEqual(result['decision'], 'INSUFFICIENT_DATA')

    def test_generator_uses_same_system_prompt(self):
        import random
        for label in ('PASS', 'FAIL', 'INSUFFICIENT_DATA'):
            row = scenario('train', 10, label, random.Random(44))
            self.assertEqual(row['messages'][0]['content'], SYSTEM)
            self.assertEqual(row['gold_decision'], label)

    def test_all_test_case_prompts_distinct_from_train(self):
        prompts_by_split = {s: {r['messages'][1]['content'] for r in read_jsonl(DATA_DIR / f'{s}.jsonl')}
                            for s in ('train', 'validation', 'test')}
        self.assertFalse(prompts_by_split['train'] & prompts_by_split['test'])
        self.assertFalse(prompts_by_split['validation'] & prompts_by_split['test'])


if __name__ == '__main__':
    unittest.main()
