"""Pure-Python dimensional inspection helper. Not an authorization to release product."""
from decimal import Decimal, InvalidOperation
from typing import Optional


def decision_for_dimension(nominal: str, lower_deviation: str, upper_deviation: str,
                           measured: Optional[str]) -> dict:
    """A single-dimensional check; all values in mm and all bounds inclusive."""
    fields = (nominal, lower_deviation, upper_deviation, measured)
    if any(x is None or str(x).strip() == "" for x in fields):
        return {"decision": "INSUFFICIENT_DATA", "reason": "A required dimension or measurement is missing."}
    try:
        n, ld, ud, m = (Decimal(str(x)) for x in fields)
        if not all(x.is_finite() for x in (n, ld, ud, m)):
            raise ValueError("Non-finite numerical value")
    except (InvalidOperation, ValueError) as exc:
        return {"decision": "INSUFFICIENT_DATA", "reason": f"Invalid numeric data: {exc}"}
    low, high = n + ld, n + ud
    if ld > ud:
        return {"decision": "INSUFFICIENT_DATA", "reason": "Lower deviation exceeds upper deviation."}
    decision = "PASS" if low <= m <= high else "FAIL"
    return {"decision": decision, "low_mm": str(low), "high_mm": str(high),
            "measured_mm": str(m), "reason": f"Measured {m} mm; permitted range [{low}, {high}] mm (inclusive)."}


if __name__ == "__main__":
    import argparse, json
    p = argparse.ArgumentParser(description="Deterministic single-dimension QA check")
    p.add_argument("--nominal", required=True)
    p.add_argument("--low-dev", required=True)
    p.add_argument("--high-dev", required=True)
    p.add_argument("--measured", default=None)
    a = p.parse_args()
    print(json.dumps(decision_for_dimension(a.nominal, a.low_dev, a.high_dev, a.measured), indent=2))
