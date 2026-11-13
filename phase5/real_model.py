"""Dependency-free inference for the deployed steel-fault model."""
from __future__ import annotations

import gzip
import json
import math
from functools import lru_cache
from pathlib import Path

ARTIFACT = Path(__file__).with_name("model") / "steel_fault_forest.json.gz"


@lru_cache(maxsize=1)
def load_model() -> dict:
    with gzip.open(ARTIFACT, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _tree_probabilities(tree: dict, values: list[float]) -> list[float]:
    node = 0
    while tree["f"][node] >= 0:
        feature = tree["f"][node]
        node = tree["l"][node] if values[feature] <= tree["t"][node] else tree["r"][node]
    counts = tree["v"][node]
    total = sum(counts)
    return [value / total for value in counts]


def predict_steel_fault(values: list[float]) -> dict:
    model = load_model()
    if len(values) != len(model["features"]):
        raise ValueError(f"Expected {len(model['features'])} measurements; received {len(values)}")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Measurements must all be finite numbers")
    probabilities = [0.0] * len(model["classes"])
    for tree in model["trees"]:
        for index, probability in enumerate(_tree_probabilities(tree, values)):
            probabilities[index] += probability
    probabilities = [value / len(model["trees"]) for value in probabilities]
    winner = max(range(len(probabilities)), key=probabilities.__getitem__)
    return {
        "classification": model["classes"][winner],
        "confidence": round(probabilities[winner], 6),
        "probabilities": {
            label: round(probability, 6)
            for label, probability in zip(model["classes"], probabilities)
        },
        "model_version": model["model_version"],
        "dataset": model["dataset"],
        "dataset_doi": model["dataset_doi"],
    }
