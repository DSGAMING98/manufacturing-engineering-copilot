"""Shared paths, model loading and Qwen3 prompt formatting.

GPU dependencies are imported inside functions: import Unsloth before Transformers/TRL.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def config():
    return json.loads((ROOT / 'configs' / 'train.json').read_text(encoding='utf-8'))


def dataset_for_sft(split, tokenizer):
    """Use explicit non-thinking Qwen3 prompts so training matches evaluation.

    Prompt-completion data lets TRL mask the prompt tokens and learn only the
    target assistant response (completion_only_loss=True).
    """
    from datasets import Dataset
    from src.data_validation import load_jsonl
    rows = load_jsonl(ROOT / 'data' / f'{split}.jsonl')
    end = tokenizer.eos_token
    if not end:
        raise RuntimeError('Tokenizer has no EOS token; cannot format completions safely.')
    examples = []
    for row in rows:
        messages = row['messages']
        prompt = tokenizer.apply_chat_template(
            messages[:-1], tokenize=False, add_generation_prompt=True,
            enable_thinking=False,
        )
        completion = messages[-1]['content'] + end
        examples.append({'prompt': prompt, 'completion': completion})
    return Dataset.from_list(examples)


def load_model(model_name, max_seq_length):
    from unsloth import FastLanguageModel
    return FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
        full_finetuning=False,
        trust_remote_code=False,
    )


def prepare_messages(question, system_message):
    return [{'role': 'system', 'content': system_message},
            {'role': 'user', 'content': question}]


def generate(model, tokenizer, messages, max_new_tokens=144):
    import torch
    # Deterministic, non-thinking decoding is deliberate for benchmark repeatability.
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
        enable_thinking=False,
    )
    encoded = tokenizer([prompt], return_tensors='pt')
    inputs = {k: v.to('cuda') for k, v in encoded.items()}
    pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    with torch.inference_mode():
        tokens = model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False,
            pad_token_id=pad_id, eos_token_id=tokenizer.eos_token_id,
        )
    output = tokenizer.decode(tokens[0][inputs['input_ids'].shape[-1]:],
                              skip_special_tokens=True)
    return output.strip()
