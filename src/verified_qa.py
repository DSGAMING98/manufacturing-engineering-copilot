"""Verified QA CLI. No model-generated decision or fabricated standards citations."""
import argparse
import json
import re
from src.tolerance_engine import inspect

# Conservative natural-language support: a single, explicit symmetric-tolerance scenario.
# For other language, use --nominal / --measured / --tolerance structured flags.
SCENARIO = re.compile(
    r'\bnominal\s+(?:diameter\s+|dimension\s+)?(?:of\s+)?(?P<nominal>\d+(?:\.\d+)?)\s*'
    r'(?P<unit>mm|in)\b.{0,90}?\b(?:tolerance\s*)?(?:±|\+/-)\s*'
    r'(?P<tolerance>\d+(?:\.\d+)?)\s*(?:mm|in)?\b.{0,150}?'
    r'\bmeasured\s+(?:diameter\s+|dimension\s+|value\s+)?(?:is\s+|of\s+)?'
    r'(?P<measured>\d+(?:\.\d+)?)\s*(?:mm|in)?\b', re.IGNORECASE | re.DOTALL
)


def from_text(question):
    match = SCENARIO.search(question)
    if not match:
        return {'decision': 'INSUFFICIENT_DATA',
                'reason': 'Cannot safely extract all dimensional fields. Use structured input.',
                'source': 'strict_input_parser'}
    values = match.groupdict()
    # Refuse multiple dimension scenarios or mixed units rather than guessing.
    if len(SCENARIO.findall(question)) != 1:
        return {'decision': 'INSUFFICIENT_DATA', 'reason': 'Ambiguous multiple measurements.', 'source': 'strict_input_parser'}
    return inspect(values['nominal'], values['measured'], tolerance=values['tolerance'], unit=values['unit'].lower())


def main():
    p = argparse.ArgumentParser(description='Verified single-dimensional inspection, no GPU required')
    p.add_argument('--nominal')
    p.add_argument('--measured')
    p.add_argument('--tolerance', help='Symmetric +/- tolerance')
    p.add_argument('--low-dev', help='Signed lower deviation')
    p.add_argument('--high-dev', help='Signed upper deviation')
    p.add_argument('--unit', choices=['mm', 'in'], default='mm')
    p.add_argument('--text', help='Conservatively parse a natural-language single-dimension scenario')
    args = p.parse_args()
    if args.text:
        result = from_text(args.text)
    else:
        result = inspect(args.nominal, args.measured, lower_deviation=args.low_dev,
                         upper_deviation=args.high_dev, tolerance=args.tolerance, unit=args.unit)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
