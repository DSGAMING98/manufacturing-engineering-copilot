"""Small transparent Phase 5 REGRESSION benchmark, not industrial accuracy.

Tool correctness is checked against hand-authored expected deterministic outputs.
It does NOT assess the underlying SLM, shop-floor safety, regulatory compliance,
or real-world performance. Outputs summary only by default.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from phase5.copilot import run

CASES = [
    ('design', {'hole_min':'20.00','hole_max':'20.04','shaft_min':'19.97','shaft_max':'19.99'}, 'classification', 'CLEARANCE'),
    ('design', {'hole_min':'20.00','hole_max':'20.02','shaft_min':'20.03','shaft_max':'20.06'}, 'classification', 'INTERFERENCE'),
    ('design', {'hole_min':'20.00','hole_max':'20.04','shaft_min':'19.99','shaft_max':'20.03'}, 'classification', 'TRANSITION'),
    ('design', {'hole_min':'20.00','hole_max':'20.00','shaft_min':'20.00','shaft_max':'20.00'}, 'classification', 'TRANSITION'),
    ('design', {'hole_min':'22','hole_max':'21','shaft_min':'19','shaft_max':'20'}, None, 'INSUFFICIENT_DATA'),
    ('design', {'hole_min':'22','hole_max':'23','shaft_min':'19','shaft_max':'20','unit':'in'}, None, 'INSUFFICIENT_DATA'),
    ('process', {'diameter_mm':'20','cutting_speed_m_per_min':'100','feed_mm_per_rev':'0.2','length_mm':'80'}, 'cutting_time_min_ideal', '0.251327'),
    ('process', {'diameter_mm':'0','cutting_speed_m_per_min':'100','feed_mm_per_rev':'0.2','length_mm':'80'}, None, 'INSUFFICIENT_DATA'),
    ('process', {'diameter_mm':'20','cutting_speed_m_per_min':'100','feed_mm_per_rev':'0','length_mm':'80'}, None, 'INSUFFICIENT_DATA'),
    ('process', {'diameter_mm':'20','cutting_speed_m_per_min':'NaN','feed_mm_per_rev':'0.2','length_mm':'80'}, None, 'INSUFFICIENT_DATA'),
    ('production', {'planned_min':'480','run_min':'420','ideal_cycle_min_per_part':'1','total_parts':'350','good_parts':'335'}, 'oee_pct', '69.79'),
    ('production', {'planned_min':'480','run_min':'500','ideal_cycle_min_per_part':'1','total_parts':'350','good_parts':'335'}, None, 'INSUFFICIENT_DATA'),
    ('production', {'planned_min':'480','run_min':'420','ideal_cycle_min_per_part':'2','total_parts':'350','good_parts':'335'}, None, 'INSUFFICIENT_DATA'),
    ('production', {'planned_min':'480','run_min':'420','ideal_cycle_min_per_part':'1','total_parts':'350','good_parts':'400'}, None, 'INSUFFICIENT_DATA'),
    ('production', {'planned_min':'480','run_min':'420','ideal_cycle_min_per_part':'1','total_parts':'0','good_parts':'0'}, None, 'INSUFFICIENT_DATA'),
    ('maintenance', {'operating_hours':'800','repair_hours':'20','failures':'4'}, 'observed_mtbf_hours', '200.0000'),
    ('maintenance', {'operating_hours':'800','repair_hours':'20','failures':'0'}, None, 'INSUFFICIENT_DATA'),
    ('maintenance', {'operating_hours':'800','repair_hours':'0','failures':'0'}, 'observed_mtbf_hours', None),
    ('maintenance', {'operating_hours':'0','repair_hours':'0','failures':'0'}, None, 'INSUFFICIENT_DATA'),
    ('quality', {'nominal':'20.00','measured':'20.03','tolerance':'0.05','unit':'mm'}, 'decision', 'PASS'),
    ('quality', {'nominal':'20.00','measured':'20.09','tolerance':'0.05','unit':'mm'}, 'decision', 'FAIL'),
    ('quality', {'nominal':'20.00','measured':'19.95','tolerance':'0.05','unit':'mm'}, 'decision', 'PASS'),
    ('quality', {'nominal':'20.00','measured':'20.05','tolerance':'0.05','unit':'mm'}, 'decision', 'PASS'),
    ('quality', {'nominal':'20.00','measured':'20.03','unit':'mm'}, None, 'INSUFFICIENT_DATA'),
    ('quality', {'nominal':'20.00','measured':'20.03','tolerance':'0.05','unit':'cm'}, None, 'INSUFFICIENT_DATA'),
    ('quality', {'nominal':'20.00','measured':'20.03','lower_dev':'-0.02','upper_dev':'0.04','unit':'mm'}, 'decision', 'PASS'),
    ('documentation', {'record_id':'IR-1','feature_id':'F-1','drawing_id':'D-1','revision':'A','nominal':'20','measured':'20.03','tolerance':'0.05','unit':'mm','equipment_id':'GAUGE-7','timestamp':'2026-11-13T09:30:00+05:30'}, 'document_status', 'DRAFT'),
    ('documentation', {'record_id':'IR-1','feature_id':'F-1','drawing_id':'D-1','revision':'A','nominal':'20','measured':'20.03','tolerance':'0.05','unit':'mm','equipment_id':'GAUGE-7','timestamp':'2026-11-13T09:30:00'}, None, 'INSUFFICIENT_DATA'),
    ('documentation', {'record_id':'IR-1','feature_id':'F-1','drawing_id':'D-1','revision':'A','nominal':'20','measured':'20.03','tolerance':'0.05','unit':'mm','equipment_id':'GAUGE-7','timestamp':'2026-11-13T09:30:00+05:30','operator_id':'<script>'}, None, 'INSUFFICIENT_DATA'),
]


def execute():
    rows = []
    for i, (domain, fields, key, expected) in enumerate(CASES, 1):
        r = run(domain, fields)
        got = r['data'].get(key) if key else r['status']
        rows.append({'case':i, 'domain':domain, 'passed':got==expected, 'expected':expected, 'actual':got})
    # source-grounded refusal is tested separately from numeric tools
    blocked = run('knowledge', question='What does ISO 9001:2015 require for product release?')
    rows.append({'case':len(rows)+1, 'domain':'knowledge', 'passed':blocked['status']=='NO_VERIFIED_SOURCE',
                 'expected':'NO_VERIFIED_SOURCE', 'actual':blocked['status']})
    return {'benchmark_kind':'software_regression_cases_only',
            'does_not_establish':'industrial_accuracy_or_SLModel_quality',
            'total':len(rows), 'passed':sum(x['passed'] for x in rows), 'cases':rows}


def main():
    p = argparse.ArgumentParser(description='Phase 5 tool regression test')
    p.add_argument('--output', type=Path, help='Optional local JSON report file')
    args = p.parse_args()
    r = execute()
    print(f"Phase 5 hand-authored tool regressions: {r['passed']}/{r['total']} passed")
    print('Not industrial accuracy. Does not measure the Qwen model.')
    for case in r['cases']:
        if not case['passed']:
            print('FAIL:',case)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(r, indent=2), encoding='utf-8')
        print('Saved:', args.output)
    if r['passed'] != r['total']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
