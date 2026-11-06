"""Measure the matching assistant against memory/verification/matching-eval-set.json.

Deterministic stage: recall at k (is an acceptable food among the candidates?).
Jev stage, only when TYPESAFE_API_KEY is set in your environment: for each
threshold, precision of "proposed" candidates and how often the assistant
proposes the right food or correctly abstains. The key is never printed.

    PYTHONPATH=src python3 scripts/evaluate_matching.py [--out memory/verification/<file>.json]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from shelfscale import matching

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    args = parser.parse_args()
    data = json.loads((ROOT / "memory/verification/matching-eval-set.json").read_text())
    rows = []
    for item in data["items"]:
        result = matching.propose(item["query"])
        gold = set(item["gold"])
        rows.append({"query": item["query"], "gold": sorted(gold), "engine": result["engine"],
                     "candidates": [{"code": c["code"], "retrieval_score": c["retrieval_score"],
                                     "probability": c["probability"], "correct": c["code"] in gold}
                                    for c in result["candidates"]]})
    answerable = [r for r in rows if r["gold"]]
    report = {
        "labels_status": data["labels_status"],
        "items": len(rows), "answerable": len(answerable), "abstain_items": len(rows) - len(answerable),
        "deterministic": {
            "recall_at_k": sum(any(c["correct"] for c in r["candidates"]) for r in answerable) / len(answerable),
            "top1": sum(bool(r["candidates"]) and r["candidates"][0]["correct"] for r in answerable) / len(answerable),
            "k": matching.settings()["candidates"],
        },
        "engine": rows[0]["engine"] if rows else None,
    }
    if os.environ.get(matching.KEY_VAR) and rows and rows[0]["engine"]["engine"] == "jev":
        sweep = {}
        for t in THRESHOLDS:
            proposed = [(r, c) for r in rows for c in r["candidates"] if c["probability"] >= t]
            right_item = sum((any(c["correct"] and c["probability"] >= t for c in r["candidates"])
                              if r["gold"] else all(c["probability"] < t for c in r["candidates"]))
                             for r in rows)
            sweep[str(t)] = {"proposals": len(proposed),
                             "precision": (sum(c["correct"] for _, c in proposed) / len(proposed)) if proposed else None,
                             "items_right": right_item / len(rows)}
        report["jev"] = {"model": rows[0]["engine"].get("model"), "sweep": sweep}
    report["rows"] = rows
    text = json.dumps(report, indent=1)
    if args.out:
        Path(args.out).write_text(text)
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
