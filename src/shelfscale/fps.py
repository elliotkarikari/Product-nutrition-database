"""Import Food Portion Sizes (3rd edition, FSA, TSO 2002) from Elliot's transcription.

Rights: Crown copyright, NOT covered by the Open Government Licence. In this
repository on Elliot's decision of November 5, 2026 (data/raw/
uk-food-portion-sizes-2002/DECISION.md). Every value carries the book
citation as its provenance.

The source file is read exactly as committed (checked against MANIFEST.json).
Weights are read, never corrected: a single "Ng" value becomes grams; "Nml"
stays a volume (no density is assumed); "a/b g" alternatives and "a-b g"
ranges keep their numbers without choosing one; anything else (for example
"l00g", with a letter l) is unreadable and reported. Rows with no weight are
cross-references ("see ...") or have no weight given; they are reported,
not imported.

CoFID matching: exact food name only (case and whitespace ignored). No
fuzzy or legacy similarity matches are used. Everything else stays an
FPS-only portion.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .model import DatasetRelease, Food, TypicalPortion

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "uk-food-portion-sizes-2002"

_NUM = r"\d+(?:\.\d+)?"
_SINGLE = re.compile(rf"^({_NUM})\s*(g|ml)$")
_ALTERNATIVES = re.compile(rf"^{_NUM}\s*g?(?:\s*/\s*{_NUM}\s*g?)+$")
_RANGE = re.compile(rf"^({_NUM})\s*g?\s*-\s*({_NUM})\s*g$")


@dataclass(frozen=True)
class FPSImport:
    release: DatasetRelease
    portions: list[TypicalPortion]
    not_imported: list[dict[str, str]]


def load_release(snapshot: Path = SNAPSHOT) -> tuple[DatasetRelease, bytes]:
    manifest = json.loads((snapshot / "MANIFEST.json").read_text(encoding="utf-8"))
    entry = manifest["files"][0]
    raw = (snapshot / entry["name"]).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != entry["sha256"]:
        raise ValueError(
            f"{entry['name']} does not match MANIFEST.json (expected sha256 "
            f"{entry['sha256']}, found {actual}). Refusing to import."
        )
    release = DatasetRelease(
        source_id=manifest["source_id"],
        dataset=manifest["dataset"],
        edition=manifest["edition"],
        publisher=manifest["publisher"],
        url=manifest["url"],
        retrieved=manifest["retrieved"],
        sha256=entry["sha256"],
        licence=manifest["rights"],
        attribution=manifest["citation"],
    )
    return release, raw


def read_weight(text: str) -> tuple[str, tuple[float, ...], str | None]:
    """(value_kind, amounts, unit) for a weight exactly as transcribed."""
    token = text.strip()
    single = _SINGLE.match(token)
    if single:
        unit = single.group(2)
        return ("single" if unit == "g" else "volume_ml"), (float(single.group(1)),), unit
    rng = _RANGE.match(token)
    if rng:
        return "range", (float(rng.group(1)), float(rng.group(2))), "g"
    if token.endswith("g") and _ALTERNATIVES.match(token):
        return "alternatives", tuple(float(n) for n in re.findall(_NUM, token)), "g"
    return "unreadable", (), None


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().casefold())


def import_fps(cofid_foods: list[Food] | None = None, snapshot: Path = SNAPSHOT) -> FPSImport:
    release, raw = load_release(snapshot)
    rows = list(csv.reader(io.StringIO(raw.decode("cp1252"))))
    header, body = rows[0], rows[1:]
    if header != ["", "Group", "Brand", "Food Name", "Portion Consumed", "Weight"]:
        raise ValueError(f"Unexpected header {header!r}.")

    by_name: dict[str, list[Food]] = {}
    for food in cofid_foods or []:
        by_name.setdefault(_key(food.name), []).append(food)

    portions: list[TypicalPortion] = []
    not_imported: list[dict[str, str]] = []
    for index, group, brand, name, portion, weight in body:
        if not weight.strip():
            reason = "cross-reference" if re.search(r"\bsee\b", name, re.IGNORECASE) else "no weight given"
            not_imported.append({"row": index, "food_name": name, "reason": reason})
            continue
        kind, amounts, unit = read_weight(weight)
        if kind == "unreadable":
            not_imported.append({"row": index, "food_name": name, "weight_text": weight,
                                 "reason": "weight not readable as written; not corrected"})
            continue
        matches = by_name.get(_key(name), [])
        cofid_id = matches[0].food_id if len(matches) == 1 else None
        portions.append(TypicalPortion(
            source_row=index,
            group=group,
            brand=brand.strip() or None,
            food_name=name,
            portion_description=portion.strip() or None,
            weight_text=weight,
            value_kind=kind,
            amounts=amounts,
            unit=unit,
            grams=amounts[0] if kind == "single" else None,
            basis="typical_portion",
            cofid_food_id=cofid_id,
            cofid_match="exact_name" if cofid_id else "none",
            release=release,
        ))
    return FPSImport(release=release, portions=portions, not_imported=not_imported)
