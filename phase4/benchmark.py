"""Offline controlled Phase 4 retrieval challenge, not industrial validation.

Runs hand-written questions against fictitious example docs only. No GPU.
"""
from __future__ import annotations

import json
from pathlib import Path

from phase4.rag_core import answer
from phase4.retrieval import load_corpus

# These prompts are different from document text, but written for our demo corpus.
CHALLENGES = [
    ('How do I calculate the upper and lower limits using nominal and tolerance?', 'DEMO-DIM-001'),
    ('What if I cannot confirm the inspection unit and drawing revision?', 'DEMO-DIM-001'),
    ('What should be recorded after measuring a dimensional feature?', 'DEMO-TRACE-001'),
    ('Does one passing measurement prove overall product conformity?', 'DEMO-DIM-001'),
    ('What should happen when a dimensional discrepancy is flagged?', 'DEMO-NCR-001'),
    ('What do I do with the original measurement record after a discrepancy?', 'DEMO-NCR-001'),
    ('Who can authorize disposition or rework when a part is nonconforming?', 'DEMO-NCR-001'),
    ('How do I double-check the gauge condition and measurement method?', 'DEMO-NCR-001'),
    ('What identifiers belong in an inspection record for traceability?', 'DEMO-TRACE-001'),
    ('What if the applicable procedure revision cannot be confirmed?', 'DEMO-TRACE-001'),
    ('Should we fabricate an external standard citation for evidence?', 'DEMO-TRACE-001'),
    ('Does a retrieved excerpt authorize releasing parts for use?', 'DEMO-TRACE-001'),
]
NEGATIVES = [
    'How do I program a six-axis robot arm using ROS 2?',
    'What is the tensile strength of aerospace titanium grade 5 in MPa?',
    'What are the mandatory clauses of ISO 9001:2015?',
    'Give me latest diesel prices in Mumbai.',
]


def run():
    chunks = load_corpus(include_demo=True)
    result = []
    for q, expected in CHALLENGES:
        r = answer(q, chunks=chunks, max_evidence=2)
        first = r.citations[0].split(':')[0] if r.citations else None
        result.append({'question': q, 'expected': expected, 'top_source': first, 'pass': first == expected})
    for q in NEGATIVES:
        r = answer(q, chunks=chunks)
        result.append({'question': q, 'expected': 'ABSTAIN', 'top_source': (r.citations[0] if r.citations else None),
                       'pass': r.abstained})
    # Default approved-only path should abstain when only demo docs are bundled.
    no_demo = answer('How do I handle a dimensional discrepancy?')
    report = {
        'label': 'toy_local_retrieval_challenge_not_industrial_or_independent_evaluation',
        'pass_count': sum(case['pass'] for case in result), 'total': len(result),
        'approved_only_abstains': no_demo.abstained,
        'all_checks_passed': all(case['pass'] for case in result) and no_demo.abstained,
        'cases': result,
    }
    path = Path('results') / 'phase4_demo_retrieval_benchmark.json'
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for case in result:
        print(f'{"PASS" if case["pass"] else "FAIL"} | expected={case["expected"]} got={case["top_source"]}: {case["question"]}')
    print(f'\nDemo corpus retrieval checks: {report["pass_count"]}/{report["total"]}')
    print('Default mode does not expose demo docs:', no_demo.abstained)
    print('No GPU/model used. This result is not manufacturing accuracy.')
    print('Saved:', path)
    return report


if __name__ == '__main__':
    raise SystemExit(0 if run()['all_checks_passed'] else 1)
