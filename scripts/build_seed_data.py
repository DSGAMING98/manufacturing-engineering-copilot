"""Creates **synthetic** data for a pipeline smoke test. NEVER claim as industrial measurements."""
import json
from decimal import Decimal
from pathlib import Path
from src.qa_tools import decision_for_dimension

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = (
    "You are a manufacturing dimensional-inspection assistant. Evaluate only the stated "
    "single dimension; do not authorize part or batch release. Never invent missing values. "
    "Format exactly four lines: Decision: PASS or FAIL or INSUFFICIENT_DATA; "
    "Rationale: concise check; Next step: appropriate human QA review; "
    "Evidence: scenario identifier. The decision is only for this dimension. /no_think"
)
PHRASINGS = [
    "Inspect the indicated feature. Part {part}, scenario {sid}. Nominal {n} mm, lower deviation {ld} mm, upper deviation {ud} mm, measured {m}. What is the dimensional inspection result?",
    "QA record {sid} for part {part}: target diameter {n} mm; tolerance deviations [{ld}, {ud}] mm; observed {m}. Report this single-dimensional check.",
    "Determine dimension conformity for item {part} ({sid}). Specified nominal={n} mm, lower dev={ld} mm, upper dev={ud} mm, measurement={m}. State the evidence and next step.",
]


def row(split: str, index: int, klass: str):
    # Distinct group IDs across splits prevent exact record leakage.
    prefix = {"train": "T", "validation": "V", "test": "X"}[split]
    part = f"P-{prefix}-{index:03d}"
    sid = f"SYN-QA-{prefix}-{index:03d}"
    nominal = Decimal(12) + Decimal(index % 70) * Decimal("0.37") + {"train": Decimal("0.00"), "validation": Decimal("0.11"), "test": Decimal("0.23")}[split]
    ld = -Decimal("0.05") - (index % 3) * Decimal("0.01")
    ud = Decimal("0.04") + (index % 4) * Decimal("0.01")
    if klass == "PASS":
        measured = nominal + Decimal("0.00") if index % 2 else nominal + ud
    elif klass == "FAIL":
        measured = nominal + ud + Decimal("0.02") if index % 2 else nominal + ld - Decimal("0.02")
    else:
        measured = None
    res = decision_for_dimension(str(nominal), str(ld), str(ud), None if measured is None else str(measured))
    assert res["decision"] == klass
    display_m = "not recorded" if measured is None else f"{measured} mm"
    phrasing = PHRASINGS[index % len(PHRASINGS)].format(part=part, sid=sid, n=nominal, ld=ld, ud=ud, m=display_m)
    if klass == "INSUFFICIENT_DATA":
        rationale = "The inspection measurement is absent, so tolerance compliance cannot be established."
        next_step = "Obtain and verify the missing measurement; have authorized QA personnel review."
    else:
        rationale = res["reason"]
        next_step = ("Record this dimensional result for authorized QA review; other acceptance criteria still apply."
                     if klass == "PASS" else "Flag this measurement for authorized QA review and verify the measurement record.")
    answer = f"Decision: {klass}\nRationale: {rationale}\nNext step: {next_step}\nEvidence: {sid} (synthetic)."
    return {"id": sid, "case_group": part, "domain": "quality_assurance", "source_kind": "synthetic_template",
            "reviewed_by_engineer": False, "gold_decision": klass,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": phrasing},
                         {"role": "assistant", "content": answer}]}


def main():
    data_dir = ROOT / "data"
    for split, per_class in (("train", 24), ("validation", 6), ("test", 8)):
        records = []
        for j in range(per_class):
            for k, klass in enumerate(("PASS", "FAIL", "INSUFFICIENT_DATA")):
                records.append(row(split, j * 3 + k + 1, klass))
        path = data_dir / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as out:
            for record in records:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"Wrote {path.relative_to(ROOT)}: {len(records)} SYNTHETIC rows (not real validation data)")


if __name__ == "__main__":
    main()
