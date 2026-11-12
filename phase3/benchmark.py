"""CPU-only Phase 2 hybrid evaluation on independently authored regression prompts.

The challenges are hand-authored by the package author, *not engineer-reviewed*.
The hybrid calculator's synthetic reference data should not be presented as an
independent real industrial benchmark.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json

from phase3.shared import DATA_DIR, RESULTS_DIR, atomic_json, read_jsonl, write_jsonl
from src.hybrid_qa import respond


def compute_metrics(predictions):
    n = len(predictions)
    if not n:
        raise ValueError('Empty benchmark')
    labels = ('PASS', 'FAIL', 'INSUFFICIENT_DATA')
    per = {}
    for gold in labels:
        rows = [r for r in predictions if r['gold'] == gold]
        per[gold] = {'total': len(rows), 'correct': sum(r['correct'] for r in rows),
                     'accuracy': (sum(r['correct'] for r in rows) / len(rows)) if rows else None}
    confusion = {label: {guess: 0 for guess in labels} for label in labels}
    for item in predictions:
        confusion[item['gold']][item['prediction']] += 1
    return {
        'count': n, 'correct': sum(r['correct'] for r in predictions),
        'accuracy': sum(r['correct'] for r in predictions) / n,
        'abstention_rate': sum(r['prediction'] == 'INSUFFICIENT_DATA' for r in predictions)/n,
        'false_acceptances': sum(r['gold'] == 'FAIL' and r['prediction'] == 'PASS' for r in predictions),
        'false_rejections': sum(r['gold'] == 'PASS' and r['prediction'] == 'FAIL' for r in predictions),
        'misclassified_missing_evidence_as_pass_or_fail': sum(
            r['gold'] == 'INSUFFICIENT_DATA' and r['prediction'] != 'INSUFFICIENT_DATA' for r in predictions),
        'per_class': per, 'confusion_matrix': confusion,
    }


def benchmark(rows):
    out = []
    for row in rows:
        report, result = respond(row['prompt'])  # CPU only: no model stylistic inference.
        pred = result['decision']
        gold = row['gold_decision']
        if gold not in ('PASS', 'FAIL', 'INSUFFICIENT_DATA'):
            raise ValueError(f'Unexpected gold label in {row["id"]}')
        out.append({'id': row['id'], 'gold': gold, 'prediction': pred, 'correct': pred == gold,
                    'reason': result.get('reason'), 'description': row['description']})
    return out, compute_metrics(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', help='Optional alternate result prefix')
    args = parser.parse_args()
    path = DATA_DIR / 'manual_challenge.jsonl'
    rows = read_jsonl(path)
    outputs, metrics = benchmark(rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    name = args.output or 'hybrid_manual_challenge'
    result_file = RESULTS_DIR / f'{name}.json'
    prediction_file = RESULTS_DIR / f'{name}_predictions.jsonl'
    summary = {
        'benchmark': 'hand-authored regression challenge, NOT engineer-validated real industrial data',
        'system': 'Phase 2 deterministic hybrid calculator, no GPU model inference',
        'dataset_path': str(path), 'metrics': metrics,
        'limitations': ['Single scalar dimension only', 'Uncertainty / GD&T / calibration not assessed',
                        'Hand-authored cases are not independent industrial measurements'],
    }
    atomic_json(result_file, summary)
    write_jsonl(prediction_file, outputs)
    print(json.dumps(summary, indent=2))
    for item in outputs:
        if not item['correct']:
            print('MISMATCH:', item)
    print('Saved:', result_file)


if __name__ == '__main__':
    main()
