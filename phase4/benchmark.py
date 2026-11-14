"""Offline retrieval checks against registered public dataset metadata."""
from __future__ import annotations

import json
from pathlib import Path

from phase4.rag_core import answer
from phase4.retrieval import load_corpus

SOURCE = 'UCI-MFG-DATASETS-001'
CHALLENGES = [
    'How many observed records are in Steel Plates Faults?',
    'Which surface fault classes are provided for steel plates?',
    'How many measured features are in the steel dataset?',
    'What is the DOI for the Steel Plates Faults dataset?',
    'What license applies to the UCI steel fault records?',
    'How many semiconductor manufacturing records are in SECOM?',
    'How many anonymized sensor and process columns are in SECOM?',
    'How many failure-labelled records are reported for SECOM?',
    'What is the DOI for the SECOM dataset?',
    'Can these datasets prove performance at a different plant?',
]
NEGATIVES = [
    'How do I program a six-axis robot arm using ROS 2?',
    'What is the tensile strength of aerospace titanium grade 5 in MPa?',
    'What are the mandatory clauses of ISO 9001:2015?',
]


def run():
    chunks = load_corpus()
    cases = []
    for question in CHALLENGES:
        result = answer(question, chunks=chunks, max_evidence=2)
        first = result.citations[0].split(':')[0] if result.citations else None
        cases.append({'question': question, 'expected': SOURCE, 'top_source': first, 'pass': first == SOURCE})
    for question in NEGATIVES:
        result = answer(question, chunks=chunks)
        cases.append({'question': question, 'expected': 'ABSTAIN',
                      'top_source': result.citations[0] if result.citations else None,
                      'pass': result.abstained})
    report = {
        'label': 'public_source_retrieval_regression',
        'pass_count': sum(case['pass'] for case in cases),
        'total': len(cases),
        'all_checks_passed': all(case['pass'] for case in cases),
        'cases': cases,
    }
    path = Path('results') / 'phase4_public_source_retrieval.json'
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for case in cases:
        print(f'{"PASS" if case["pass"] else "FAIL"} | expected={case["expected"]} got={case["top_source"]}: {case["question"]}')
    print(f'Public-source retrieval checks: {report["pass_count"]}/{report["total"]}')
    return report


if __name__ == '__main__':
    raise SystemExit(0 if run()['all_checks_passed'] else 1)
