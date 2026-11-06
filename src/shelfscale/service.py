"""Assessment service: NPM 2004/05 (in force), NPM 2018 (shadow) and traffic lights.

Two layers:

- ``assess_values`` assesses nutrient values that are already per 100 g.
  It is the one place scores and colours are computed, for caller-supplied
  values and for values ShelfScale looks up itself.
- ``assess_product`` and ``assess_bulk`` take caller-supplied payloads,
  validate and convert them, and call ``assess_values``. ShelfScale does not
  verify caller-supplied values, and every response says so.
"""

from __future__ import annotations

from typing import Any, Iterable

from .validation import number
from .npm import calculate_npm
from . import laws
from .npm2018 import MODEL_ID as NPM2018_ID, calculate_npm2018
from .traffic_lights import traffic_lights

MODEL_ID = "uk-npm-2004/05"
MAX_BULK_ITEMS = 1000
# The guidance scores food and drink alike on 100 g. Per-100 ml inputs are
# converted, never relabelled: value per 100 g = value per 100 ml / specific
# gravity (g/ml). See docs/API.md, "Scoring basis", for why this divides
# where the guidance's worked examples 2 and 6 multiply.
SCORING_BASIS = "per_100g"
INPUT_BASES = ("per_100g", "per_100ml")
_PER_AMOUNT_FIELDS = (
    "energy_kj", "fat_g", "saturated_fat_g", "total_sugars_g", "free_sugars_g", "protein_g",
    "sodium_mg", "salt_g", "fibre_nsp_g", "fibre_aoac_g",
)
_REQUIRED_NUTRIENTS = (
    "energy_kj",
    "saturated_fat_g",
    "total_sugars_g",
    "fruit_veg_nuts_percent",
    "protein_g",
)
_FIBRE_FIELDS = ("fibre_nsp_g", "fibre_aoac_g")
_NPM_FIELDS = (
    "energy_kj", "saturated_fat_g", "total_sugars_g", "fruit_veg_nuts_percent",
    "protein_g", "sodium_mg", "salt_g", "fibre_nsp_g", "fibre_aoac_g",
)


def _salt_g(values: dict[str, float]) -> float:
    return values["salt_g"] if "salt_g" in values else values["sodium_mg"] / 400.0


def _traffic_light_inputs(values: dict[str, float]) -> dict[str, float | None]:
    return {
        "fat": values.get("fat_g"),
        "saturates": values["saturated_fat_g"],
        "sugars": values["total_sugars_g"],
        "salt": _salt_g(values),
    }


def npm2018_block(
    values: dict[str, float],
    *,
    is_drink: bool,
    labels: dict[str, str] | None = None,
    not_applicable: str | None = None,
) -> dict[str, Any]:
    """The NPM 2018 shadow-model result for per-100 g values, or why there is none.

    Free sugars are never taken from total sugars; AOAC fibre is never
    derived from NSP. ``labels`` names where each input came from
    (default: caller_supplied).
    """
    labels = labels or {}
    block: dict[str, Any] = {"model": NPM2018_ID, "status": laws.status_text(NPM2018_ID),
                             "law": laws.label(NPM2018_ID)}
    if not_applicable:
        return {**block, "applicable": False, "scorable": False, "reason": not_applicable}
    inputs: dict[str, Any] = {}
    missing: list[str] = []

    def take(name: str, value: float | None, source: str, why_missing: str) -> None:
        if value is None:
            missing.append(f"{name} ({why_missing})")
        inputs[name] = {"value": value, "source": source if value is not None else "not available"}

    for name in ("energy_kj", "saturated_fat_g", "protein_g"):
        take(name, values.get(name), labels.get(name, "caller_supplied"), "not available")
    take("free_sugars_g", values.get("free_sugars_g"), labels.get("free_sugars_g", "caller_supplied"),
         "NPM 2018 scores free sugars; total sugars are never used in their place")
    if "salt_g" in values:
        take("salt_g", values["salt_g"], labels.get("salt_g", "caller_supplied"), "")
    elif "sodium_mg" in values:
        take("salt_g", values["sodium_mg"] / 400.0,
             f"from sodium_mg ({labels.get('sodium_mg', 'caller_supplied')}): salt = sodium x 2.5", "")
    else:
        take("salt_g", None, "", "not available")
    if "fibre_aoac_g" in values:
        take("fibre_aoac_g", values["fibre_aoac_g"], labels.get("fibre_aoac_g", "caller_supplied"), "")
    else:
        take("fibre_aoac_g", None, "",
             "NPM 2018 uses AOAC fibre; only NSP is available and the guidance names no conversion factor"
             if "fibre_nsp_g" in values else "not available")
    if "fvns_g" in values:
        take("fvns_g", values["fvns_g"], labels.get("fvns_g", "caller_supplied"), "")
    elif "fruit_veg_nuts_percent" in values:
        take("fvns_g", values["fruit_veg_nuts_percent"],
             f"from fruit_veg_nuts_percent ({labels.get('fruit_veg_nuts_percent', 'caller_supplied')}); "
             "2004/05 definition, which does not count seeds; send fvns_g to be exact", "")
    else:
        take("fvns_g", None, "", "not available")

    block["inputs"] = inputs
    if missing:
        return {**block, "applicable": True, "scorable": False, "missing_inputs": missing}
    result = calculate_npm2018(is_drink=is_drink, **{k: v["value"] for k, v in inputs.items()})
    return {
        **block,
        "applicable": True,
        "scorable": True,
        "score": result.score,
        "less_healthy": result.less_healthy,
        "a_points": result.a_points,
        "c_points": result.c_points,
        "total_a": result.total_a,
        "total_c": result.total_c,
        "protein_counted": result.protein_counted,
        "fibre_method": "aoac",
    }


