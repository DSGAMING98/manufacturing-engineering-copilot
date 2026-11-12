"""GPU benchmark for BASE, V1 or V2 model on exactly the same Phase 3 split.

Do not repeatedly tune against final test data. Use validation to iterate.
Separate from CPU-only hybrid calculator results.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from math import sqrt
from pathlib import Path
import re

from phase3.shared import DATA_DIR, RESULTS_DIR, atomic_json, read_jsonl, settings, write_jsonl
from phase3.validate_data import validate

DECISION = re.compile(r'^\s*Decision:\s*(PASS|FAIL|INSUFFICIENT_DATA)\b', re.I | re.M)
LABELS = ('PASS', 'FAIL', 'INSUFFICIENT_DATA')


def parse_decision(raw):
    matches = list(DECISION.finditer(raw or ''))
    return matches[0].group(1).upper() if len(matches) == 1 else None


def wilson_interval(successes: int, total: int, z: float = 1.96):
    if total <= 0:
        return [None, None]
    p = successes / total
    denom = 1 + z*z / total
    center = (p + z*z/(2*total)) / denom
    half = z * sqrt(p*(1-p)/total + z*z/(4*total*total)) / denom
    return [max(0, center-half), min(1, center+half)]


def scores(predictions):
    gold_count = Counter(row['gold'] for row in predictions)
    right_count = Counter(row['gold'] for row in predictions if row['correct'])
    n = len(predictions)
    if not n:
        raise ValueError('No predictions to score')
    correct_n = sum(row['correct'] for row in predictions)
    return {
        'total': n, 'correct': correct_n,
        'decision_accuracy': correct_n / n,
        'wilson_95_interval': wilson_interval(correct_n, n),
        'format_parse_rate': sum(row['prediction'] is not None for row in predictions) / n,
        'gold_labels': dict(gold_count),
        'per_class_accuracy': {label: right_count[label] / gold_count[label] if gold_count[label] else None
                               for label in LABELS},
        'false_acceptances': sum(row['gold'] == 'FAIL' and row['prediction'] == 'PASS' for row in predictions),
        'false_rejections': sum(row['gold'] == 'PASS' and row['prediction'] == 'FAIL' for row in predictions),
        'missing_evidence_predicted_as_pass': sum(row['gold'] == 'INSUFFICIENT_DATA' and row['prediction'] == 'PASS' for row in predictions),
        'missing_evidence_predicted_as_fail': sum(row['gold'] == 'INSUFFICIENT_DATA' and row['prediction'] == 'FAIL' for row in predictions),
    }


def main():
    p = argparse.ArgumentParser(description='Evaluate base/V1/V2 standalone SLM on Phase 3 synthetic QA examples')
    p.add_argument('--split', choices=['validation', 'test'], default='validation')
    p.add_argument('--adapter', type=Path, help='Leave blank for base foundation model')
    p.add_argument('--tag', required=True, help='Use base, v1, v2, etc. to distinguish results')
    p.add_argument('--limit', type=int, help='Quick diagnostic subset only; not official split metric')
    p.add_argument('--confirm-final-test', action='store_true',
                   help='Confirm held-out test evaluation after choosing model using validation only')
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', args.tag):
        p.error('--tag must be 1-40 letters/numbers/hyphens/underscores')
    if args.split == 'test' and not args.confirm_final_test:
        p.error('Test is locked to discourage repeated tuning. Add --confirm-final-test once at final evaluation.')
    if args.limit is not None and args.limit < 1:
        p.error('--limit must be positive')
    validate()
    cfg = settings()
    # Import Unsloth first for patching the user's working stack.
    from unsloth import FastLanguageModel
    import torch
    from src.common import generate, load_model
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    model, tokenizer = load_model(cfg['model_name'], cfg['max_seq_length'])
    if args.adapter:
        from peft import PeftModel
        resolved = args.adapter.resolve()
        if not (resolved / 'adapter_config.json').exists():
            raise FileNotFoundError(f'Missing adapter at {resolved}')
        model = PeftModel.from_pretrained(model, str(resolved), is_trainable=False)
    FastLanguageModel.for_inference(model)
    rows = read_jsonl(DATA_DIR / f'{args.split}.jsonl')
    if args.limit is not None:
        rows = rows[:args.limit]
    predicted = []
    for idx, record in enumerate(rows, 1):
        answer = generate(model, tokenizer, record['messages'][:-1], max_new_tokens=cfg['max_new_tokens'])
        guess = parse_decision(answer)
        gold = record['gold_decision']
        predicted.append({'id': record['id'], 'gold': gold, 'prediction': guess,
                          'correct': gold == guess, 'raw_response': answer})
        print(f'[{idx}/{len(rows)}] {record["id"]} expected={gold} predicted={guess}')
    metric = scores(predicted)
    report = {'system': 'standalone foundation or LoRA model, NOT hybrid calculator',
              'data': 'synthetic_rule_generated_phase3; no industrial validation',
              'data_sha256': hashlib.sha256((DATA_DIR / f'{args.split}.jsonl').read_bytes()).hexdigest(),
              'split': args.split, 'tag': args.tag, 'adapter': str(args.adapter) if args.adapter else None,
              'subset_limit': args.limit, 'scores': metric}
    name = f'{args.tag}_{args.split}' + ('_quick' if args.limit is not None else '')
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    atomic_json(RESULTS_DIR / f'{name}.json', report)
    write_jsonl(RESULTS_DIR / f'{name}_predictions.jsonl', predicted)
    print(json.dumps(report, indent=2))
    print('Saved:', RESULTS_DIR / f'{name}.json')


if __name__ == '__main__':
    main()
