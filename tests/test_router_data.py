import unittest

from phase3.validate_router_data import validate


class RouterDataValidationTests(unittest.TestCase):
    def test_all_router_records_pass_structural_validation(self):
        result = validate()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['records_valid'], 1484)
        self.assertEqual(result['record_validation_rate'], 1.0)
        self.assertEqual(result['cross_split_duplicate_prompts'], 0)


if __name__ == '__main__':
    unittest.main()
