"""CPU-only reproducibility gate for shipping source and making paper figures."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import sys
import unittest
from phase3.validate_data import validate
from phase4.benchmark import run as rag_benchmark
from phase5.benchmark import execute as tools_benchmark
from phase6.stress import exercise as stress_benchmark
from phase6.release_checks import audit

ROOT=Path(__file__).resolve().parents[1]


def run_suite():
    suite=unittest.TestLoader().discover(str(ROOT/'tests'),pattern='test_*.py')
    outcome=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
    return {'total':outcome.testsRun,'failures':len(outcome.failures),'errors':len(outcome.errors),'skipped':len(outcome.skipped),
            'passed':outcome.wasSuccessful()}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=ROOT/'results/phase6/reproducibility.json')
    args=p.parse_args()
    data=validate()
    tests=run_suite()
    rag=rag_benchmark()
    tools=tools_benchmark()
    stress=stress_benchmark()
    release=audit()
    all_good=tests['passed'] and not release and rag['all_checks_passed'] and tools['passed']==tools['total'] and not stress['failed']
    report={
      'utc_time':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
      'system':platform.platform(),'scope':'CPU-only synthetic software regression and provenance checks, not GPU validation or industrial deployment',
      'dataset_validation':data, 'unittest':tests,
      'rag_demo_regressions':{'passed':rag['pass_count'],'total':rag['total']},
      'six_domain_regressions':{'passed':tools['passed'],'total':tools['total']},
      'quality_arithmetic_regressions':{'passed':stress['passed'],'total':stress['cases']},
      'path_audit_issues':[{'path':x,'reason':y} for x,y in release],
      'passed':bool(all_good),
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('\nPHASE 6 REPRODUCIBILITY:', 'PASS' if all_good else 'FAIL')
    print('Saved:',args.output)
    if not all_good:
        raise SystemExit(1)

if __name__=='__main__':
    main()
