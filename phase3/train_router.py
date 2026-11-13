"""Train a small LoRA adapter for seven-way engineering tool routing."""
from __future__ import annotations

import argparse
import inspect
import os

from phase3.generate_router_data import DATA_DIR
from phase3.shared import ROOT, atomic_json, read_jsonl, settings


def dataset_for(split, tokenizer):
    from datasets import Dataset
    packed = []
    for row in read_jsonl(DATA_DIR / f'{split}.jsonl'):
        prompt = tokenizer.apply_chat_template(
            row['messages'][:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        packed.append({'prompt': prompt, 'completion': row['messages'][-1]['content'] + tokenizer.eos_token})
    return Dataset.from_list(packed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-steps', type=int, default=90)
    parser.add_argument('--output-dir', default='models/router_qlora_v1')
    args = parser.parse_args()
    if not 1 <= args.max_steps <= 500:
        parser.error('--max-steps must be 1..500')
    output = (ROOT / args.output_dir).resolve()
    if not output.is_relative_to((ROOT / 'models').resolve()):
        parser.error('--output-dir must be inside models')
    if (output / 'adapter' / 'adapter_config.json').exists():
        raise FileExistsError(f'Refusing to overwrite {output / "adapter"}')
    os.environ.setdefault('WANDB_DISABLED', 'true')
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
    from unsloth import FastLanguageModel
    import torch
    from trl import SFTConfig, SFTTrainer
    from src.common import load_model

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is required')
    cfg = settings()
    model, tokenizer = load_model(cfg['model_name'], 256)
    model = FastLanguageModel.get_peft_model(
        model, r=8, lora_alpha=16,
        target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
        lora_dropout=0, bias='none', use_gradient_checkpointing='unsloth', random_state=3407,
    )
    values = dict(
        output_dir=str(output), per_device_train_batch_size=2, per_device_eval_batch_size=4,
        gradient_accumulation_steps=4, learning_rate=1e-4, max_steps=args.max_steps,
        logging_steps=10, eval_steps=30, save_steps=30, save_total_limit=3,
        warmup_ratio=.05, optim='adamw_8bit', lr_scheduler_type='cosine', weight_decay=.01,
        seed=3407, data_seed=3407, report_to='none', packing=False,
        completion_only_loss=True, bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(), gradient_checkpointing=True,
    )
    signature = inspect.signature(SFTConfig).parameters
    values['max_length' if 'max_length' in signature else 'max_seq_length'] = 256
    values['eval_strategy' if 'eval_strategy' in signature else 'evaluation_strategy'] = 'steps'
    config = SFTConfig(**{k: v for k, v in values.items() if k in signature})
    kwargs = dict(model=model, train_dataset=dataset_for('train', tokenizer),
                  eval_dataset=dataset_for('validation', tokenizer), args=config)
    trainer_signature = inspect.signature(SFTTrainer.__init__).parameters
    kwargs['processing_class' if 'processing_class' in trainer_signature else 'tokenizer'] = tokenizer
    trainer = SFTTrainer(**kwargs)
    result = trainer.train()
    adapter = output / 'adapter'
    model.save_pretrained(str(adapter))
    tokenizer.save_pretrained(str(adapter))
    atomic_json(output / 'training_summary.json', {
        'status': 'completed', 'task': 'seven_way_manufacturing_tool_routing',
        'foundation_model': cfg['model_name'], 'optimizer_steps': args.max_steps,
        'train_loss': result.training_loss, 'metrics': result.metrics,
        'limitations': 'Synthetic intent data only; model routes tools and never performs arithmetic or approval.',
    })
    print('Saved router adapter:', adapter)


if __name__ == '__main__':
    main()
