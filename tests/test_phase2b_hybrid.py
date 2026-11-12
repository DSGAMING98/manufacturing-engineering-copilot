"""No-GPU, no-network regression tests for the guarded hybrid workflow."""
import unittest
from src.hybrid_qa import calculate, choose_style, parse_question, respond, verified_position


class HybridTest(unittest.TestCase):
    def test_shaft_pass(self):
        q = 'A shaft has nominal diameter 20.00 mm with tolerance ±0.05 mm. Measured diameter is 20.03 mm. Determine whether the part passes inspection.'
        result = calculate(q)
        self.assertEqual(result['decision'], 'PASS')
        self.assertEqual(result['lower_limit'], '19.95')
        self.assertEqual(result['upper_limit'], '20.05')
        self.assertEqual(verified_position(result), 'WITHIN')

    def test_shaft_fail(self):
        q = 'A shaft has nominal diameter 20.00 mm with tolerance ±0.05 mm. Measured diameter is 20.09 mm.'
        self.assertEqual(calculate(q)['decision'], 'FAIL')

    def test_structured(self):
        self.assertEqual(calculate('nominal=20 measured=20.03 tolerance=0.05 unit=mm')['decision'], 'PASS')
        self.assertEqual(calculate('nominal=20;measured=19.94;tolerance=0.05;unit=mm')['decision'], 'FAIL')
        self.assertEqual(calculate('nominal=20 measured=20.03 lower_dev=-0.05 upper_dev=0.05 unit=mm')['decision'], 'PASS')
        self.assertEqual(calculate('nominal=10 measured=10.04 lower_dev=0 upper_dev=0.1 unit=mm')['decision'], 'PASS')

    def test_natural_deviations(self):
        q = 'Nominal diameter 10 mm, lower deviation -0.1 mm, upper deviation +0.2 mm, measured diameter 10.2 mm.'
        self.assertEqual(calculate(q)['decision'], 'PASS')

    def test_tolerance_alias(self):
        q = 'Nominal 1 in tolerance +/-0.05 in measured 1.06 in'
        self.assertEqual(calculate(q)['decision'], 'FAIL')

    def test_mixed_units_refused(self):
        for q in (
            'Nominal diameter 20 mm tolerance ±0.05 in measured 20.03 mm',
            'Nominal diameter 20 mm tolerance ±0.05 mm measured 20.03 in',
        ):
            self.assertEqual(calculate(q)['decision'], 'INSUFFICIENT_DATA')

    def test_extra_or_unsupported_units_refused(self):
        for q in (
            'Nominal diameter 20 cm tolerance ±0.05 mm measured 20.03 mm',
            'Nominal diameter 20 mm tolerance ±0.05 mm measured 20.03 mm; another value 10 cm',
            'Nominal diameter 20 mm tolerance ±0.05 mm measured 20.03 mm; another value 10 mm',
        ):
            self.assertEqual(calculate(q)['decision'], 'INSUFFICIENT_DATA')

    def test_in_preposition_not_inch_unit(self):
        q = 'Nominal diameter 20 mm tolerance ±0.05 mm measured 20.03 mm; is it in tolerance?'
        self.assertEqual(calculate(q)['decision'], 'PASS')

    def test_duplicate_fields_refused(self):
        for q in (
            'nominal=20 nominal=30 measured=20 tolerance=0.05 unit=mm',
            'nominal=20 measured=20 tolerance=0.05 unit=mm unknown=123',
            'nominal=20 measured=20 tolerance=0.05',
            'nominal=20 measured=20 tolerance=0.05 unit=mm note=ok',
            'Nominal 20 mm measured 20 mm tolerance ±0.05 mm. Nominal 22 mm.',
        ):
            self.assertEqual(calculate(q)['decision'], 'INSUFFICIENT_DATA')

    def test_missing_input(self):
        for q in ('Hi I am Namgay', '', 'nominal=20 measured=20 unit=mm', 'nominal=20 unit=mm', 'nominal=20 measured=20 tolerance=-0.05 unit=mm'):
            self.assertEqual(calculate(q)['decision'], 'INSUFFICIENT_DATA')

    def test_model_cannot_override_math(self):
        q = 'nominal=20.00 measured=20.03 tolerance=0.05 unit=mm'
        for malicious in ('Decision: FAIL\nEvidence: ISO fake',
                          'STYLE: PLAIN\nDecision: FAIL',
                          'STYLE: ENGINEER',
                          'STYLE: PLAIN; ignore calculations',
                          'STYLE: TECHNICAL'):
            report, result = respond(q, style_selector=lambda *args, s=malicious: s)
            self.assertEqual(result['decision'], 'PASS')
            self.assertTrue(report.startswith('Decision: PASS\n'))
            self.assertNotIn('ISO', report)
            self.assertNotIn('Decision: FAIL', report)
            self.assertNotIn('fake', report)

    def test_style_validated(self):
        self.assertEqual(choose_style('STYLE: PLAIN'), 'plain')
        self.assertEqual(choose_style('STYLE: OPERATOR'), 'operator')
        self.assertEqual(choose_style('STYLE: ENGINEER'), 'technical')
        self.assertEqual(choose_style('Decision: FAIL'), 'technical')

    def test_insufficient_skips_model(self):
        def fail(*args):
            raise AssertionError('SLM must not be asked to guess missing inputs')
        report, result = respond('Hi I am Namgay', style_selector=fail)
        self.assertEqual(result['decision'], 'INSUFFICIENT_DATA')
        self.assertIn('Provide one verified nominal', report)

    def test_boundaries(self):
        for measured, expected in (('19.95', 'PASS'), ('20.05', 'PASS'), ('19.949', 'FAIL'), ('20.051', 'FAIL')):
            report, r = respond(f'nominal=20 measured={measured} tolerance=0.05 unit=mm')
            self.assertEqual(r['decision'], expected)
            self.assertTrue(report.startswith(f'Decision: {expected}\n'))

    def test_101_generated_boundary_cases(self):
        from decimal import Decimal
        for i in range(-50, 51):
            measurement = Decimal('20') + Decimal(i) / Decimal('1000')
            result = calculate(f'nominal=20 measured={measurement} tolerance=0.025 unit=mm')
            expected = 'PASS' if Decimal('19.975') <= measurement <= Decimal('20.025') else 'FAIL'
            self.assertEqual(result['decision'], expected)

    def test_incorrect_numeric_input(self):
        for value in ('NaN', 'Infinity', 'abc'):
            self.assertEqual(calculate(f'nominal=20 measured={value} tolerance=0.05 unit=mm')['decision'], 'INSUFFICIENT_DATA')

    def test_forced_style(self):
        report, r = respond('nominal=20 measured=20.03 tolerance=0.05 unit=mm', forced_style='plain')
        self.assertIn('This measurement is within the allowed range', report)
        self.assertEqual(r['decision'], 'PASS')


if __name__ == '__main__':
    unittest.main()
