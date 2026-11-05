"""Import CoFID 2021 into the canonical core.

Reads the raw GOV.UK workbook in data/raw/uk-cofid-2021, after checking it
against the sha256 in MANIFEST.json, and returns foods and nutrient
observations. Every observation keeps the value text exactly as the
workbook has it, and points at its food and at the dataset release.

Rules, all from the dataset's own notes and user guide:

- Values are per 100 g of food, except alcoholic beverages (food group Q)
  which are per 100 ml, and the fatty-acid columns labelled "/100g FA",
  which are per 100 g of fatty acids.
- "Tr" is a trace. "N" means present in significant quantities with no
  reliable amount. Neither is turned into a number.
- A few values are written in brackets, e.g. "(0.11)". The 2021 user guide
  does not define brackets (in the printed McCance and Widdowson tables they
  mark estimates). The number is kept, flagged as number_bracketed, so a
  consumer can tell it apart from an ordinary value.
- NSP fibre (ENGFIB, Englyst method) and AOAC fibre (AOACFIB) are separate
  nutrients measured by different methods. They stay separate observations
  and are never merged or converted.
- Food codes are not unique in CoFID 2021 (13-669 names two foods), so
  foods get an id that is unique within the release; see _food_ids.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .model import DatasetRelease, Food, NutrientDefinition, NutrientObservation
from .xlsx import read_sheet, sheet_names

DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "uk-cofid-2021"

_NON_DATA_SHEETS = {"List of tables", "1.1 Notes"}
_FACTORS_SHEET = "1.2 Factors"
_FIRST_VALUE_COLUMN = 7          # columns A-G are food identity
_FIRST_DATA_ROW = 4              # rows 1-3 are headers (Factors has one header row)
_ALCOHOLIC_GROUP = "Q"           # user guide, Appendix B
_FATTY_ACID_BASIS = re.compile(r"/\s*100g FA\b")
_NUMBER = re.compile(r"-?\d+(\.\d+)?([eE]-?\d+)?")
_BRACKETED = re.compile(r"\((-?\d+(\.\d+)?)\)")
_FIBRE_METHODS = {"ENGFIB": "nsp_englyst", "AOACFIB": "aoac"}
STATE = "as_described_in_food_name"
METHOD = "compiled_food_table"


@dataclass(frozen=True)
class CoFIDImport:
    release: DatasetRelease
    foods: list[Food]
    definitions: list[NutrientDefinition]
    observations: list[NutrientObservation]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_release(snapshot: Path = DEFAULT_SNAPSHOT) -> tuple[DatasetRelease, Path]:
    """Read MANIFEST.json and verify the dataset file before anything is parsed."""
    manifest = json.loads((snapshot / "MANIFEST.json").read_text(encoding="utf-8"))
    entry = next(f for f in manifest["files"] if f["role"] == "dataset")
    path = snapshot / entry["name"]
    actual = _sha256(path)
    if actual != entry["sha256"]:
        raise ValueError(
            f"{path.name} does not match MANIFEST.json "
            f"(expected sha256 {entry['sha256']}, found {actual}). Refusing to import."
        )
    release = DatasetRelease(
        source_id=manifest["source_id"],
        dataset=manifest["dataset"],
        edition=manifest["edition"],
        publisher=manifest["publisher"],
        url=entry["url"],
        retrieved=manifest["retrieved"],
        sha256=entry["sha256"],
        licence=manifest["licence"],
        attribution=manifest["attribution"],
    )
    return release, path


def _unit(label: str) -> str | None:
    match = re.search(r"\(([^()]*)\)\s*$", label)
    return match.group(1).strip() if match else None


def _parse_value(text: str, where: str) -> tuple[float | None, str]:
    token = text.strip()
    if token == "Tr":
        return None, "trace"
    if token == "N":
        return None, "present_not_quantified"
    if _NUMBER.fullmatch(token):
        return float(token), "number"
    bracketed = _BRACKETED.fullmatch(token)
    if bracketed:
        return float(bracketed.group(1)), "number_bracketed"
    raise ValueError(f"Unrecognised value {text!r} at {where}.")


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.strip()
    return text or None


def _food_ids(codes: dict[int, str]) -> dict[int, str]:
    """The food code where it is unique; code@row<n> for every row that shares one."""
    counts = Counter(codes.values())
    return {
        row: code if counts[code] == 1 else f"{code}@row{row}"
        for row, code in codes.items()
    }


def import_cofid(snapshot: Path = DEFAULT_SNAPSHOT) -> CoFIDImport:
    release, path = load_release(snapshot)
    tables = [name for name in sheet_names(path) if name not in _NON_DATA_SHEETS]

    sheets = {name: read_sheet(path, name) for name in tables}

    # Food identity comes from the Factors sheet; every other sheet must list
    # exactly the same codes on exactly the same rows.
    factors = sheets[_FACTORS_SHEET]
    codes = {
        row: cells[0].strip()
        for row, cells in factors.items()
        if row >= _FIRST_DATA_ROW and cells and _clean(cells[0])
    }
    for name, rows in sheets.items():
        other = {
            row: cells[0].strip()
            for row, cells in rows.items()
            if row >= _FIRST_DATA_ROW and cells and _clean(cells[0])
        }
        if other != codes:
            raise ValueError(f"Sheet {name!r} does not list the same foods on the same rows.")

    ids = _food_ids(codes)
    foods: dict[int, Food] = {}
    for row, code in codes.items():
        cells = factors[row] + [None] * 7
        foods[row] = Food(
            food_id=ids[row],
            source_code=code,
            name=_clean(cells[1]),
            description=_clean(cells[2]),
            group=_clean(cells[3]),
            previous_codes=_clean(cells[4]),
            main_data_reference=_clean(cells[5]),
            footnote=_clean(cells[6]),
            source_row=row,
            release=release,
        )

    definitions: list[NutrientDefinition] = []
    observations: list[NutrientObservation] = []
    for name in tables:
        rows = sheets[name]
        labels = rows[1]
        source_codes = rows.get(2, []) if name != _FACTORS_SHEET else []
        for column in range(_FIRST_VALUE_COLUMN, len(labels)):
            label = _clean(labels[column])
            if label is None:
                continue
            if name == _FACTORS_SHEET:
                code = f"FACTOR:{label}"
            else:
                code = _clean(source_codes[column]) if column < len(source_codes) else None
                if code is None:
                    raise ValueError(f"Column {column} of {name!r} has a label but no code.")
            definition = NutrientDefinition(
                code=code,
                label=label,
                unit=_unit(label) if name != _FACTORS_SHEET else None,
                table=name,
                method=_FIBRE_METHODS.get(code),
            )
            definitions.append(definition)
            per_fatty_acids = bool(_FATTY_ACID_BASIS.search(label))

            for row, food in foods.items():
                cells = rows[row]
                text = cells[column] if column < len(cells) else None
                if text is None or not text.strip():
                    continue
                value, kind = _parse_value(text, f"{name} row {row} column {column + 1}")
                if name == _FACTORS_SHEET:
                    basis = "food_factor"
                elif per_fatty_acids:
                    basis = "per_100g_fatty_acids"
                elif (food.group or "").startswith(_ALCOHOLIC_GROUP):
                    basis = "per_100ml"
                else:
                    basis = "per_100g"
                observations.append(
                    NutrientObservation(
                        food=food,
                        definition=definition,
                        value=value,
                        value_text=text,
                        value_kind=kind,
                        basis=basis,
                        state=STATE,
                        method=METHOD,
                        status="current",
                        release=release,
                    )
                )

    return CoFIDImport(
        release=release,
        foods=list(foods.values()),
        definitions=definitions,
        observations=observations,
    )
