"""Evaluate the local tool-routing adapter on a fixed synthetic split."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from phase3.generate_router_data import DATA_DIR, LABELS, SYSTEM
from phase3.shared import ROOT, atomic_json, read_jsonl, settings

TOOL = re.compile(r'^\s*Tool:\s*(design|process|production|quality|maintenance|documentation|knowledge)\s*$', re.I)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--split', choices=('validation', 'test', 'manual_challenge', 'holdout2'), default='validation')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--confirm-final-test', action='store_true')
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--descriptive-system', action='store_true',
                        help='Use the current explicit tool definitions for every evaluation request')
    args = parser.parse_args()
    if args.split == 'test' and not args.confirm_final_test:
        parser.error('Add --confirm-final-test after selecting the adapter on validation only.')
    from unsloth import FastLanguageModel
    import torch
    from src.common import generate_batch, load_model
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is required')
    cfg = settings()
    model, tokenizer = load_model(cfg['model_name'], 256)
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(args.adapter.resolve()), is_trainable=False)
    FastLanguageModel.for_inference(model)
    rows = read_jsonl(DATA_DIR / f'{args.split}.jsonl')
    predictions = []
    for start in range(0, len(rows), args.batch_size):
        batch = rows[start:start + args.batch_size]
        message_batches = []
        for row in batch:
            messages = row['messages'][:-1]
            if args.descriptive_system:
                messages = [{'role': 'system', 'content': SYSTEM}, messages[1]]
            message_batches.append(messages)
        answers = generate_batch(model, tokenizer, message_batches, max_new_tokens=12)
        for row, answer in zip(batch, answers):
            match = TOOL.fullmatch(answer.strip())
            predicted = match.group(1).lower() if match else None
            predictions.append({'id': row['id'], 'gold': row['gold_tool'], 'prediction': predicted,
                                'correct': predicted == row['gold_tool'], 'raw': answer.strip()})
        print(f'{min(start + len(batch), len(rows))}/{len(rows)}', flush=True)
    total = len(predictions)
    correct = sum(item['correct'] for item in predictions)
    by_gold = Counter(item['gold'] for item in predictions)
    by_correct = Counter(item['gold'] for item in predictions if item['correct'])
    data_description = (
        'manually authored post-training challenge; not independently reviewed'
        if args.split in ('manual_challenge', 'holdout2') else 'balanced synthetic held-out templates'
    )
    report = {
        'task': 'seven_way_manufacturing_tool_routing', 'data': data_description,
        'split': args.split, 'tag': args.tag, 'adapter': str(args.adapter) if args.adapter else None,
        'descriptive_system_prompt': args.descriptive_system,
        'total': total, 'correct': correct, 'accuracy': correct / total,
        'format_parse_rate': sum(item['prediction'] is not None for item in predictions) / total,
        'per_class_recall': {label: by_correct[label] / by_gold[label] for label in LABELS},
        'limitations': 'This measures synthetic intent routing, not industrial engineering correctness.',
    }
    output = ROOT / 'results' / 'phase3'
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / f'{args.tag}_{args.split}.json', report)
    (output / f'{args.tag}_{args.split}_predictions.jsonl').write_text(
        ''.join(json.dumps(row, sort_keys=True) + '\n' for row in predictions), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
