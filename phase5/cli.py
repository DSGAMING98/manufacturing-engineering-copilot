"""Unified six-domain CLI plus optional guarded Qwen evidence selection.

Examples:
  python -m phase5.cli --once 'quality nominal=20.00 measured=20.03 tolerance=0.05 unit=mm'
  python -m phase5.cli --once 'knowledge What belongs in an inspection record?' --include-demo
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shlex

from phase5.copilot import DOMAINS, run

EXAMPLES = '''
    design hole_min=20.00 hole_max=20.04 shaft_min=19.97 shaft_max=20.01 unit=mm
    process diameter_mm=20 cutting_speed_m_per_min=100 feed_mm_per_rev=0.2 length_mm=80
    production planned_min=480 run_min=420 ideal_cycle_min_per_part=1 total_parts=350 good_parts=335
    quality nominal=20.00 measured=20.03 tolerance=0.05 unit=mm
    maintenance operating_hours=800 repair_hours=20 failures=4
    documentation record_id=IR-001 feature_id=SHAFT-1 drawing_id=DR-001 revision=A nominal=20 measured=20.03 tolerance=0.05 unit=mm equipment_id=GAUGE-7 timestamp=2026-11-13T09:30:00+05:30
    knowledge What identifiers belong in an inspection record for traceability?
'''


def parse_command(command: str) -> tuple[str, dict, str | None]:
    command = command.strip()
    if not command:
        raise ValueError('Blank command.')
    domain, _, body = command.partition(' ')
    domain = domain.lower()
    if domain in ('knowledge', 'docs', 'search'):
        return 'knowledge', {}, body.strip()
    if domain not in DOMAINS:
        raise ValueError('First word must be one of: ' + ', '.join(DOMAINS) + ', knowledge.')
    fields = {}
    try:
        tokens = shlex.split(body)
    except ValueError as exc:
        raise ValueError('Invalid quotation in command.') from exc
    if len(tokens) > 20:
        raise ValueError('Too many fields.')
    for token in tokens:
        if '=' not in token:
            raise ValueError('Expected key=value fields after the domain name.')
        k, v = token.split('=', 1)
        if not k or not v or k in fields:
            raise ValueError('Malformed or duplicate field: ' + k)
        fields[k] = v
    return domain, fields, None


def main():
    parser = argparse.ArgumentParser(description='Six-domain manufacturing research copilot (deterministic tools + Phase 4 document citations)')
    parser.add_argument('--once', help='Run exactly one domain command then exit.')
    parser.add_argument('--include-demo', action='store_true', help='Include FICTIONAL demo evidence (off by default).')
    parser.add_argument('--adapter', type=Path, help='Optional trained LoRA used ONLY to rank source excerpts for document search, GPU required.')
    args = parser.parse_args()
    selector = None
    if args.adapter:
        from phase4.rag_chat import EvidenceSelector
        selector = EvidenceSelector(args.adapter)
        print('Qwen adapter loaded for citation excerpt selection only. Numerical and operational outputs are tool-controlled.')
    print('Manufacturing Copilot Phase 5 | six domains | research prototype, not shop-floor authorization')
    print('Enter: <domain> key=value ...  | knowledge <question> | examples | exit')

    def ask(line):
        if line.strip().lower() in ('examples', 'help', '?'):
            print(EXAMPLES)
            return
        try:
            domain, fields, question = parse_command(line)
            response = run(domain, fields, question=question, include_demo=args.include_demo, selector=selector)
            print('\n' + response['report'] + '\n')
        except ValueError as exc:
            print('INSUFFICIENT_DATA: ' + str(exc) + '\nType examples for supported inputs.\n')

    if args.once:
        ask(args.once)
        return
    while True:
        try:
            line = input('\nYou > ')
        except (EOFError, KeyboardInterrupt):
            print('\nBye')
            return
        if line.strip().lower() in ('exit', 'quit', 'q'):
            return
        if line.strip():
            ask(line)


if __name__ == '__main__':
    main()
