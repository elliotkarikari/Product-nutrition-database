"""Canonical core records (docs/DATA_MODEL.md).

A nutrient value is never stored bare: every NutrientObservation points at
the Food it describes and the DatasetRelease it came from, and keeps the
value exactly as the source wrote it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DatasetRelease:
    source_id: str          # id in data/source-register.yaml
    dataset: str
    edition: str
    publisher: str
    url: str                # the file the values were read from
    retrieved: str          # ISO 8601, UTC
    sha256: str
    licence: str
    attribution: str


@dataclass(frozen=True, slots=True)
class NutrientDefinition:
    code: str               # the source's own code, e.g. ENGFIB
    label: str              # the source's own column label
    unit: str | None
    table: str              # worksheet the column comes from
    method: str | None      # set where the source defines one, e.g. fibre: nsp_englyst | aoac


@dataclass(frozen=True, slots=True)
class Food:
    food_id: str            # unique within the release
    source_code: str        # the source's food code; NOT unique in CoFID 2021
    name: str
    description: str | None
    group: str | None
    previous_codes: str | None
    main_data_reference: str | None
    footnote: str | None
    source_row: int         # worksheet row in the source file
    release: DatasetRelease


@dataclass(frozen=True, slots=True)
class NutrientObservation:
    food: Food
    definition: NutrientDefinition
    value: float | None     # None for trace or unquantified values
    value_text: str         # exactly as written in the source
    value_kind: str         # number | number_bracketed | trace | present_not_quantified
    basis: str              # per_100g | per_100ml | per_100g_fatty_acids | food_factor
    state: str              # how the source states the food's state
    method: str             # how the value was produced, as far as the source says
    status: str             # current | superseded
    release: DatasetRelease
