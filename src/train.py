"""QLoRA adapter training for the synthetic dimensional QA starter dataset."""
import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os

from src.common import ROOT, config, dataset_for_sft, load_model
from src.data_validation import validate


def main():
    p = argparse.ArgumentParser(description='Train a small Qwen3 QA LoRA adapter')
    p.add_argument('--max-steps', type=int, default=None, help='Override configured step count, e.g. 2')
    args = p.parse_args()
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
    os.environ.setdefault('WANDB_DISABLED', 'true')

    # REQUIRED IMPORT ORDER: Unsloth first for its performance patches.
    from unsloth import FastLanguageModel
    import torch
    from trl import SFTConfig, SFTTrainer

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable. Run python -m src.preflight first.')
    counts = validate()
    settings = config()
    steps = args.max_steps if args.max_steps is not None else int(settings['max_steps'])
    if steps < 1:
        raise ValueError('--max-steps must be positive')
    output = ROOT / settings['output_dir']
    output.mkdir(parents=True, exist_ok=True)
    print('Validated dataset:', json.dumps(counts, indent=2))
    print('Loading 4-bit foundation model:', settings['model_name'])
    model, tokenizer = load_model(settings['model_name'], settings['max_seq_length'])
    model = FastLanguageModel.get_peft_model(
        model, r=settings['lora_rank'], lora_alpha=settings['lora_alpha'],
        target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj',
                        'gate_proj', 'up_proj', 'down_proj'],
        lora_dropout=0, bias='none',
        use_gradient_checkpointing='unsloth',
        random_state=settings['seed'], use_rslora=False,
    )

    sft_args = {
        'output_dir': str(output),
        'per_device_train_batch_size': settings['batch_size'],
        'per_device_eval_batch_size': 1,
        'gradient_accumulation_steps': settings['gradient_accumulation_steps'],
        'learning_rate': settings['learning_rate'],
        'max_steps': steps,
        'logging_steps': settings['logging_steps'],
        'eval_steps': settings['eval_steps'],
        'save_steps': settings['save_steps'],
        'save_total_limit': 2,
        'warmup_ratio': 0.03,
        'optim': 'adamw_8bit',
        'lr_scheduler_type': 'linear',
        'weight_decay': 0.01,
        'seed': settings['seed'],
        'data_seed': settings['seed'],
        'report_to': 'none',
        'dataloader_num_workers': 0,
        'dataset_num_proc': 1,
        'packing': False,
        'completion_only_loss': True,
        'bf16': torch.cuda.is_bf16_supported(),
        'fp16': not torch.cuda.is_bf16_supported(),
        'gradient_checkpointing': True,
        'save_strategy': 'steps',
    }
    signature = inspect.signature(SFTConfig).parameters
    if 'completion_only_loss' not in signature:
        raise RuntimeError('Installed TRL lacks completion_only_loss; upgrade Unsloth/TRL.')
    length_key = 'max_length' if 'max_length' in signature else 'max_seq_length'
    sft_args[length_key] = settings['max_seq_length']
    if 'eval_strategy' in signature:
        sft_args['eval_strategy'] = 'steps'
    elif 'evaluation_strategy' in signature:
        sft_args['evaluation_strategy'] = 'steps'
    else:
        raise RuntimeError('Cannot locate evaluation strategy argument in installed TRL.')
    sft_args = {key: value for key, value in sft_args.items() if key in signature}

    trainer_kwargs = {
        'model': model,
        'train_dataset': dataset_for_sft('train', tokenizer),
        'eval_dataset': dataset_for_sft('validation', tokenizer),
        'args': SFTConfig(**sft_args),
    }
    trainer_signature = inspect.signature(SFTTrainer.__init__).parameters
    if 'processing_class' in trainer_signature:
        trainer_kwargs['processing_class'] = tokenizer
    elif 'tokenizer' in trainer_signature:
        trainer_kwargs['tokenizer'] = tokenizer
    else:
        raise RuntimeError('Unknown TRL SFTTrainer tokenizer API; update dependencies.')

    trainer = SFTTrainer(**trainer_kwargs)
    trained = trainer.train()
    adapter_dir = output / 'adapter'
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    digests = {name: hashlib.sha256((ROOT / 'data' / f'{name}.jsonl').read_bytes()).hexdigest()
               for name in ('train', 'validation', 'test')}
    versions = {}
    for name in ('torch', 'unsloth', 'trl', 'transformers', 'datasets', 'peft'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = 'not-installed'
    summary = {
        'status': 'training_completed',
        'purpose': 'pipeline smoke test on SYNTHETIC data; not industrially validated',
        'foundation_model': settings['model_name'],
        'steps': steps,
        'train_loss': trained.training_loss,
        'train_runtime_seconds': trained.metrics.get('train_runtime'),
        'dataset_sha256': digests,
        'software_versions': versions,
        'configuration': settings,
        'adapter_directory': str(adapter_dir),
    }
    (output / 'train_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('\nSUCCESS: adapter saved to:', adapter_dir)
    print('Validate: python -m src.evaluate --split validation --adapter models/qa_qlora/adapter')


if __name__ == '__main__':
    main()
