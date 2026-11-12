"""Compare previously saved validation runs; never manufacture missing metrics."""
import json
from pathlib import Path
from src.common import ROOT


def compare():
    base_path = ROOT / 'results' / 'baseline_validation_metrics.json'
    ft_path = ROOT / 'results' / 'finetuned_validation_metrics.json'
    for path in (base_path, ft_path):
        if not path.is_file():
            raise FileNotFoundError(f'Missing {path.name}. Run both complete validation evaluations first.')
    b = json.loads(base_path.read_text(encoding='utf-8'))
    f = json.loads(ft_path.read_text(encoding='utf-8'))
    if b.get('subset_limit') is not None or f.get('subset_limit') is not None:
        raise ValueError('Partial --limit evaluations cannot be presented as full results.')
    if b['count'] != f['count'] or b['split'] != f['split']:
        raise ValueError('Runs were not evaluated on the same complete split.')
    summary = {
        'validation_examples': b['count'],
        'dataset_provenance': 'synthetic_only',
        'baseline_accuracy': b['decision_accuracy'],
        'finetuned_accuracy': f['decision_accuracy'],
        'difference_percentage_points': 100 * (f['decision_accuracy'] - b['decision_accuracy']),
        'baseline_format_parse_rate': b['format_parse_rate'],
        'finetuned_format_parse_rate': f['format_parse_rate'],
        'warning': 'Synthetic-template results are not evidence of real manufacturing generalization.',
    }
    path = ROOT / 'results' / 'validation_comparison.json'
    path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    print('Saved to:', path)


if __name__ == '__main__':
    compare()
