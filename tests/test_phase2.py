import unittest
from decimal import Decimal
from src.tolerance_engine import inspect
from src.verified_qa import from_text


class TestPhase2(unittest.TestCase):
    def test_original_bug(self):
        r = inspect('20.00', '20.03', tolerance='0.05')
        self.assertEqual(r['decision'], 'PASS')
        self.assertEqual(r['upper_limit'], '20.05')

    def test_over_upper(self):
        self.assertEqual(inspect('20', '20.09', tolerance='0.05')['decision'], 'FAIL')

    def test_boundaries(self):
        for value in ('19.95', '20.05'):
            self.assertEqual(inspect('20', value, tolerance='0.05')['decision'], 'PASS')

    def test_unilateral(self):
        self.assertEqual(inspect('10', '10.04', lower_deviation='0', upper_deviation='0.1')['decision'], 'PASS')
        self.assertEqual(inspect('10', '9.99', lower_deviation='0', upper_deviation='0.1')['decision'], 'FAIL')

    def test_missing_invalid(self):
        for measured in (None, '', 'NaN', 'Infinity', 'abc'):
            self.assertEqual(inspect('20', measured, tolerance='0.05')['decision'], 'INSUFFICIENT_DATA')

    def test_invalid_range(self):
        self.assertEqual(inspect('20', '20', lower_deviation='0.2', upper_deviation='-0.2')['decision'], 'INSUFFICIENT_DATA')

    def test_negative_tolerance(self):
        self.assertEqual(inspect('20', '20', tolerance='-0.05')['decision'], 'INSUFFICIENT_DATA')

    def test_text(self):
        s = 'A shaft has nominal diameter 20.00 mm with tolerance ±0.05 mm. Measured diameter is 20.03 mm.'
        self.assertEqual(from_text(s)['decision'], 'PASS')

    def test_no_guessing(self):
        self.assertEqual(from_text('hi, i am namgay')['decision'], 'INSUFFICIENT_DATA')

    def test_50_cases(self):
        # 101 independent boundary and near-boundary cases.
        for i in range(-50, 51):
            m = Decimal('20') + Decimal(i) / Decimal('1000')
            r = inspect('20', str(m), tolerance='0.025')
            expected = 'PASS' if Decimal('19.975') <= m <= Decimal('20.025') else 'FAIL'
            self.assertEqual(r['decision'], expected)


if __name__ == '__main__':
    unittest.main()
