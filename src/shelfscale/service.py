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

_REQUIRED_NUTRIENTS = (
    "energy_kj",
    "saturated_fat_g",
    "total_sugars_g",
    "fruit_veg_nuts_percent",
    "fibre_aoac_g",
    "protein_g",
)


def _require_number(nutrients: dict, name: str) -> float:
    value = nutrients.get(name)
    if value is None:
        raise ValueError(f"nutrients.{name} is required.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"nutrients.{name} must be a number.")
    return float(value)


def assess_product(payload: dict[str, Any]) -> dict[str, Any]:
    """Assess one product from its per-100 g/ml nutrient values.

    Payload shape:
        {
          "id": "sku-123",                  # or "name"
          "is_drink": false,
          "portion_g": 30,                  # optional, for per-portion view
          "nutrients": {
            "energy_kj": 1800, "saturated_fat_g": 4.0, "total_sugars_g": 20,
            "sodium_mg": 300,               # or "salt_g": 0.75
            "fruit_veg_nuts_percent": 0, "fibre_aoac_g": 2.0, "protein_g": 6.0
          }
        }
    """
    if not isinstance(payload, dict):
        raise ValueError("Product payload must be an object.")
    product_id = payload.get("id") or payload.get("name")
    if not product_id:
        raise ValueError("Product needs an 'id' or a 'name'.")
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

    is_drink = bool(payload.get("is_drink", False))
    result = calculate_npm(is_drink=is_drink, **values)

    response: dict[str, Any] = {
        "id": product_id,
        "model": MODEL_ID,
        "basis": "per_100ml" if is_drink else "per_100g",
        "score": result.score,
        "less_healthy": result.less_healthy,
        "a_points": result.a_points,
        "c_points": result.c_points,
        "total_a": result.total_a,
        "total_c": result.total_c,
        "protein_counted": result.protein_counted,
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
            "fibre_aoac_g": round(values["fibre_aoac_g"] * factor, 2),
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
