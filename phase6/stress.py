"""Deterministic numerical regression grid. Does NOT measure model accuracy."""
from __future__ import annotations
import argparse
from decimal import Decimal
import json
from pathlib import Path
from src.tolerance_engine import inspect
from phase5.copilot import run


def exercise():
    checked = 0
    errors=[]
    for nominal in ('0', '20.00', '100.00', '1000.0', '250.125'):
        n=Decimal(nominal)
        for tolerance in ('0', '0.01', '0.05', '0.50', '2.00'):
            t=Decimal(tolerance)
            for displacement in ('-3', '-2.5', '-2', '-1.5', '-1.01', '-1', '-0.999', '-0.99', '-0.5', '-0.1', '0', '0.1', '0.5', '0.99', '0.999', '1', '1.01', '1.5', '2', '2.5', '3'):
                # When tolerance is zero, extra fixed 0.01mm exercise excludes 0 only.
                delta=Decimal(displacement)*t if t else Decimal(displacement)*Decimal('0.01')
                measured=n+delta
                expected = 'PASS' if (n-t <= measured <= n+t) else 'FAIL'
                raw=inspect(nominal, str(measured), tolerance=tolerance,unit='mm')
                via=run('quality',{'nominal':nominal,'measured':str(measured),'tolerance':tolerance,'unit':'mm'})
                checked += 1
                if raw['decision']!=expected or via['status']!='CALCULATED' or via['data'].get('decision')!=expected:
                    errors.append({'nominal':nominal,'tol':tolerance,'measured':str(measured),'expected':expected,
                                   'raw':raw.get('decision'),'via':via['data'].get('decision')})
    # Four edge cases: invalid numeric/missing tolerance/unmatched units/not-a-number
    for scenario in (
        {'nominal':'20','measured':'NaN','tolerance':'0.05','unit':'mm'},
        {'nominal':'20','measured':'20.02','unit':'mm'},
        {'nominal':'20','measured':'20.02','tolerance':'-0.05','unit':'mm'},
        {'nominal':'20','measured':'20.02','tolerance':'0.05','unit':'inch'},
    ):
        checked += 1
        via = run('quality',scenario)
        if via['status'] != 'INSUFFICIENT_DATA':
            errors.append({'scenario':scenario,'status':via['status']})
    return {'kind':'deterministic_regression_only','cases':checked,'passed':checked-len(errors),
            'failed':len(errors),'errors':errors[:15],
            'research_limit':'No production safety, metrology traceability or industrial testing established'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    r=exercise()
    print(f"Phase 6 deterministic stress tests: {r['passed']}/{r['cases']} passed")
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    if r['failed']:
        print(json.dumps(r['errors'],indent=2))
        raise SystemExit(1)

if __name__=='__main__':
    main()
