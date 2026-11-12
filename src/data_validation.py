"""Dataset schema and train/validation/test leakage checks (stdlib only)."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    if not records:
        raise ValueError(f"Empty dataset {path}")
    return records


def validate(data_dir=ROOT / "data"):
    all_ids, all_groups, all_prompts, counts = set(), set(), set(), {}
    for split in ("train", "validation", "test"):
        path = Path(data_dir) / f"{split}.jsonl"
        data = load_jsonl(path)
        labels = collections.Counter()
        for ix, row in enumerate(data, 1):
            for key in ("id", "case_group", "source_kind", "messages", "gold_decision"):
                if key not in row:
                    raise ValueError(f"{split} row {ix}: missing {key}")
            if row["gold_decision"] not in ("PASS", "FAIL", "INSUFFICIENT_DATA"):
                raise ValueError(f"{split} row {ix}: unexpected gold label")
            msgs = row["messages"]
            if [m.get("role") for m in msgs] != ["system", "user", "assistant"]:
                raise ValueError(f"{split} row {ix}: messages must be system/user/assistant")
            if not all(isinstance(m.get("content"), str) and m["content"].strip() for m in msgs):
                raise ValueError(f"{split} row {ix}: missing message content")
            if f"Decision: {row['gold_decision']}" not in msgs[-1]["content"]:
                raise ValueError(f"{split} row {ix}: gold label and response disagree")
            if row["id"] in all_ids or row["case_group"] in all_groups:
                raise ValueError(f"Cross-record case ID/group overlap at {split} row {ix}")
            all_ids.add(row["id"]); all_groups.add(row["case_group"])
            digest = hashlib.sha256(msgs[1]["content"].strip().lower().encode()).hexdigest()
            if digest in all_prompts:
                raise ValueError(f"Exact duplicated question at {split} row {ix}")
            all_prompts.add(digest)
            labels[row["gold_decision"]] += 1
        counts[split] = {"total": len(data), "labels": dict(labels), "sources": dict(collections.Counter(x["source_kind"] for x in data))}
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = ap.parse_args()
    print(json.dumps(validate(args.data_dir), indent=2))
    print("PASS: no exact case-group or question overlap among splits")
