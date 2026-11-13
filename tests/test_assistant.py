import unittest
import json
from pathlib import Path

from phase5.assistant import assist, extract_fields, route_domain
from phase5.web_app import process_payload


class AssistantTests(unittest.TestCase):
    def test_routes_all_engineering_domains(self):
        cases = {
            'design': 'calculate hole shaft clearance fit',
            'process': 'estimate turning spindle rpm and feed rate',
            'production': 'calculate OEE from planned time and good parts',
            'quality': 'inspect a measured dimension against tolerance',
            'maintenance': 'calculate MTBF and MTTR from failures',
            'documentation': 'create a draft inspection record with drawing id',
            'knowledge': 'what does the traceability procedure document say?',
        }
        for expected, prompt in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(route_domain(prompt)[0], expected)

    def test_quality_request_executes_verified_tool(self):
        result = assist('Check quality: nominal=20, measured=20.03, tolerance=0.05, unit=mm')
        self.assertEqual(result['status'], 'CALCULATED')
        self.assertEqual(result['data']['decision'], 'PASS')
        self.assertEqual(result['assistant']['routed_domain'], 'quality')
        self.assertFalse(result['assistant']['model_arithmetic'])

    def test_design_natural_labels_execute(self):
        result = assist(
            'Find hole shaft fit with hole min 20.00 mm, hole max 20.04 mm, '
            'shaft min 19.97 mm and shaft max 20.01 mm.'
        )
        self.assertEqual(result['status'], 'CALCULATED')
        self.assertEqual(result['data']['classification'], 'TRANSITION')

    def test_missing_values_get_specific_follow_up(self):
        result = assist('Please calculate OEE for planned time=480 and run time=420.')
        self.assertEqual(result['status'], 'NEEDS_INPUT')
        self.assertEqual(result['domain'], 'production')
        self.assertIn('good_parts', result['assistant']['missing_fields'])
        self.assertNotIn('planned_min', result['assistant']['missing_fields'])

    def test_ambiguous_prompt_is_not_guessed(self):
        result = assist('Can you help me?')
        self.assertEqual(result['status'], 'NEEDS_INPUT')
        self.assertEqual(result['domain'], 'assistant')

    def test_process_extraction_does_not_guess_unlabelled_numbers(self):
        fields = extract_fields('process', 'turning 20 100 0.2 80')
        self.assertEqual(fields, {})

    def test_api_accepts_prompt_only(self):
        result = process_payload({'prompt': 'quality nominal=20 measured=20.03 tolerance=0.05 unit=mm'})
        self.assertEqual(result['data']['decision'], 'PASS')
        refused = process_payload({'prompt': 'quality check', 'domain': 'quality'})
        self.assertEqual(refused['status'], 'INSUFFICIENT_DATA')

    def test_conservative_hosted_router_on_manual_challenge(self):
        path = Path(__file__).parents[1] / 'phase3' / 'router_data' / 'manual_challenge.jsonl'
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
        for row in rows:
            with self.subTest(case=row['id']):
                self.assertEqual(route_domain(row['messages'][1]['content'])[0], row['gold_tool'])


if __name__ == '__main__':
    unittest.main()
