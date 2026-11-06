"""Check Elliot's FPS transcription against the tabula extraction on main.

Usage:
    git -C <main checkout> show cfadc8a:"Data/Processed/FoodPortionSized/FoodPortionSizes_PDF.csv" > extraction.csv
    PYTHONPATH=src python3 scripts/reconcile_fps.py extraction.csv > docs/fps_reconciliation.csv

The extraction is a check only, never a source; the transcription wins.
Both files follow the book's order and its group headings. Within a group:

- same food and portion: the extraction record has exactly the same words
  (brand + food name + portion, lower-cased, punctuation ignored, order preserved) as the
  transcription row. Only these pairs can disagree on weight;
- ambiguous or reordered wording stays unresolved unless a reviewed food/portion
  decision establishes the match; word order and repeated tokens are preserved;
- anything else is "not located in extraction"; extraction records with a
  weight that no transcription row claimed are "only in extraction".

OCR-character differences (I or l for 1, O for 0, m1 or in1 for ml) are
reported separately from real weight differences. Nothing is averaged.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys

EXPECTED_SHA256 = "cd5816a5da578e140a8094822916210624fc201ac9c936fe8ea1904205448dd1"
_WEIGHT = re.compile(r"^[\dIlOo][\dIlOo., /-]*\s*(g|ml|m1|in1)$")


def words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", text.lower()))


def identity_key(group, brand, name, portion):
    return json.dumps([group.strip(), brand.strip().casefold(), name.strip().casefold(),
                       portion.strip().casefold()], ensure_ascii=False)


def squash(weight: str) -> str:
    return weight.replace(" ", "").lower()


def ocr(weight: str) -> str:
    w = squash(weight).replace("in1", "ml").replace("m1", "ml")
    return w.replace("i", "1").replace("l", "1").replace("o", "0").replace("m1", "ml")


def extraction_records(rows, groups):
    records = collections.defaultdict(list)
    group, name = None, ""
    for row in rows:
        cells = [c.strip() for c in row[1:]] + ["", "", ""]
        if cells[0] in groups and not any(cells[1:4]):
            group, name = cells[0], ""
            continue
        if group is None:
            continue
        if cells[0]:
            name = cells[0]
        present = [c for c in cells[:4] if c]
        weight = next((c for c in reversed(present) if _WEIGHT.match(c)), "")
        text = [c for c in present if c != weight]
        if not cells[0] and name:
            text = [name] + text
        if weight or text:
            records[group].append({"row": row[0], "text": " | ".join(text), "weight": weight,
                                   "words": words(" ".join(text))})
    return records


def main(path: str) -> None:
    raw = open(path, "rb").read()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        sys.exit("Extraction file does not match the checksum recorded in the FPS manifest.")
    extraction = list(csv.reader(io.StringIO(raw.decode("utf-8"))))[1:]
    sys.path.insert(0, "src")
    from shelfscale.fps import load_release
    _, t_raw = load_release()
    transcription = list(csv.reader(io.StringIO(t_raw.decode("cp1252"))))[1:]
    groups = list(dict.fromkeys(r[1].strip() for r in transcription))
    records = extraction_records(extraction, groups)

    reviews = json.loads((Path(__file__).resolve().parents[1] / "data/reconciliation/fps-review.json").read_text())
    reserved = {r["extraction_row"] for r in reviews.values() if r["extraction_row"]}
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["identity_key", "review_note", "result", "group", "transcription_row", "transcription_brand", "transcription_food",
                  "transcription_portion", "transcription_weight", "extraction_row",
                  "extraction_text", "extraction_weight"])
    used = set()
    for index, group, brand, name, portion, weight in transcription:
        g = group.strip()
        identity = identity_key(g, brand, name, portion)
        key = words(" ".join([brand, name, portion]))
        review = reviews.get(identity)
        exact = [r for r in records[g] if r["words"] == key and (g, r["row"]) not in used
                 and r["row"] not in reserved]
        record, result, note = None, "not located in extraction", ""
        if review:
            note = review["reason"]
            if review["extraction_row"] and weight != review["transcription_weight"]:
                raise ValueError("Reviewed transcription weight changed")
            if review["extraction_row"]:
                exact = [r for r in records[g] if r["row"] == review["extraction_row"]]
                if len(exact) != 1: raise ValueError("Reviewed extraction row missing")
            else:
                exact = []
                result = "ambiguous portion; book check required"
        if len(exact) > 1:
            result = "ambiguous extraction matches"
            note = "Candidate rows: " + ", ".join(r["row"] for r in exact)
        elif exact:
            record = exact[0]
            if (g, record["row"]) in used: raise ValueError("Extraction row reused")
            if squash(record["weight"]) == squash(weight):
                result = "agree (reviewed food and portion)" if review else "agree (same words, same weight)"
            elif not record["weight"] or not weight.strip():
                result = "one side has no weight"
            elif ocr(record["weight"]) == ocr(weight):
                result = "OCR-character difference only"
            else:
                result = "DIFFERENT WEIGHT, same food and portion"
        if record:
            used.add((g, record["row"]))
        out.writerow([identity, note, result, g, index, brand, name, portion, weight,
                      record["row"] if record else "", record["text"] if record else "",
                      record["weight"] if record else ""])
    for g, recs in records.items():
        for r in recs:
            if (g, r["row"]) not in used and r["weight"]:
                out.writerow(["", "", "only in extraction", g, "", "", "", "", "", r["row"], r["text"], r["weight"]])


if __name__ == "__main__":
    main(sys.argv[1])
