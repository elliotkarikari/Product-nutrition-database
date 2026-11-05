"""Import unit weights from the official fruit and vegetable sampling reports.

Sources (data/raw/uk-fv-sampling-2011 and -2015): the Department of Health
2013 sampling report (sampling 2011-12) and the Public Health England 2017
sampling report (sampling 2015-16). Each PDF is kept unchanged; the importer
reads its pdftotext -layout extraction, after checking both checksums.

What is imported, per composite food:

- each sub-sample's average item weight from the report's "Edible portion
  weights" table, grouped under the composite, with the retail purchase
  record (name, brand, pack size, date, shop) where the report gives one;
- a PortionObservation with the sample size and spread (min, max, mean, sd).

The gate: a composite is imported only when the mean of its table's first
weight column reproduces the report's own stated average (within 0.1 g,
the precision the report prints). That is the evidence that the column is
the whole-item weight. The same check decides whether edible portions are
imported. Tables that do not reconcile are reported, with the reason, and
nothing is imported from them. No value is guessed.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .model import (
    DatasetRelease,
    PortionObservation,
    PurchaseRecord,
    SampleComposite,
    SubSample,
)

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
SNAPSHOTS = (RAW / "uk-fv-sampling-2011", RAW / "uk-fv-sampling-2015")
WEIGHT_TOLERANCE_G = 0.1
EDIBLE_TOLERANCE = 0.01

_NOISE = re.compile(
    r"^\s*(\d+|Nutrient analysis of fruit and vegetables|"
    r"Nutrient analysis survey of fresh and processed fruit and vegetables with respect to fibre)\s*$"
)
_SAMPLE = re.compile(r"^Sample (\d+): (.+?)\s*$")
_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
_STATED_WEIGHT = re.compile(r"^\s*(Average weight (?:of )?.+?)\s*[=:]\s*(\d+(?:\.\d+)?)\s*g?\s*$")
_STATED_EDIBLE = re.compile(r"^\s*Average edible portion\s*[=:]\s*(\d+(?:\.\d+)?)\s*$")
_FIELD = re.compile(
    r"^(Composite Sample Number|Composite Sample Name|Sub-sample Number|Sub-sample Name|"
    r"Brand|Pack size|Purchase Date|Place of Purchase):\s*(.*?)\s*$"
)
_ANY_LABEL = re.compile(r"^[A-Z][A-Za-z /()&-]*:")
_DATE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})$")


@dataclass(frozen=True)
class NotImported:
    release: DatasetRelease
    composite_number: str
    food_name: str
    reason: str


@dataclass(frozen=True)
class SampleImport:
    observations: list[PortionObservation]
    not_imported: list[NotImported]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_snapshot(folder: Path) -> tuple[DatasetRelease, str]:
    """Verify the report and its text against MANIFEST.json; return release and text."""
    manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        actual = _sha256(folder / entry["name"])
        if actual != entry["sha256"]:
            raise ValueError(
                f"{entry['name']} does not match MANIFEST.json (expected sha256 "
                f"{entry['sha256']}, found {actual}). Refusing to import."
            )
    report = next(f for f in manifest["files"] if f["role"] == "report")
    text = next(f for f in manifest["files"] if f["role"] == "text")
    release = DatasetRelease(
        source_id=manifest["source_id"],
        dataset=manifest["dataset"],
        edition=manifest["edition"],
        publisher=manifest["publisher"],
        url=report["url"],
        retrieved=manifest["retrieved"],
        sha256=report["sha256"],
        licence=manifest["licence"],
        attribution=manifest["attribution"],
    )
    return release, (folder / text["name"]).read_text(encoding="utf-8")


def _iso_date(text: str | None) -> str | None:
    match = _DATE.match((text or "").strip())
    if not match:
        return None
    day, month, year = (int(g) for g in match.groups())
    if year < 100:
        year += 2000
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _purchase_records(lines: list[str]) -> dict[tuple[str, str], PurchaseRecord]:
    """Map (composite number, sub-sample number) to its first full purchase record."""
    records: dict[tuple[str, str], PurchaseRecord] = {}
    current: dict[str, str] | None = None
    last_field: str | None = None

    def flush() -> None:
        if current and current.get("Purchase Date") is not None:
            key = (current.get("Composite Sample Number", ""), current.get("Sub-sample Number", ""))
            if key not in records:
                records[key] = PurchaseRecord(
                    subsample_number=key[1],
                    name=current.get("Sub-sample Name") or None,
                    brand=current.get("Brand") or None,
                    pack_size=current.get("Pack size") or None,
                    purchase_date=current.get("Purchase Date") or None,
                    place=current.get("Place of Purchase") or None,
                )

    for line in lines:
        match = _FIELD.match(line)
        if match:
            label, value = match.groups()
            if label == "Composite Sample Number":
                flush()
                current = {}
            if current is not None:
                current[label] = value
                last_field = label
            continue
        if not line.strip():
            last_field = None
            continue
        if current is not None and last_field in ("Sub-sample Name", "Place of Purchase") \
                and not _ANY_LABEL.match(line.strip()):
            current[last_field] = f"{current[last_field]} {line.strip()}".strip()
        else:
            last_field = None
    flush()
    return records


def _within(value: float, stated: float, tolerance: float) -> bool:
    return abs(value - stated) <= tolerance + 1e-9


def import_samples(folder: Path) -> SampleImport:
    release, text = load_snapshot(folder)
    lines = text.split("\n")
    purchases = _purchase_records(lines)
    heads = [(i, m) for i, line in enumerate(lines) for m in [_SAMPLE.match(line)] if m]

    observations: list[PortionObservation] = []
    not_imported: list[NotImported] = []
    for k, (start, head) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        block = [line for line in lines[start:end] if not _NOISE.match(line)]
        table_at = next((j for j, line in enumerate(block) if "Edible portion weights" in line), None)
        if table_at is None:
            continue
        number, name = head.group(1), head.group(2)

        def skip(reason: str) -> None:
            not_imported.append(NotImported(release, number, name, reason))

        before = block[:table_at]
        stated_weight = next((m for m in map(_STATED_WEIGHT.match, before) if m), None)
        stated_edible = next((m for m in map(_STATED_EDIBLE.match, before) if m), None)
        note = " ".join(
            line.strip() for line in block[1:table_at]
            if line.strip() and not _STATED_WEIGHT.match(line) and not _STATED_EDIBLE.match(line)
            and not line.strip().startswith("Average ")
        )

        rows: list[tuple[str, list[float | None], str]] = []
        for line in block[table_at + 1:]:
            if not line.strip():
                continue
            row = re.match(rf"^\s*({number}\.\d+)\s+(.*)$", line)
            if row:
                cells = [
                    None if token == "N/A" else float(token)
                    for token in row.group(2).split()
                    if _NUMBER.match(token) or token == "N/A"
                ]
                rows.append((row.group(1), cells, line.rstrip()))
            elif rows and not line[:1].isspace():
                break          # a new title at the left margin ends the table

        if stated_weight is None:
            skip("The report states no average item weight for this table.")
            continue
        stated_g = float(stated_weight.group(2))
        weights = [cells[0] for _, cells, _ in rows if cells and cells[0] is not None]
        if not weights:
            skip("The table has no readable weight values.")
            continue
        mean_g = statistics.fmean(weights)
        if not _within(mean_g, stated_g, WEIGHT_TOLERANCE_G):
            skip(
                f"The table's first weight column averages {mean_g:.2f} g over {len(weights)} "
                f"sub-samples; the report states {stated_g:g} g. Not reconciled."
            )
            continue

        edible_ok = False
        stated_ep = None
        if stated_edible is not None:
            stated_ep = float(stated_edible.group(1))
            edible = [cells[-1] for _, cells, _ in rows if cells and cells[-1] is not None]
            edible_ok = (
                bool(edible) and all(0 < e <= 1 for e in edible)
                and _within(statistics.fmean(edible), stated_ep, EDIBLE_TOLERANCE)
            )

        subsamples = []
        dates = []
        for sub_number, cells, row_text in rows:
            purchase = purchases.get((number, sub_number))
            iso = _iso_date(purchase.purchase_date if purchase else None)
            if iso:
                dates.append(iso)
            subsamples.append(SubSample(
                number=sub_number,
                weight_g=cells[0] if cells else None,
                edible_portion=cells[-1] if (edible_ok and cells) else None,
                row_text=row_text,
                purchase=purchase,
            ))
        if not dates:
            skip("No purchase date could be read for any sub-sample, so the period is unknown.")
            continue

        composite = SampleComposite(
            composite_number=number,
            food_name=name,
            preparation_note=note,
            subsamples=tuple(subsamples),
            release=release,
        )
        edible_values = [s.edible_portion for s in subsamples if s.edible_portion is not None]
        observations.append(PortionObservation(
            composite=composite,
            description=stated_weight.group(1),
            grams=mean_g,
            basis="weighed_sample_mean",
            sample_size=len(weights),
            min_g=min(weights),
            max_g=max(weights),
            mean_g=mean_g,
            sd_g=statistics.stdev(weights) if len(weights) > 1 else None,
            stated_mean_g=stated_g,
            edible_portion_mean=statistics.fmean(edible_values) if edible_values else None,
            edible_portion_min=min(edible_values) if edible_values else None,
            edible_portion_max=max(edible_values) if edible_values else None,
            edible_portion_n=len(edible_values) if edible_values else None,
            stated_edible_portion=stated_ep if edible_ok else None,
            period_start=min(dates),
            period_end=max(dates),
            release=release,
        ))
        if stated_ep is not None and not edible_ok:
            not_imported.append(NotImported(
                release, number, name,
                f"Edible portions only: the table's last column does not reproduce the stated "
                f"average edible portion ({stated_ep:g}). Weights were imported; edible portions were not.",
            ))
    return SampleImport(observations=observations, not_imported=not_imported)


def import_all_samples() -> SampleImport:
    observations: list[PortionObservation] = []
    not_imported: list[NotImported] = []
    for folder in SNAPSHOTS:
        result = import_samples(folder)
        observations.extend(result.observations)
        not_imported.extend(result.not_imported)
    return SampleImport(observations=observations, not_imported=not_imported)
