import unittest
from pathlib import Path
from src.common import ROOT, config
from src.qa_tools import decision_for_dimension
from src.data_validation import validate
from src.evaluate import extract_decision


class PipelineTest(unittest.TestCase):
    def test_inclusive_bounds_and_failures(self):
        self.assertEqual(decision_for_dimension('10', '-0.1', '0.2', '10.2')['decision'], 'PASS')
        self.assertEqual(decision_for_dimension('10', '-0.1', '0.2', '9.9')['decision'], 'PASS')
        self.assertEqual(decision_for_dimension('10', '-0.1', '0.2', '10.201')['decision'], 'FAIL')
        self.assertEqual(decision_for_dimension('20', '-0.1', '0.2', '20.21')['decision'], 'FAIL')

    def test_missing_invalid_and_nonfinite(self):
        self.assertEqual(decision_for_dimension('10', '-0.1', '0.2', None)['decision'], 'INSUFFICIENT_DATA')
        self.assertEqual(decision_for_dimension('10', '0.2', '-0.1', '10.1')['decision'], 'INSUFFICIENT_DATA')
        self.assertEqual(decision_for_dimension('10', '-0.1', '0.2', 'NaN')['decision'], 'INSUFFICIENT_DATA')

    def test_strict_output_parser(self):
        self.assertEqual(extract_decision('Decision: FAIL\nRationale: out'), 'FAIL')
        self.assertEqual(extract_decision('Decision: INSUFFICIENT_DATA\nRationale: missing'), 'INSUFFICIENT_DATA')
        self.assertIsNone(extract_decision('I think it is probably fine'))

    def test_splits_and_provenance(self):
        report = validate()
        self.assertEqual(report['train']['total'], 72)
        self.assertEqual(report['validation']['total'], 18)
        self.assertEqual(report['test']['total'], 24)
        self.assertTrue((ROOT / 'data' / 'README.md').is_file())

    def test_configuration(self):
        c = config()
        self.assertTrue(c['model_name'].startswith('unsloth/'))
        self.assertEqual(c['lora_rank'], 8)
        self.assertEqual(c['max_seq_length'], 512)


if __name__ == '__main__':
    unittest.main()
