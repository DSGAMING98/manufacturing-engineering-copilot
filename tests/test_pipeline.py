import unittest
from pathlib import Path
from src.qa_tools import decision_for_dimension


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


if __name__ == '__main__':
    unittest.main()
