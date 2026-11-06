"""Score a producer's whole range from the page: one row per product.

Each row is resolved, then scored by the same functions as the keyed API:

- the user's own per-100 g label figures -> service.assess_product
  (supplied mode; the response says ShelfScale has not verified them);
- a CoFID code -> cofid_assess.lookup_and_assess;
- a CoFID name, exactly (case and spacing ignored) -> lookup;
- any other name -> a confirmed match from the matching assistant, if the
  user has confirmed one for that exact name; otherwise a gap.

A row that cannot be resolved is a gap with its reason and the closest
deterministic candidates. Nothing is guessed into a score. Rows keep their
order index; the response sorts verdict flips to the top.
"""

from __future__ import annotations

import re
from typing import Any

from . import laws
from .as_sold import describe
from .cofid_assess import lookup_and_assess
from .lookup import DATA_RELEASE
from .matching import confirmation, retrieve
from .npm2018 import MODEL_ID as NPM2018_ID
from .service import MODEL_ID, assess_product, dual_summary
from .ui_api import foods_by_id, source_card
from .validation import number

MAX_ROWS = 200
NUTRIENT_FIELDS = ("energy_kj", "fat_g", "saturated_fat_g", "total_sugars_g", "free_sugars_g",
                   "sodium_mg", "salt_g", "protein_g", "fibre_nsp_g", "fibre_aoac_g",
                   "fruit_veg_nuts_percent", "fvns_g")

CORE_FIELDS = ("energy_kj", "fat_g", "saturated_fat_g", "total_sugars_g", "sodium_mg", "salt_g",
               "protein_g", "fibre_nsp_g", "fibre_aoac_g")


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().casefold())


def _by_name() -> dict[str, list]:
    out: dict[str, list] = {}
    for food in foods_by_id().values():
        out.setdefault(_key(food.name), []).append(food)
    return out


def _optional(row: dict, name: str, maximum: float | None = None, positive: bool = False) -> float | None:
    value = row.get(name)
    if value in (None, ""):
        return None
    return number(value, name, maximum=maximum, positive=positive)