def npm0405_block(values: dict[str, float], *, is_drink: bool) -> dict[str, Any]:
    npm = calculate_npm(is_drink=is_drink, **{k: v for k, v in values.items() if k in _NPM_FIELDS})
    return {
        "model": MODEL_ID,
        "status": laws.status_text(MODEL_ID),
        "law": laws.label(MODEL_ID),
        "scorable": True,
        "score": npm.score,
        "less_healthy": npm.less_healthy,
        "a_points": npm.a_points,
        "c_points": npm.c_points,
        "total_a": npm.total_a,
        "total_c": npm.total_c,
        "protein_counted": npm.protein_counted,
        "fibre_method": npm.fibre_method,
    }


def verdict_changes(models: dict[str, dict[str, Any]]) -> bool | None:
    """True or False when both models scored; None when either could not."""
    old, new = models[MODEL_ID], models[NPM2018_ID]
    if not (old.get("scorable") and new.get("scorable")):
        return None
    return old["less_healthy"] != new["less_healthy"]


def assess_values(
    *,
    per_100g: dict[str, float],
    is_drink: bool,
    per_100ml: dict[str, float] | None = None,
    portion_g: float | None = None,
    portion_ml: float | None = None,
    npm2018: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score per-100 g values under both models and colour them with traffic lights.

    ``per_100g`` needs the NPM 2004/05 inputs (exactly one of sodium_mg/salt_g
    and of fibre_nsp_g/fibre_aoac_g); it may carry fat_g (traffic lights) and
    free_sugars_g / fvns_g (NPM 2018). ``npm2018`` replaces the 2018 block
    when the caller has built it from other inputs (lookup mode). Drink colours need per-100 ml values;
    without them drink colours are reported as not assessed, never assumed.
    """
    old = npm0405_block(per_100g, is_drink=is_drink)
    new = npm2018 if npm2018 is not None else npm2018_block(per_100g, is_drink=is_drink)
    models = {MODEL_ID: old, NPM2018_ID: new}
    fibre_field = "fibre_nsp_g" if old["fibre_method"] == "nsp" else "fibre_aoac_g"

    if not is_drink:
        lights = traffic_lights(is_drink=False, per_100=_traffic_light_inputs(per_100g), portion=portion_g)
    elif per_100ml is not None:
        lights = traffic_lights(is_drink=True, per_100=_traffic_light_inputs(per_100ml), portion=portion_ml)
    else:
        lights = {
            "scheme": "uk-fop-2016",
            "basis": "per_100ml",
            "product_type": "drink",
            "colours": None,
            "not_assessed": (
                "Drink traffic lights are assessed per 100 ml (FoP guidance, Table 3). "
                "These values are per 100 g; supply basis 'per_100ml' with specific_gravity."
            ),
        }

    result: dict[str, Any] = {
        "basis": SCORING_BASIS,
        "models": models,
        "verdict_changes_under_2018": verdict_changes(models),
        "traffic_lights": lights,
    }
    if portion_g is not None:
        factor = portion_g / 100.0
        per_portion = {
            "portion_g": portion_g,
            "energy_kj": round(per_100g["energy_kj"] * factor, 1),
            "energy_kcal": round(per_100g["energy_kj"] * factor / 4.184, 1),
            "saturated_fat_g": round(per_100g["saturated_fat_g"] * factor, 2),
            "total_sugars_g": round(per_100g["total_sugars_g"] * factor, 2),
            "salt_g": round(_salt_g(per_100g) * factor, 3),
            fibre_field: round(per_100g[fibre_field] * factor, 2),
            "protein_g": round(per_100g["protein_g"] * factor, 2),
        }
        for optional in ("fat_g", "free_sugars_g"):
            if optional in per_100g:
                per_portion[optional] = round(per_100g[optional] * factor, 2)
        for name, value in per_portion.items():
            number(value, f"per_portion.{name}")
        result["per_portion"] = per_portion
    return result


def _require_number(nutrients: dict, name: str) -> float:
    value = nutrients.get(name)
    if value is None:
        raise ValueError(f"nutrients.{name} is required.")
    return number(value, f"nutrients.{name}")


def _positive(payload: dict, name: str) -> float | None:
    value = payload.get(name)
    if value is None:
        return None
    return number(value, name, positive=True)


def assess_product(payload: dict[str, Any]) -> dict[str, Any]:
    """Assess one product from caller-supplied nutrient values.

    Payload shape:
        {
          "id": "sku-123",                  # or "name"
          "is_drink": false,
          "basis": "per_100g",              # or "per_100ml" with
          "specific_gravity": 1.04,         #   a specific gravity (g/ml)
          "portion_g": 30,                  # optional: per-portion view; food traffic lights
          "portion_ml": 330,                # optional, drinks: per-portion traffic lights
          "nutrients": {
            "energy_kj": 1800, "fat_g": 9.0, "saturated_fat_g": 4.0,
            "total_sugars_g": 20,
            "sodium_mg": 300,               # or "salt_g": 0.75
            "fruit_veg_nuts_percent": 0, "protein_g": 6.0,
            "fibre_nsp_g": 1.6,             # or "fibre_aoac_g": 2.0
            "free_sugars_g": 12.0,          # optional; needed for the NPM 2018 shadow score
            "fvns_g": 0                     # optional; NPM 2018 fruit, veg, nuts and seeds
          }
        }
    """
    if not isinstance(payload, dict):
        raise ValueError("Product payload must be an object.")
    product_id = payload.get("id") or payload.get("name")
    if not isinstance(product_id, str) or not product_id.strip():
        raise ValueError("Product needs an 'id' or a 'name'.")
    basis = payload.get("basis", SCORING_BASIS)
    if basis not in INPUT_BASES:
        raise ValueError("basis must be 'per_100g' or 'per_100ml'.")
    gravity = None
    if basis == "per_100ml":
        if payload.get("specific_gravity") is None:
            raise ValueError(
                "basis 'per_100ml' needs specific_gravity (g/ml). NPM scores per "
                "100 g, and per-100 ml values cannot be converted without it."
            )
        gravity = number(payload["specific_gravity"], "specific_gravity", positive=True)
    elif payload.get("specific_gravity") is not None:
        raise ValueError("specific_gravity only applies with basis 'per_100ml'.")
    nutrients = payload.get("nutrients")
    if not isinstance(nutrients, dict):
        raise ValueError("Product needs a 'nutrients' object.")

    values = {name: _require_number(nutrients, name) for name in _REQUIRED_NUTRIENTS}
    for optional in ("sodium_mg", "salt_g", "fat_g", "free_sugars_g", "fvns_g"):
        if nutrients.get(optional) is not None:
            values[optional] = _require_number(nutrients, optional)
    fibre_given = [name for name in _FIBRE_FIELDS if nutrients.get(name) is not None]
    if len(fibre_given) != 1:
        raise ValueError(
            "Supply exactly one of nutrients.fibre_nsp_g or nutrients.fibre_aoac_g "
            "(NSP is preferred where known)."
        )
    values[fibre_given[0]] = _require_number(nutrients, fibre_given[0])

    is_drink = payload.get("is_drink", False)
    if not isinstance(is_drink, bool):
        raise ValueError("is_drink must be true or false (a JSON boolean).")
    portion_g = _positive(payload, "portion_g")
    portion_ml = _positive(payload, "portion_ml")
    if portion_ml is not None and not is_drink:
        raise ValueError("portion_ml applies to drinks only; use portion_g for food.")

    per_100ml = None
    conversion = None
    if gravity is not None:
        per_100ml = dict(values)
        for name in _PER_AMOUNT_FIELDS:
            if name in values:
                values[name] = number(values[name] / gravity, name)
        conversion = {
            "from_basis": "per_100ml",
            "to_basis": SCORING_BASIS,
            "specific_gravity": gravity,
            "rule": "value_per_100g = value_per_100ml / specific_gravity",
            "unchanged": [k for k in ("fruit_veg_nuts_percent", "fvns_g") if k in values],
            "values": {
                name: {"per_100ml": per_100ml[name], "per_100g": values[name]}
                for name in _PER_AMOUNT_FIELDS if name in values
            },
        }

    assessment = assess_values(
        per_100g=values,
        is_drink=is_drink,
        per_100ml=per_100ml if is_drink else None,
        portion_g=portion_g,
        portion_ml=portion_ml,
    )
    return {
        "id": product_id,
        **assessment,
        "input_conversion": conversion,
        "evidence_note": (
            "Score computed from caller-supplied nutrient values. "
            "ShelfScale has not verified these values."
        ),
    }


def run_bulk(payload: dict[str, Any], key: str, handle) -> tuple[list, list, int]:
    """Shared bulk rule: partial success, a per-row error list, a size limit."""
    if not isinstance(payload, dict):
        raise ValueError("Bulk payload must be an object.")
    items = payload.get(key)
    if not isinstance(items, list) or not items:
        raise ValueError(f"Bulk payload needs a non-empty '{key}' list.")
    if len(items) > MAX_BULK_ITEMS:
        raise ValueError(
            f"Bulk limit is {MAX_BULK_ITEMS} items per synchronous call. "
            "Split larger ranges into calls of at most 1000 items; asynchronous jobs are not implemented."
        )
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        item_id = (item.get("id") or item.get("name")) if isinstance(item, dict) else None
        try:
            results.append(handle(item))
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append({"index": index, "id": item_id, "error": str(exc)})
    return results, errors, len(items)


def assess_bulk(payload: dict[str, Any]) -> dict[str, Any]:
    """Assess many products in one call.

    Partial success is a rule, not an accident: a bad row is reported in
    ``errors`` and never blocks the rest of the range.
    """
    results, errors, received = run_bulk(payload, "products", assess_product)
    return {
        "models": [MODEL_ID, NPM2018_ID],
        "summary": {
            "received": received,
            "assessed": len(results),
            "failed": len(errors),
            **dual_summary([r["models"] for r in results],
                           [r["verdict_changes_under_2018"] for r in results]),
        },
        "results": results,
        "errors": errors,
    }


def dual_summary(models: list[dict[str, dict[str, Any]]], changes: list[bool | None]) -> dict[str, Any]:
    """Per-model counts for a bulk summary, and how many verdicts change under 2018."""
    return {
        "less_healthy": {
            model_id: sum(1 for m in models if m[model_id].get("scorable") and m[model_id]["less_healthy"])
            for model_id in (MODEL_ID, NPM2018_ID)
        },
        "scorable": {
            model_id: sum(1 for m in models if m[model_id].get("scorable"))
            for model_id in (MODEL_ID, NPM2018_ID)
        },
        "verdict_changes_under_2018": sum(1 for c in changes if c),
    }
