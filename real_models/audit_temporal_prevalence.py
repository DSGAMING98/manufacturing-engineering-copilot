"""Audit SECOM failure prevalence in five chronological 235-row blocks.

Uses the original UCI labels and recorded timestamps, not numbers copied from
the paper. The first block contains 627 rows; the next four contain 235 each.
Run: python -m real_models.audit_temporal_prevalence
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from real_models.train_real_models import fetch
from real_models.evaluate_secom_chrono import read_labels_and_timestamps

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"real_models/evidence/secom_temporal_prevalence.json"

def main():
    folder, archive_hash=fetch("secom")
    labels,times=read_labels_and_timestamps(folder/"secom_labels.data")
    order=np.argsort(times,kind="stable")
    labels,times=labels[order],times[order]
    if len(labels)!=1567 or int(labels.sum())!=104:
        raise AssertionError("UCI source labels changed: expected 1567 rows and 104 failures.")
    boundaries=(0,627,862,1097,1332,1567)
    blocks=[]
    for i,(a,b) in enumerate(zip(boundaries[:-1],boundaries[1:]),start=1):
        count=b-a
        failures=int(labels[a:b].sum())
        blocks.append({
           "block":i,"start_row_inclusive":a+1,"end_row_inclusive":b,
           "samples":count,"failures":failures,"pass":count-failures,
           "failure_prevalence":failures/count,
           "earliest_timestamp":times[a].isoformat(sep=" "),
           "latest_timestamp":times[b-1].isoformat(sep=" "),
        })
    if sum(x["failures"] for x in blocks)!=104:
        raise AssertionError("Failure totals do not reconcile.")
    # Confirm the original 60/20/20 chronological boundaries separately.
    a,b=int(.6*len(labels)),int(.8*len(labels))
    original=[
        {"partition":"train","rows":a,"failures":int(labels[:a].sum())},
        {"partition":"validation","rows":b-a,"failures":int(labels[a:b].sum())},
        {"partition":"test","rows":len(labels)-b,"failures":int(labels[b:].sum())},
    ]
    result={
      "status":"VERIFIED_FROM_RAW_UCI_LABELS",
      "dataset":"UCI SECOM",
      "dataset_doi":"10.24432/C54305",
      "archive_sha256":archive_hash,
      "source_file":"secom_labels.data",
      "ordering":"stable ascending sort by parsed timestamp",
      "records":len(labels),"total_failures":int(labels.sum()),
      "global_prevalence":float(np.mean(labels)),
      "five_consecutive_blocks":blocks,
      "first_627_records_failure_share":int(labels[:627].sum())/int(labels.sum()),
      "chronological_60_20_20":original,
      "interpretation_limit":"Describes time-varying outcome prevalence, not proven concept drift, leakage mechanism, or causal explanation."
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
