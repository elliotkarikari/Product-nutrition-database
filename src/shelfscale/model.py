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


@dataclass(frozen=True, slots=True)
class PurchaseRecord:
    """One retail purchase as the sampling report records it, text as written."""
    subsample_number: str
    name: str | None
    brand: str | None
    pack_size: str | None
    purchase_date: str | None
    place: str | None


@dataclass(frozen=True, slots=True)
class SubSample:
    """One sub-sample row from a report's edible-portion table.

    weight_g is the report's average weight of one item in this sub-sample
    (each sub-sample is itself several items; see the composite's
    preparation_note). None where the report prints N/A.
    """
    number: str
    weight_g: float | None
    edible_portion: float | None    # set only when the composite's edible portion reconciled
    row_text: str                   # the table row exactly as extracted
    purchase: PurchaseRecord | None


@dataclass(frozen=True, slots=True)
class SampleComposite:
    """A composite food and the real retail sub-samples it was built from."""
    composite_number: str
    food_name: str
    preparation_note: str           # the report's own paragraph on how items were sampled
    subsamples: tuple[SubSample, ...]
    release: DatasetRelease


@dataclass(frozen=True, slots=True)
class PortionObservation:
    """A unit weight with its sample: never a bare number."""
    composite: SampleComposite
    description: str                # the report's own wording, e.g. "Average weight of whole banana"
    grams: float                    # mean of the sub-sample weights
    basis: str                      # weighed_sample_mean
    sample_size: int                # sub-samples with a weight
    min_g: float
    max_g: float
    mean_g: float
    sd_g: float | None              # sample standard deviation; None when n < 2
    stated_mean_g: float            # the report's own stated average, reconciled within 0.1 g
    edible_portion_mean: float | None
    edible_portion_min: float | None
    edible_portion_max: float | None
    edible_portion_n: int | None
    stated_edible_portion: float | None
    period_start: str               # earliest purchase date, ISO 8601
    period_end: str                 # latest purchase date, ISO 8601
    release: DatasetRelease
