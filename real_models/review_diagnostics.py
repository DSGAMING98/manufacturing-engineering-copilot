"""Development-only router diagnostic. Not an independently annotated field test.

Run: python -m real_models.review_diagnostics
Prompt/label pairs were developer-authored. Do not publish the diagnostic
accuracy as representative manufacturing-user accuracy.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from phase5.assistant import route_domain
from phase4.retrieval import load_corpus

ROOT = Path(__file__).resolve().parents[1]

CASES = {
    "design": """check hole shaft fit|clearance of cylindrical features|minimum hole maximum shaft|calculate interference|are mating diameters in transition|worst case fit envelope|find fit class|how much shaft clearance is present|hole minimum 20 shaft maximum 21|shaft and hole pairing|cylindrical assembly review|fit clearance 0.05mm|interference of 0.12mm|hole_max=20.02 shaft_min=20|mating diameters 18mm""",
    "process": """turning speed in RPM|lathe single pass time|cutting speed 100 m/min|spindle rpm for a 20mm cylinder|feed rate during turning|feed per revolution|estimate machining time|single-pass process plan|cutting time length 80mm|what is the spindle speed|workpiece turning diameter|compute rpm|cutting speed and feed rate|lathe operating data|machining time with tool feed""",
    "production": """OEE of the current shift|availability performance quality|good parts and total parts|production run efficiency|compute overall equipment effectiveness OEE|run time of production|planned minutes and good count|line effectiveness|calculate availability|total parts 400 good parts 350|ideal cycle time|part-count data|production effectiveness|run time planned time ratio|cycle time throughput""",
    "quality": """dimensional quality check|check tolerance nominal 20mm|inspection pass or fail|measured feature diameter|measurement under specification limits|conforming tolerance|asymmetric tolerance decision|lower deviation and upper deviation|quality gauge reads|one dimension inspection|nominal=20 measured=21|acceptance check of a measured value|inspection pass at boundary|is measurement in tolerance|pass fail dimensional check""",
    "maintenance": """MTBF from operating hours|MTTR repair duration|failure counts and breakdowns|historical reliability indicators|machine downtime hours|repair hours 20|operating hours 800 and failures 4|estimate observed availability|mean time between failure|equipment restoration time|maintenance uptime hours|reliability indicators not remaining-life|what is remaining useful life|breakdowns in a shift|repair duration and uptime""",
    "documentation": """draft inspection record|inspection sheet with timestamp|drawing revision in record|record id and feature id|draft measurement record|technical documentation of inspection|inspection record metadata|controlled draft for drawing ID|equipment id and operator id|gauge id in inspection sheet|final sign-off status|traceable draft|record id IR-04|structured inspection record|drawing id and revision""",
    "knowledge": """find a registered source|procedure excerpt for parts|approved documents about gauges|search document evidence|cite source lines|indexed evidence library|find the local procedure|what does this registered document say|knowledge citation check|find traceability identifiers|registered work instructions|what source supports these numbers|procedure library reference|search source citations|look up approved document excerpt""",
}
ABSTAIN = """hi there|please help me|how is the weather|summarize this poem|tell me a joke|42|what time is it|make a PPT|tell me everything|give recommendations|I have a question|open the door|move the actuator|buy a car|write some code|explain a term|unrelated question|thank you|hello world|nothing specified""".split("|")


def main():
    prompts = [(label, prompt) for label, part in CASES.items() for prompt in part.split("|")]
    prompts += [(None, prompt) for prompt in ABSTAIN]
    results = []
    for expected, prompt in prompts:
        predicted, scores = route_domain(prompt)
        results.append({"prompt": prompt, "expected": expected or "ABSTAIN",
                        "predicted": predicted or "ABSTAIN",
                        "correct": expected == predicted, "scores": scores})
    failures = [item for item in results if not item["correct"]]
    counts = Counter(item["expected"] for item in results)
    success = Counter(item["expected"] for item in results if item["correct"])
    chunks = load_corpus()
    report = {
        "source": "developer-authored diagnostic, not independently labelled field requests",
        "routing": {
            "n": len(results), "correct": len(results)-len(failures),
            "accuracy": (len(results)-len(failures))/len(results),
            "per_label_recall": {k: success[k]/v for k,v in counts.items()},
            "failures": failures,
        },
        "retrieval": {
            "status": "NOT_EVALUATED",
            "registered_source_ids": sorted({item.source_id for item in chunks}),
            "indexed_chunks": len(chunks),
            "reason": "Hit@k needs independent relevance-labelled query-to-document pairs",
        },
    }
    out = ROOT / "real_models/evidence/review_diagnostics.json"
    out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"prompts": len(results), "routing_correct": len(results)-len(failures),
                      "retrieval_status": "NOT_EVALUATED"}, indent=2))


if __name__ == "__main__":
    main()
