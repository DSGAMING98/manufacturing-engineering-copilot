from pathlib import Path
import unittest
from phase6.release_checks import is_disallowed
from phase6.stress import exercise

class Phase6Tests(unittest.TestCase):
    def test_private_paths_are_blocked(self):
        for path in ('.venv/Lib/torch.py','models/qa_qlora_v2/adapter/adapter.safetensors',
                     'phase4/docs/local/customer_manual.md','results/phase3/v2_validation.json',
                     'data/.env','secrets/token.json'):
            self.assertIsNotNone(is_disallowed(Path(path)),path)

    def test_open_source_paths_allowed(self):
        for path in ('real_models/train_real_models.py','real_models/evidence/real_model_report.json',
                     'phase4/docs/public_dataset_sources.md','README.md'):
            self.assertIsNone(is_disallowed(Path(path)))

    def test_stress_grid(self):
        output=exercise()
        self.assertEqual(output['failed'],0)
        self.assertGreaterEqual(output['cases'],400)

if __name__=='__main__':
    unittest.main()
