import json
from pathlib import Path
import unittest

from phase5.web_app import process_payload
from phase5.real_model import load_model, predict_steel_fault


class RealModelTests(unittest.TestCase):
    def test_artifact_metadata_and_dimensions(self):
        model = load_model()
        self.assertEqual(model['dataset_doi'], '10.24432/C5J88N')
        self.assertEqual(len(model['features']), 27)
        self.assertEqual(len(model['classes']), 7)
        self.assertGreaterEqual(len(model['trees']), 100)

    def test_known_observed_row_predicts(self):
        row = [42, 50, 270900, 270944, 267, 17, 44, 24220, 76, 108, 1687, 1, 0, 80,
               .0498, .2415, .1818, .0047, .4706, 1, 1, 2.4265, .9031, 1.6435, .8182, -.2913, .5822]
        result = predict_steel_fault(row)
        self.assertIn(result['classification'], load_model()['classes'])
        self.assertAlmostEqual(sum(result['probabilities'].values()), 1.0, places=5)

    def test_api_rejects_wrong_dimension(self):
        output = process_payload({'domain': 'real_quality', 'fields': {'measurements': '1,2'}})
        self.assertEqual(output['status'], 'INSUFFICIENT_DATA')

    def test_committed_report_is_real_only(self):
        path = Path(__file__).parents[1] / 'real_models' / 'evidence' / 'real_model_report.json'
        report = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(report['data_policy'], 'observed_public_records_only')
        self.assertEqual(report['models']['steel_fault_classifier']['observed_records'], 1941)
        self.assertEqual(report['models']['secom_failure_risk']['observed_records'], 1567)


if __name__ == '__main__':
    unittest.main()
