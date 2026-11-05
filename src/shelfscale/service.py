"""Assessment service: single and bulk UK NPM 2004/05 scoring.

The service scores nutrient values supplied by the caller. It does not look
values up and it does not verify them: where the values came from is the
caller's evidence, and every response says so. Database-backed assessment
( values resolved from ShelfScale's own provenance-carrying data) is a
separate layer specified in docs/API.md.
"""

from __future__ import annotations

from typing import Any, Iterable

from .npm import calculate_npm

MODEL_ID = "uk-npm-2004/05"
MAX_BULK_ITEMS = 1000
# The guidance scores food and drink alike on 100 g. Per-100 ml inputs are
# converted, never relabelled: value per 100 g = value per 100 ml / specific
# gravity (g/ml). See docs/API.md, "Scoring basis", for why this divides
# where the guidance's worked examples 2 and 6 multiply.
SCORING_BASIS = "per_100g"
INPUT_BASES = ("per_100g", "per_100ml")
_PER_AMOUNT_FIELDS = (
    "energy_kj", "saturated_fat_g", "total_sugars_g", "protein_g",
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


def _require_number(nutrients: dict, name: str) -> float:
    value = nutrients.get(name)
    if value is None:
        raise ValueError(f"nutrients.{name} is required.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"nutrients.{name} must be a number.")
    return float(value)


def assess_product(payload: dict[str, Any]) -> dict[str, Any]:
    """Assess one product from its per-100 g nutrient values (food and drink).

    Payload shape:
        {
          "id": "sku-123",                  # or "name"
          "is_drink": false,
          "basis": "per_100g",              # optional; or "per_100ml" with
          "specific_gravity": 1.04,         #   a specific gravity (g/ml)
          "portion_g": 30,                  # optional, for per-portion view
          "nutrients": {
            "energy_kj": 1800, "saturated_fat_g": 4.0, "total_sugars_g": 20,
            "sodium_mg": 300,               # or "salt_g": 0.75
            "fruit_veg_nuts_percent": 0, "protein_g": 6.0,
            "fibre_nsp_g": 1.6              # or "fibre_aoac_g": 2.0
          }
        }
    """
    if not isinstance(payload, dict):
        raise ValueError("Product payload must be an object.")
    product_id = payload.get("id") or payload.get("name")
    if not product_id:
        raise ValueError("Product needs an 'id' or a 'name'.")
    basis = payload.get("basis", SCORING_BASIS)
    if basis not in INPUT_BASES:
        raise ValueError("basis must be 'per_100g' or 'per_100ml'.")
    gravity = None
    if basis == "per_100ml":
        gravity = payload.get("specific_gravity")
        if gravity is None:
            raise ValueError(
                "basis 'per_100ml' needs specific_gravity (g/ml). NPM scores per "
                "100 g, and per-100 ml values cannot be converted without it."
            )
        if isinstance(gravity, bool) or not isinstance(gravity, (int, float)) or gravity <= 0:
            raise ValueError("specific_gravity must be a positive number (g/ml).")
        gravity = float(gravity)
    elif payload.get("specific_gravity") is not None:
        raise ValueError("specific_gravity only applies with basis 'per_100ml'.")
    nutrients = payload.get("nutrients")
    if not isinstance(nutrients, dict):
        raise ValueError("Product needs a 'nutrients' object.")

    values = {name: _require_number(nutrients, name) for name in _REQUIRED_NUTRIENTS}
    sodium_mg = nutrients.get("sodium_mg")
    salt_g = nutrients.get("salt_g")
    if sodium_mg is not None:
        values["sodium_mg"] = _require_number(nutrients, "sodium_mg")
    if salt_g is not None:
        values["salt_g"] = _require_number(nutrients, "salt_g")
    fibre_given = [name for name in _FIBRE_FIELDS if nutrients.get(name) is not None]
    if len(fibre_given) != 1:
        raise ValueError(
            "Supply exactly one of nutrients.fibre_nsp_g or nutrients.fibre_aoac_g "
            "(NSP is preferred where known)."
        )
    fibre_field = fibre_given[0]
    values[fibre_field] = _require_number(nutrients, fibre_field)

    conversion = None
    if gravity is not None:
        supplied = dict(values)
        for name in _PER_AMOUNT_FIELDS:
            if name in values:
                values[name] = values[name] / gravity
        conversion = {
            "from_basis": "per_100ml",
            "to_basis": SCORING_BASIS,
            "specific_gravity": gravity,
            "rule": "value_per_100g = value_per_100ml / specific_gravity",
            "unchanged": ["fruit_veg_nuts_percent"],
            "values": {
                name: {"per_100ml": supplied[name], "per_100g": values[name]}
                for name in _PER_AMOUNT_FIELDS if name in values
            },
        }

    is_drink = payload.get("is_drink", False)
    if not isinstance(is_drink, bool):
        raise ValueError("is_drink must be true or false (a JSON boolean).")
    result = calculate_npm(is_drink=is_drink, **values)

    response: dict[str, Any] = {
        "id": product_id,
        "model": MODEL_ID,
        "basis": SCORING_BASIS,
        "score": result.score,
        "less_healthy": result.less_healthy,
        "a_points": result.a_points,
        "c_points": result.c_points,
        "total_a": result.total_a,
        "total_c": result.total_c,
        "protein_counted": result.protein_counted,
        "fibre_method": result.fibre_method,
        "input_conversion": conversion,
        "evidence_note": (
            "Score computed from caller-supplied nutrient values. "
            "ShelfScale has not verified these values."
        ),
    }

    portion_g = payload.get("portion_g")
    if portion_g is not None:
        if isinstance(portion_g, bool) or not isinstance(portion_g, (int, float)) or portion_g <= 0:
            raise ValueError("portion_g must be a positive number.")
        factor = float(portion_g) / 100.0
        sodium_for_portion = values.get("sodium_mg")
        if sodium_for_portion is None:
            sodium_for_portion = values["salt_g"] * 400.0
        response["per_portion"] = {
            "portion_g": float(portion_g),
            "energy_kj": round(values["energy_kj"] * factor, 1),
            "energy_kcal": round(values["energy_kj"] * factor / 4.184, 1),
            "saturated_fat_g": round(values["saturated_fat_g"] * factor, 2),
            "total_sugars_g": round(values["total_sugars_g"] * factor, 2),
            "salt_g": round(sodium_for_portion / 400.0 * factor, 3),
            fibre_field: round(values[fibre_field] * factor, 2),
            "protein_g": round(values["protein_g"] * factor, 2),
        }
    return response


def assess_bulk(payload: dict[str, Any]) -> dict[str, Any]:
    """Assess many products in one call.

    Partial success is a rule, not an accident: a bad row is reported in
    ``errors`` and never blocks the rest of the range. That is what a
    retailer or university scoring thousands of products needs.
    """
    if not isinstance(payload, dict):
        raise ValueError("Bulk payload must be an object.")
    products: Iterable[Any] = payload.get("products") or []
    products = list(products)
    if not products:
        raise ValueError("Bulk payload needs a non-empty 'products' list.")
    if len(products) > MAX_BULK_ITEMS:
        raise ValueError(
            f"Bulk limit is {MAX_BULK_ITEMS} products per synchronous call. "
            "Larger ranges use the asynchronous bulk job in docs/API.md."
        )

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, item in enumerate(products):
        item_id = item.get("id") or item.get("name") if isinstance(item, dict) else None
        try:
            results.append(assess_product(item))
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append({"index": index, "id": item_id, "error": str(exc)})

    return {
        "model": MODEL_ID,
        "summary": {
            "received": len(products),
            "assessed": len(results),
            "failed": len(errors),
            "less_healthy": sum(1 for r in results if r["less_healthy"]),
        },
        "results": results,
        "errors": errors,
    }
