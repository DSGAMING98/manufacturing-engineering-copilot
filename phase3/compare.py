"""Report side-by-side scores only if files use identical split and dataset hash."""
from __future__ import annotations
import argparse
import json

from phase3.shared import RESULTS_DIR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['validation', 'test'], default='validation')
    parser.add_argument('--tags', nargs='+', default=['base', 'v1', 'v2'])
    args = parser.parse_args()
    seen = []
    for tag in args.tags:
        path = RESULTS_DIR / f'{tag}_{args.split}.json'
        if not path.exists():
            print(f'SKIP (not yet evaluated): {path}')
            continue
        obj = json.loads(path.read_text(encoding='utf-8'))
        if obj['split'] != args.split or obj['subset_limit'] is not None:
            raise ValueError(f'{path} cannot be compared as a full {args.split} split')
        seen.append(obj)
    if not seen:
        raise FileNotFoundError('No completed model evaluation files found. Run phase3.evaluate_model first.')
    fingerprints = {obj['data_sha256'] for obj in seen}
    if len(fingerprints) != 1:
        raise ValueError('Dataset SHA256 mismatch. Refusing misleading comparison.')
    print('Phase 3 synthetic model-only comparison on:', args.split)
    print('Same data SHA256:', next(iter(fingerprints)))
    print(f'{"MODEL":<15} {"CORRECT":>8} {"TOTAL":>8} {"ACCURACY":>12} {"FALSE-PASS":>12} {"FALSE-FAIL":>12}')
    for r in seen:
        s = r['scores']
        print(f'{r["tag"]:<15} {s["correct"]:>8} {s["total"]:>8} '
              f'{s["decision_accuracy"]*100:>11.2f}% {s["false_acceptances"]:>12} {s["false_rejections"]:>12}')
    print('Warning: all examples synthetic. This is NOT industrial accuracy.')


if __name__ == '__main__':
    main()
