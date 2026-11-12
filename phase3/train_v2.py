"""QLoRA V2: train from the original foundation model, not the Phase 1 adapter.

This keeps V1 untouched for an apples-to-apples dataset comparison. GPU run
must occur locally in the user's PyCharm environment; no GPU claim is made here.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os

from phase3.shared import DATA_DIR, ROOT, atomic_json, read_jsonl, settings
from phase3.validate_data import validate


def dataset_for_sft(split, tokenizer):
    from datasets import Dataset
    rows = read_jsonl(DATA_DIR / f'{split}.jsonl')
    if not tokenizer.eos_token:
        raise RuntimeError('Tokenizer has no EOS token')
    packed = []
    for row in rows:
        messages = row['messages']
        prompt = tokenizer.apply_chat_template(messages[:-1], tokenize=False,
                                                add_generation_prompt=True, enable_thinking=False)
        packed.append({'prompt': prompt, 'completion': messages[-1]['content'] + tokenizer.eos_token})
    return Dataset.from_list(packed)


def main():
    p = argparse.ArgumentParser(description='Phase 3 V2 model training; writes separate adapter')
    p.add_argument('--smoke', action='store_true', help='Only two steps, separate smoke output folder')
    p.add_argument('--max-steps', type=int, default=None, help='Optional custom optimizer steps')
    args = p.parse_args()
    if args.smoke and args.max_steps is not None:
        p.error('Use either --smoke or --max-steps, not both')
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
    os.environ.setdefault('WANDB_DISABLED', 'true')
    # REQUIRED IMPORT ORDER: Unsloth patches before Torch / Transformers / PEFT.
    from unsloth import FastLanguageModel
    import torch
    from trl import SFTConfig, SFTTrainer
    from src.common import load_model

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA not detected. Use your working GPU .venv Python interpreter.')
    validate()
    cfg = settings()
    steps = 2 if args.smoke else (args.max_steps if args.max_steps is not None else int(cfg['max_steps']))
    if steps < 1:
        raise ValueError('Training steps must be positive')
    output = ROOT / ('models/qa_qlora_v2_smoke' if args.smoke else cfg['output_dir'])
    if (output / 'adapter' / 'adapter_config.json').exists():
        raise FileExistsError(f'Existing trained adapter found at {output / "adapter"}. Refusing to overwrite.')
    output.mkdir(parents=True, exist_ok=True)
    print('PHASE 3: TRAINING SYNTHETIC QA DATA. Not industrial validation.')
    print('Split sizes: 480 train / 90 validation / 120 held-out synthetic test.')
    print('Model:', cfg['model_name'], '| steps:', steps, '| output:', output)
    model, tokenizer = load_model(cfg['model_name'], cfg['max_seq_length'])
    model = FastLanguageModel.get_peft_model(
        model, r=cfg['lora_rank'], lora_alpha=cfg['lora_alpha'],
        target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
        lora_dropout=0, bias='none', use_gradient_checkpointing='unsloth',
        random_state=cfg['seed'], use_rslora=False,
    )
    values = dict(
        output_dir=str(output), per_device_train_batch_size=cfg['batch_size'],
        per_device_eval_batch_size=1, gradient_accumulation_steps=cfg['gradient_accumulation_steps'],
        learning_rate=cfg['learning_rate'], max_steps=steps,
        logging_steps=cfg['logging_steps'], eval_steps=min(cfg['eval_steps'], steps),
        save_steps=min(cfg['save_steps'], steps), save_total_limit=2,
        warmup_ratio=0.03, optim='adamw_8bit', lr_scheduler_type='linear',
        weight_decay=0.01, seed=cfg['seed'], data_seed=cfg['seed'], report_to='none',
        dataloader_num_workers=0, dataset_num_proc=1, packing=False,
        completion_only_loss=True, bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(), gradient_checkpointing=True,
        save_strategy='steps',
    )
    signature = inspect.signature(SFTConfig).parameters
    if 'completion_only_loss' not in signature:
        raise RuntimeError('Installed TRL lacks completion_only_loss. Check your Unsloth environment.')
    values['max_length' if 'max_length' in signature else 'max_seq_length'] = cfg['max_seq_length']
    if 'eval_strategy' in signature:
        values['eval_strategy'] = 'steps'
    elif 'evaluation_strategy' in signature:
        values['evaluation_strategy'] = 'steps'
    else:
        raise RuntimeError('Installed TRL lacks evaluation strategy support')
    sft = SFTConfig(**{key: value for key, value in values.items() if key in signature})
    trainer_kwargs = dict(model=model, train_dataset=dataset_for_sft('train', tokenizer),
                          eval_dataset=dataset_for_sft('validation', tokenizer), args=sft)
    ts = inspect.signature(SFTTrainer.__init__).parameters
    if 'processing_class' in ts:
        trainer_kwargs['processing_class'] = tokenizer
    elif 'tokenizer' in ts:
        trainer_kwargs['tokenizer'] = tokenizer
    else:
        raise RuntimeError('Unrecognized SFTTrainer tokenizer argument')
    trainer = SFTTrainer(**trainer_kwargs)
    train_output = trainer.train()
    adapter = output / 'adapter'
    model.save_pretrained(str(adapter))
    tokenizer.save_pretrained(str(adapter))
    versions = {}
    for name in ('torch', 'unsloth', 'trl', 'transformers', 'datasets', 'peft'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = 'not-installed'
    summary = {
        'status': 'completed', 'training_dataset': 'synthetic_rule_generated_phase3',
        'research_limitation': 'No independent industrial data; trained model cannot authorize product release',
        'foundation_model': cfg['model_name'], 'trained_from_base_not_v1': True,
        'optimizer_steps': steps, 'is_smoke': args.smoke,
        'train_loss': train_output.training_loss, 'metrics': train_output.metrics,
        'data_sha256': {part: hashlib.sha256((DATA_DIR / f'{part}.jsonl').read_bytes()).hexdigest()
                        for part in ('train', 'validation', 'test')},
        'versions': versions, 'config': cfg, 'adapter_dir': str(adapter),
    }
    atomic_json(output / 'phase3_training_summary.json', summary)
    print('\nSUCCESS V2 adapter:', adapter)
    if not args.smoke:
        print('Next: python -m phase3.evaluate_model --split validation --adapter models/qa_qlora_v2/adapter --tag v2')


if __name__ == '__main__':
    main()
