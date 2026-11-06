"""Browser-facing data for the ShelfScale page.

The page calls these through same-origin routes on the service (see api.py).
They run in-process on the same functions the authenticated API uses, so
the browser never holds the API key and no score is computed anywhere else.

Three things live here and nowhere else:

- search: names and codes only, to find a food_id;
- one-tap portions: weights linked to a CoFID food by the existing exact-name
  rule (FPS already; the sampling reports by the same rule), never fuzzy;
- provenance cards: a plain-language summary of where each value came from,
  built from the observation's own release record.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from .cofid_assess import lookup_and_assess
from .fps import import_fps
from .lookup import DATA_RELEASE, _index, cofid_release
from .model import Food
from .validation import number
from .as_sold import describe

MAX_RESULTS = 25
MAX_QUERY = 80
COFID_SOURCE = "uk-cofid-2021"

# A name that says the food is sold as a powder or concentrate. This only
# raises a flag in the page; it never changes a value or a score.
_AS_SOLD_WORDS = re.compile(r"\b(powder|powdered|granules|concentrate|concentrated|undiluted)\b",
                            re.IGNORECASE)

# Values the food page shows, in label order, with the CoFID code behind each.
PANEL = (
    ("energy_kj", "Energy", "KJ", "kJ"),
    ("energy_kcal", "Energy", "KCALS", "kcal"),
    ("fat_g", "Fat", "FAT", "g"),
    ("saturated_fat_g", "of which saturates", "SATFOD", "g"),
    ("carbohydrate_g", "Carbohydrate", "CHO", "g"),
    ("total_sugars_g", "of which total sugars", "TOTSUG", "g"),
    ("fibre_nsp_g", "Fibre (NSP)", "ENGFIB", "g"),
    ("fibre_aoac_g", "Fibre (AOAC)", "AOACFIB", "g"),
    ("protein_g", "Protein", "PROT", "g"),
    ("sodium_mg", "Sodium", "NA", "mg"),
)


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().casefold())


@lru_cache(maxsize=1)
def foods_by_id() -> dict[str, Food]:
    return {food.food_id: food for food in cofid_release().foods}


@lru_cache(maxsize=1)
def _overlay_foods() -> frozenset[str]:
    by_food = _index()[2]
    return frozenset(fid for fid, obs in by_food.items()
                     if any(o.release.source_id != COFID_SOURCE and o.status == "current" for o in obs))


@lru_cache(maxsize=1)
def _portions() -> dict[str, tuple[dict[str, Any], ...]]:
    """One-tap and listed portions per CoFID food_id."""
    foods = cofid_release().foods
    by_name: dict[str, list[Food]] = {}
    for food in foods:
        by_name.setdefault(_key(food.name), []).append(food)
    out: dict[str, list[dict[str, Any]]] = {}

    fps = import_fps(foods)
    for p in fps.portions:
        if not p.cofid_food_id:
            continue
        label = ", ".join(x for x in (p.brand, p.portion_description) if x) or "typical portion"
        out.setdefault(p.cofid_food_id, []).append({
            "label": label,
            "grams": p.grams,
            "tappable": p.grams is not None,
            "weight_text": p.weight_text,
            "basis": "typical portion as printed",
            "kind": p.value_kind,
            "source": {
                "label": "Food Portion Sizes 2002",
                "citation": p.release.attribution,
                "rights": p.release.licence,
                "detail": f"Row {p.source_row}, {p.food_name}; matched to CoFID by exact food name.",
                "note": None if p.grams is not None else
                        "Not offered as a one-tap weight: the book gives "
                        + ("a volume, and no density is assumed." if p.value_kind == "volume_ml"
                           else "more than one weight, and none is chosen."),
            },
        })

    from .as_sold import sample_units
    for food_id, units in sample_units().items():
        for u in units:
            if not u["applied"]:
                continue
            out.setdefault(food_id, []).append({
                "label": u["label"], "grams": u["typical_g"], "tappable": True,
                "weight_text": f"{u['typical_g']:.1f} g", "basis": u["basis"], "kind": "sample_mean",
                "range_g": [u["low_g"], u["high_g"]], "n": u["n"],
                "source": {**u["source"], "detail": f"{u['source']['detail']} {u['spread']}", "note": None},
            })
    return {k: tuple(v) for k, v in out.items()}


def portions_for(food_id: str) -> list[dict[str, Any]]:
    return list(_portions().get(food_id, ()))


def search(query: str) -> dict[str, Any]:
    if not isinstance(query, str):
        raise ValueError("Search needs text.")
    q = " ".join(query.split())
    if len(q) < 2:
        return {"query": q, "results": [], "note": "Type at least two letters."}
    if len(q) > MAX_QUERY:
        raise ValueError(f"Search text is limited to {MAX_QUERY} characters.")
    tokens = q.casefold().split()
    overlays = _overlay_foods()
    portions = _portions()
    hits = []
    for food in foods_by_id().values():
        name = food.name.casefold()
        if food.source_code.casefold() == q.casefold() or all(t in name for t in tokens):
            rank = (food.source_code.casefold() != q.casefold(), not name.startswith(tokens[0]),
                    len(name), name)
            hits.append((rank, food))
    hits.sort(key=lambda pair: pair[0])
    results = [{
        "food_id": food.food_id,
        "code": food.source_code,
        "name": food.name,
        "group": food.group,
        "overlay": food.food_id in overlays,
        "portions": sum(1 for p in portions.get(food.food_id, ()) if p["tappable"]),
    } for _, food in hits[:MAX_RESULTS]]
    note = None
    if not hits:
        note = "No CoFID 2021 food matches. This is a gap; nothing else is searched to fill it."
    elif len(hits) > MAX_RESULTS:
        note = f"Showing {MAX_RESULTS} of {len(hits)} matches. Add a word to narrow it."
    return {"query": q, "data_release": DATA_RELEASE, "total": len(hits),
            "results": results, "note": note}


def source_card(observation: dict[str, Any]) -> dict[str, Any]:
    """Where one value came from, in words, from its observation record."""
    release = observation["release"]
    official = release["source_id"] != COFID_SOURCE
    if official:
        short = "Milk overlay" if "milk" in release["source_id"] else (
            "Beef overlay" if "beef" in release["source_id"] else release["dataset"])
        period = observation.get("analysis_period") or observation.get("period_start")
        label = f"{short} {period}" if period else short
    else:
        label = "CoFID 2021"
    return {
        "label": label,
        "dataset": release["dataset"],
        "edition": release["edition"],
        "publisher": release["publisher"],
        "rights": release["licence"],
        "citation": release["attribution"],
        "period": observation.get("analysis_period"),
        "locator": observation.get("source_locator"),
        "observation_id": observation["observation_id"],
        "supersedes": observation.get("supersedes"),
        "url": release["url"],
    }


def as_sold_flag(name: str) -> dict[str, str] | None:
    if not _AS_SOLD_WORDS.search(name):
        return None
    return {
        "flag": "as_sold",
        "text": ("CoFID lists this food as sold (a powder or concentrate). The NPM guidance "
                 "scores such products as made up to the maker's instructions; ShelfScale "
                 "has not reconstituted it, so the score shown is for the product as sold. "
                 "In a recipe, weigh it as sold and add any water or milk as its own ingredient."),
        "detected_by": "the food's CoFID name",
    }


def _optional(params: dict[str, str], name: str, *, maximum: float | None = None,
              positive: bool = False) -> float | None:
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number.") from None
    return number(value, name, positive=positive, maximum=maximum)


def food(food_id: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    params = params or {}
    record = foods_by_id().get(food_id)
    if record is None:
        raise LookupError("No CoFID 2021 food has that id.")
    payload: dict[str, Any] = {"code": record.source_code}
    portion_g = _optional(params, "portion_g", positive=True, maximum=100000)
    free_sugars = _optional(params, "free_sugars_g", maximum=100)
    fvn = _optional(params, "fvn_percent", maximum=100)
    if fvn is not None:
        payload["fvn_percent"] = fvn
    if portion_g is not None:
        payload["portion_g"] = portion_g
    if free_sugars is not None:
        payload["free_sugars_g"] = free_sugars
    result = lookup_and_assess(payload)
    match = next(m for m in result["matches"] if m["food_id"] == food_id)
    current = {o["nutrient_code"]: o for o in match["observations"] if o["status"] == "current"}
    panel = []
    for key, label, code, unit in PANEL:
        o = current.get(code)
        panel.append({
            "key": key, "label": label, "code": code, "unit": unit,
            "value": o["value"] if o else None,
            "value_kind": o["value_kind"] if o else "not_given",
            "value_text": o["value_text"] if o else None,
            "basis": o["basis"] if o else None,
            "source": source_card(o) if o else None,
        })
    salt = current.get("NA")
    pack_g = _optional(params, "pack_g", positive=True, maximum=100000)
    confirmed = frozenset(k for k in (params.get("unit") or "").split(",") if k)
    inputs = match["assessment"]["models"]["uk-npm-2004/05"].get("inputs") or {}
    value = lambda name: (inputs.get(name) or {}).get("value")  # noqa: E731
    sodium = value("sodium_mg")
    per_100 = {"fat": value("fat_g"), "saturates": value("saturated_fat_g"),
               "sugars": value("total_sugars_g"), "salt": None if sodium is None else sodium / 400.0,
               "energy_kj": value("energy_kj")}
    sold = describe(food_id, record.source_code, per_100, pack_g=pack_g, confirmed=confirmed)
    shown = {code for _, _, code, _ in PANEL}
    overlay_values = [{
        "code": o["nutrient_code"], "label": o["nutrient_label"], "unit": o["unit"],
        "value": o["value"], "value_kind": o["value_kind"], "value_text": o["value_text"],
        "basis": o["basis"], "source": source_card(o),
    } for o in current.values()
        if o["source_id"] != COFID_SOURCE and o["nutrient_code"] not in shown
        and ":" not in o["nutrient_code"]]
    return {
        "food_id": food_id,
        "code": record.source_code,
        "name": record.name,
        "description": record.description,
        "group": record.group,
        "data_release": DATA_RELEASE,
        "panel_basis": "per_100g",
        "panel": panel,
        "overlay_values": overlay_values,
        "as_sold": sold,
        "salt_from_sodium": {"rule": "salt = sodium x 2.5", "source": source_card(salt)} if salt else None,
        "portions": portions_for(food_id),
        "portion_g": portion_g,
        "caller_supplied": {k: v for k, v in (("fvn_percent", fvn), ("free_sugars_g", free_sugars))
                            if v is not None},
        "powder": as_sold_flag(record.name),
        "assessment": match["assessment"],
        "evidence_note": result["evidence_note"],
    }
