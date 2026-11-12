from pathlib import Path
import unittest
from phase6.release_checks import is_disallowed
from phase6.stress import exercise
from phase6.plot_results import verified_model_rows, load_models, load_training_points

class Phase6Tests(unittest.TestCase):
    def test_private_paths_are_blocked(self):
        for path in ('.venv/Lib/torch.py','models/qa_qlora_v2/adapter/adapter.safetensors',
                     'phase4/docs/local/customer_manual.md','results/phase3/v2_validation.json',
                     'data/.env','secrets/token.json'):
            self.assertIsNotNone(is_disallowed(Path(path)),path)

    def test_open_source_paths_allowed(self):
        for path in ('src/train.py','phase3/data/train.jsonl','phase6/evidence/observed_comparison.json',
                     'phase4/docs/demo_traceability.md','README.md'):
            self.assertIsNone(is_disallowed(Path(path)))

    def test_stress_grid(self):
        output=exercise()
        self.assertEqual(output['failed'],0)
        self.assertGreaterEqual(output['cases'],400)

    def test_reported_results_match_counts(self):
        records,metadata=load_models(prefer_local=False)
        self.assertEqual([(x['tag'],x['correct']) for x in records],[('base',40),('v1',38),('v2',59)])
        self.assertEqual(metadata['source_kind'],'user_reported_console_comparison')

    def test_invalid_metric_rejected(self):
        self.assertRaises(ValueError,verified_model_rows,[{'tag':'bad','correct':101,'total':90,'false_acceptances':1,'false_rejections':1}])

    def test_v1_observed_loss_provenance(self):
        points=load_training_points('v1')
        self.assertEqual(len(points['train']),24)
        self.assertEqual(len(points['eval']),3)

if __name__=='__main__':
    unittest.main()
