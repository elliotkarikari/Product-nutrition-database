"""Service-level lookup of CoFID 2021 foods (used by the HTTP lookup endpoints).

Neither CoFID food codes nor food names are unique in the 2021 dataset, so
a lookup always returns a list of matches. An empty list is a gap, reported
as a gap: nothing is filled from any other source.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .cofid import CoFIDImport, import_cofid
from .model import DatasetRelease, Food, NutrientObservation
from .overlays import import_overlays, apply_overlays


DATA_RELEASE = "uk-cofid-2021+milk-2022-23+beef-2024-v1"


@lru_cache(maxsize=1)
def cofid_release() -> CoFIDImport:
    """The verified CoFID 2021 import, built once per process (about 4 s)."""
    return import_cofid()


@lru_cache(maxsize=1)
def overlay_release():
    return import_overlays(cofid_release())


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, list[Food]], dict[str, list[Food]], dict[str, list[NutrientObservation]]]:
    data = cofid_release()
    by_code: dict[str, list[Food]] = {}
    by_name: dict[str, list[Food]] = {}
    for food in data.foods:
        by_code.setdefault(food.source_code, []).append(food)
        by_name.setdefault(food.name, []).append(food)
    by_food: dict[str, list[NutrientObservation]] = {}
    for observation in apply_overlays(data.observations, overlay_release().observations):
        by_food.setdefault(observation.food.food_id, []).append(observation)
    return by_code, by_name, by_food


def _release_dict(release: DatasetRelease) -> dict[str, str]:
    return {
        "source_id": release.source_id,
        "dataset": release.dataset,
        "edition": release.edition,
        "publisher": release.publisher,
        "url": release.url,
        "retrieved": release.retrieved,
        "sha256": release.sha256,
        "licence": release.licence,
        "attribution": release.attribution,
    }


def _observation_dict(observation: NutrientObservation) -> dict[str, Any]:
    definition = observation.definition
    return {
        "observation_id": observation.observation_id,
        "release": _release_dict(observation.release),
        "period_start": observation.period_start,
        "period_end": observation.period_end,
        "analysis_period": observation.analysis_period,
        "source_locator": observation.source_locator,
        "source_food": observation.source_food or observation.food.name,
        "confidence": observation.confidence,
        "supersedes": observation.supersedes,
        "superseded_by": observation.superseded_by,
        "nutrient_code": definition.code,
        "nutrient_label": definition.label,
        "unit": definition.unit,
        "method": definition.method,
        "value": observation.value,
        "value_text": observation.value_text,
        "value_kind": observation.value_kind,
        "basis": observation.basis,
        "state": observation.state,
        "value_method": observation.method,
        "status": observation.status,
        "source_id": observation.release.source_id,
        "edition": observation.release.edition,
        "food_code": observation.food.source_code,
        "table": definition.table,
    }


def _food_dict(food: Food, observations: list[NutrientObservation]) -> dict[str, Any]:
    return {
        "food_id": food.food_id,
        "food_code": food.source_code,
        "name": food.name,
        "description": food.description,
        "group": food.group,
        "previous_codes": food.previous_codes,
        "main_data_reference": food.main_data_reference,
        "footnote": food.footnote,
        "source_row": food.source_row,
        "observations": [_observation_dict(o) for o in observations],
    }


def lookup_cofid(*, code: str | None = None, name: str | None = None) -> dict[str, Any]:
    """Find CoFID 2021 foods by exact food code or exact food name.

    Exactly one of ``code`` and ``name`` must be given. Returns every match
    with all its observations and the release they came from.
    """
    if (code is None) == (name is None):
        raise ValueError("Supply exactly one of code or name.")
    by_code, by_name, by_food = _index()
    query = {"code": code} if code is not None else {"name": name}
    foods = by_code.get(code, []) if code is not None else by_name.get(name, [])

    if not foods:
        note = "No CoFID 2021 food matches. This is a gap; no other source is used to fill it."
    elif len(foods) > 1:
        what = "food code" if code is not None else "food name"
        note = (
            f"{len(foods)} CoFID 2021 foods share this {what}. They are different "
            "foods with different values; choose by food_id."
        )
    else:
        note = None

    return {
        "query": query,
        "release": _release_dict(cofid_release().release),
        "data_release": DATA_RELEASE,
        "matches": [_food_dict(food, by_food.get(food.food_id, [])) for food in foods],
        "note": note,
    }
