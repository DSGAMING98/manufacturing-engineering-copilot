"""Qwen3 + deterministic QA, without giving the model authority over decisions.

Usage:
  python -m src.hybrid_chat --adapter models/qa_qlora/adapter
  python -m src.hybrid_chat --no-model --once "nominal=20 measured=20.03 tolerance=0.05 unit=mm"
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.hybrid_qa import model_style_prompt, respond, SUPPORTED_STYLES


class StyleSelector:
    """Load the existing model/adapter ONCE; infer ONLY a response style code."""
    def __init__(self, adapter: Path):
        # Unsloth must be imported before transformers/PEFT/torch where possible.
        from unsloth import FastLanguageModel
        import torch
        from src.common import config, load_model
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable. Use --no-model to test the verified calculation path.')
        cfg = config()
        model, tokenizer = load_model(cfg['model_name'], cfg['max_seq_length'])
        from peft import PeftModel
        adapter = adapter.resolve()
        if not (adapter / 'adapter_config.json').exists():
            raise FileNotFoundError(f'Missing trained adapter: {adapter}')
        model = PeftModel.from_pretrained(model, str(adapter), is_trainable=False)
        FastLanguageModel.for_inference(model)
        self.model = model
        self.tokenizer = tokenizer

    def __call__(self, question: str, result: dict) -> str:
        from src.common import generate, prepare_messages
        system = ('You only select report presentation style. Reply EXACTLY '
                  'STYLE: TECHNICAL or STYLE: PLAIN or STYLE: OPERATOR. /no_think')
        messages = prepare_messages(model_style_prompt(question, result), system)
        return generate(self.model, self.tokenizer, messages, max_new_tokens=24)


def main():
    p = argparse.ArgumentParser(description='Hybrid QA demo: Python verifies measurement, Qwen only selects presentation style')
    p.add_argument('--adapter', type=Path, default=Path('models/qa_qlora/adapter'))
    p.add_argument('--no-model', action='store_true', help='CPU-only deterministic report, no model loaded')
    p.add_argument('--style', choices=SUPPORTED_STYLES, help='Override model-chosen presentation style')
    p.add_argument('--once', help='Run a single question and exit')
    args = p.parse_args()

    selector = None
    if args.no_model:
        print('Verified calculator mode: no SLM loaded.')
    elif args.style:
        print('Verified calculator mode: explicit style override, no model inference required.')
    else:
        selector = StyleSelector(args.adapter)
        print('Hybrid mode: Qwen adapter loaded for style selection only.')

    print('Engineering decisions are calculated by Python Decimal, NOT by the model.')
    print('Research prototype. Not for product release, certification, or autonomous QA.')
    print('Enter a dimension scenario, key=value fields, or exit.')

    def ask(question: str):
        report, _ = respond(question, style_selector=selector, forced_style=args.style)
        print('\nVerified QA >\n' + report)

    if args.once is not None:
        ask(args.once)
        return
    while True:
        try:
            question = input('\nYou > ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nBye')
            return
        if question.lower() in ('exit', 'quit', 'q'):
            return
        if question:
            ask(question)


if __name__ == '__main__':
    main()
