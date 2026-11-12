"""Interactive research demo: no autonomous machine actions or product release."""
import argparse
from pathlib import Path
from src.common import config, generate, load_model, prepare_messages
from scripts.build_seed_data import SYSTEM


def main():
    p = argparse.ArgumentParser(description='Interactive QA assistant')
    p.add_argument('--adapter', type=Path, default=None)
    args = p.parse_args()

    from unsloth import FastLanguageModel
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA not available; run python -m src.preflight')
    cfg = config()
    model, tokenizer = load_model(cfg['model_name'], cfg['max_seq_length'])
    if args.adapter:
        from peft import PeftModel
        path = args.adapter.resolve()
        if not (path / 'adapter_config.json').exists():
            raise FileNotFoundError(f'Adapter not found at {path}')
        model = PeftModel.from_pretrained(model, str(path), is_trainable=False)
    FastLanguageModel.for_inference(model)
    print('Manufacturing QA research demo. No automated safety or product-release decisions.')
    print('Enter a single-dimensional measurement scenario, or type exit.')
    while True:
        try:
            question = input('\nYou > ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nBye')
            return
        if question.lower() in ('exit', 'quit', 'q'):
            return
        if question:
            print('\nModel >\n' + generate(
                model, tokenizer, prepare_messages(question, SYSTEM), cfg['max_new_tokens']))


if __name__ == '__main__':
    main()
