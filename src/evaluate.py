"""Save auditable baseline and fine-tuned QA classification measurements."""
import argparse
from collections import Counter
import json
import re
from pathlib import Path

from src.common import ROOT, config, generate, load_model
from src.data_validation import load_jsonl, validate

LABEL_RE = re.compile(r'(?im)^\s*Decision:\s*(PASS|FAIL|INSUFFICIENT_DATA)\b')


def extract_decision(text):
    m = LABEL_RE.search(text)
    return m.group(1) if m else None


def evaluate():
    p = argparse.ArgumentParser(description='Evaluate a base or adapter QA model')
    p.add_argument('--split', choices=('validation', 'test'), default='validation')
    p.add_argument('--adapter', type=Path, default=None)
    p.add_argument('--limit', type=int, default=None, help='Quick test only; not an official metric')
    args = p.parse_args()
    validate()
    settings = config()

    # Must import Unsloth first before PEFT/Transformers/TRL.
    from unsloth import FastLanguageModel
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; run preflight before loading model.')
    model, tokenizer = load_model(settings['model_name'], settings['max_seq_length'])
    if args.adapter:
        from peft import PeftModel
        adapter_dir = args.adapter.resolve()
        if not (adapter_dir / 'adapter_config.json').is_file():
            raise FileNotFoundError('Adapter missing: ' + str(adapter_dir))
        model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=False)
    FastLanguageModel.for_inference(model)

    records = load_jsonl(ROOT / 'data' / f'{args.split}.jsonl')
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError('--limit must be positive')
        records = records[:args.limit]
    output = []
    for ix, record in enumerate(records, 1):
        prediction_text = generate(model, tokenizer, record['messages'][:-1],
                                   settings['max_new_tokens'])
        label = extract_decision(prediction_text)
        result = {
            'id': record['id'], 'gold': record['gold_decision'],
            'prediction': label, 'correct': label == record['gold_decision'],
            'raw_response': prediction_text,
            'source_kind': record['source_kind'],
        }
        output.append(result)
        print(f"[{ix}/{len(records)}] {record['id']}: expected={record['gold_decision']} predicted={label}")
    total = len(output)
    gold_hist = Counter(r['gold'] for r in output)
    correct_hist = Counter(r['gold'] for r in output if r['correct'])
    metric = {
        'dataset': 'synthetic_template_only',
        'warning': 'This evaluation DOES NOT establish industrial manufacturing performance.',
        'split': args.split, 'count': total,
        'subset_limit': args.limit,
        'base_model': settings['model_name'],
        'adapter': str(args.adapter) if args.adapter else None,
        'decision_accuracy': sum(r['correct'] for r in output) / total,
        'format_parse_rate': sum(r['prediction'] is not None for r in output) / total,
        'gold_label_counts': dict(gold_hist),
        'per_class_accuracy': {label: correct_hist[label]/n for label, n in gold_hist.items()},
    }
    output_dir = ROOT / 'results'
    output_dir.mkdir(exist_ok=True)
    run_name = ('finetuned' if args.adapter else 'baseline') + '_' + args.split
    if args.limit is not None:
        run_name += '_quick'
    (output_dir / f'{run_name}_metrics.json').write_text(json.dumps(metric, indent=2), encoding='utf-8')
    with (output_dir / f'{run_name}_predictions.jsonl').open('w', encoding='utf-8') as f:
        for item in output:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print('\n' + json.dumps(metric, indent=2))
    print('Wrote results/', run_name, '_metrics.json', sep='')


if __name__ == '__main__':
    evaluate()