def _models(models: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for model_id in (MODEL_ID, NPM2018_ID):
        m = models[model_id]
        out[model_id] = {
            "law": laws.label(model_id),
            "scorable": bool(m.get("scorable")),
            "score": m.get("score"),
            "less_healthy": m.get("less_healthy"),
            "missing": m.get("missing_inputs") or ([m["reason"]] if m.get("reason") else []),
        }
    return out


def _sources(food: dict[str, Any]) -> list[str]:
    labels = []
    for o in food["observations"]:
        if o["status"] == "current" and o["nutrient_code"] in ("KJ", "FAT", "SATFOD", "TOTSUG", "NA", "PROT",
                                                                 "ENGFIB", "AOACFIB"):
            label = source_card(o)["label"]
            if label not in labels:
                labels.append(label)
    return labels


def _lookup_row(index: int, row: dict, food_id: str, basis: str, extra: dict) -> dict[str, Any]:
    food = foods_by_id()[food_id]
    payload = {"code": food.source_code, **{k: v for k, v in extra.items() if v is not None}}
    result = lookup_and_assess(payload)
    match = next(m for m in result["matches"] if m["food_id"] == food_id)
    a = match["assessment"]
    inputs = a["models"][MODEL_ID].get("inputs") or {}
    value = lambda n: (inputs.get(n) or {}).get("value")  # noqa: E731
    sodium = value("sodium_mg")
    sold = describe(food_id, food.source_code,
                    {"fat": value("fat_g"), "saturates": value("saturated_fat_g"),
                     "sugars": value("total_sugars_g"), "energy_kj": value("energy_kj"),
                     "salt": None if sodium is None else sodium / 400.0},
                    pack_g=extra.get("pack_g"))
    return {
        "index": index, "status": "scored", "input": row.get("name") or row.get("code"),
        "resolved": {"food_id": food_id, "code": food.source_code, "name": food.name, "basis": basis},
        "models": _models(a["models"]),
        "verdict_changes_under_2018": a["verdict_changes_under_2018"],
        "per_100g": {k: value(k) for k in ("energy_kj", "fat_g", "saturated_fat_g", "total_sugars_g",
                                           "sodium_mg", "protein_g")},
        "sources": _sources(match),
        "caller_supplied": {k: v for k, v in extra.items() if v is not None and k != "pack_g"},
        "as_sold": {"kind": sold["kind"], "unit": sold["unit"], "band": sold.get("band"),
                    "proposed_units": len(sold["proposed_units"]),
                    "sale_format": (sold["sale"] or {}).get("sale_format"), "note": sold.get("note")},
    }


def _supplied_row(index: int, row: dict) -> dict[str, Any]:
    nutrients = {k: row[k] for k in NUTRIENT_FIELDS if row.get(k) not in (None, "")}
    payload = {"id": row.get("name") or f"row {index + 1}", "nutrients": nutrients,
               "is_drink": bool(row.get("is_drink"))}
    result = assess_product(payload)
    return {
        "index": index, "status": "scored", "input": payload["id"],
        "resolved": {"food_id": None, "code": None, "name": payload["id"], "basis": "your label figures"},
        "models": _models(result["models"]),
        "verdict_changes_under_2018": result["verdict_changes_under_2018"],
        "per_100g": {k: nutrients.get(k) for k in ("energy_kj", "fat_g", "saturated_fat_g", "total_sugars_g",
                                                   "sodium_mg", "protein_g")},
        "sources": ["Your label figures (not verified by ShelfScale)"],
        "caller_supplied": nutrients,
        "as_sold": {"kind": "packaged" if row.get("pack_g") else "unknown", "unit": None, "band": None,
                    "sale_format": None, "note": None},
    }


def _resolve(index: int, row: Any, by_name: dict, confirmed: dict[str, dict]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("Each row must be an object.")
    if any(row.get(k) not in (None, "") for k in CORE_FIELDS):
        return _supplied_row(index, row)
    extra = {"free_sugars_g": _optional(row, "free_sugars_g", 100),
             "fvn_percent": _optional(row, "fvn_percent", 100),
             "pack_g": _optional(row, "pack_g", 100000, positive=True)}
    code = (row.get("code") or "").strip() if isinstance(row.get("code"), str) else ""
    name = " ".join(row["name"].split()) if isinstance(row.get("name"), str) else ""
    if code:
        foods = [f for f in foods_by_id().values() if f.source_code == code]
        if len(foods) == 1:
            return _lookup_row(index, row, foods[0].food_id, "CoFID code", extra)
        reason = "No CoFID 2021 food has this code." if not foods else \
            f"{len(foods)} CoFID foods share this code; give the name instead."
        return {"index": index, "status": "gap", "input": code, "reason": reason, "candidates": []}
    if not name:
        raise ValueError("Give a CoFID name or code, or your own per-100 g figures.")
    foods = by_name.get(_key(name), [])
    if len(foods) == 1:
        return _lookup_row(index, row, foods[0].food_id, "exact CoFID name", extra)
    if _key(name) in confirmed:
        record = confirmed[_key(name)]
        return _lookup_row(index, row, record["food_id"], record["basis"], extra)
    reason = ("No CoFID 2021 food has exactly this name. Use the matching assistant to confirm one, "
              "or give your own label figures.") if not foods else \
        f"{len(foods)} CoFID foods share this name; give the code instead."
    return {"index": index, "status": "gap", "input": name, "reason": reason,
            "candidates": [{k: c[k] for k in ("food_id", "code", "name", "retrieval_score")}
                           for c in retrieve(name, 3)]}


def run(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Bulk payload must be an object.")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Give at least one row.")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"The page scores up to {MAX_ROWS} rows at a time. Split the list, "
                         "or use the keyed bulk API for larger ranges.")
    confirmed = {}
    for item in payload.get("confirmed") or []:
        record = confirmation(item)
        confirmed[_key(record["query"])] = record
    by_name = _by_name()
    scored, gaps, errors = [], [], []
    for index, row in enumerate(rows):
        try:
            result = _resolve(index, row, by_name, confirmed)
        except (ValueError, TypeError) as exc:
            errors.append({"index": index, "input": (row.get("name") or row.get("code")) if isinstance(row, dict)
                           else None, "error": str(exc)})
            continue
        (scored if result["status"] == "scored" else gaps).append(result)

    def order(r):
        old, new = r["models"][MODEL_ID], r["models"][NPM2018_ID]
        return (r["verdict_changes_under_2018"] is not True,
                not (old["less_healthy"] or new["less_healthy"]), r["index"])
    scored.sort(key=order)
    return {
        "mode": "bulk",
        "data_release": DATA_RELEASE,
        "laws": [laws.label(m) for m in (MODEL_ID, NPM2018_ID)],
        "summary": {"received": len(rows), "scored": len(scored), "gaps": len(gaps), "errors": len(errors),
                    "loose": sum(1 for r in scored if r["as_sold"]["kind"] == "loose"),
                    **dual_summary([{k: {"scorable": v["scorable"], "less_healthy": v["less_healthy"]}
                                     for k, v in r["models"].items()} for r in scored],
                                   [r["verdict_changes_under_2018"] for r in scored])},
        "rows": scored, "gaps": gaps, "errors": errors,
        "rule": ("Rows are scored by the same engines as the API. A row that cannot be resolved is a gap "
                 "with its reason; nothing is guessed into a score. NPM 2018 needs your free sugars "
                 "figure for each row; total sugars are never used instead."),
    }
