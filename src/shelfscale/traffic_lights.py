"""UK front-of-pack traffic lights (red, amber, green), from the official text.

Source: "Guide to creating a front of pack (FoP) nutrition label for
pre-packed products sold through retail outlets", Department of Health,
Food Standards Agency and devolved administrations, updated November 2016.
Annex 3, Tables 2 and 3, and Step 3. GOV.UK copy:
https://assets.publishing.service.gov.uk/media/5a80cd03ed915d74e33fc7c5/FoP_Nutrition_labelling_UK_guidance.pdf
(sha256 e31e2d94b9eaa42254be46a1aa828a0ea19f2282cbf300230300478d6f607321,
retrieved 2026-11-05). The FSA's copy republished on GOV.UK on 25 June 2026
(fop-guidance_0.pdf) has the same text.

Rules implemented exactly as written:

- Food is assessed per 100 g "whether or not it is sold by volume"
  (Table 2); drinks per 100 ml (Table 3).
- Green: at or below the low cut-off. Amber: above low and at or below
  high. Red: above high.
- Per-portion criteria are red only. They apply when the portion is more
  than 100 g (food) or more than 150 ml (drink). A nutrient over its
  per-portion cut-off is red regardless of its per-100 g/ml colour; every
  other nutrient is coloured on the per-100 g/ml criteria (Step 3.2).
- Energy is never colour coded.

The guidance defines no overall or "summary" colour, so none is produced.
"""

from __future__ import annotations

from typing import Any

GUIDANCE = {
    "title": "Guide to creating a front of pack (FoP) nutrition label for pre-packed "
             "products sold through retail outlets",
    "publisher": "Department of Health, Food Standards Agency and devolved administrations",
    "edition": "Updated November 2016",
    "url": "https://assets.publishing.service.gov.uk/media/5a80cd03ed915d74e33fc7c5/"
           "FoP_Nutrition_labelling_UK_guidance.pdf",
    "sections": "Annex 3, Tables 2 and 3; Step 3",
}

NUTRIENTS = ("fat", "saturates", "sugars", "salt")

# (low cut-off, high cut-off) in g per 100 g (food) or per 100 ml (drink).
_FOOD_PER_100G = {"fat": (3.0, 17.5), "saturates": (1.5, 5.0), "sugars": (5.0, 22.5), "salt": (0.3, 1.5)}
_DRINK_PER_100ML = {"fat": (1.5, 8.75), "saturates": (0.75, 2.5), "sugars": (2.5, 11.25), "salt": (0.3, 0.75)}

# Red per portion, in g per portion, and the portion size above which it applies.
_FOOD_RED_PER_PORTION = {"fat": 21.0, "saturates": 6.0, "sugars": 27.0, "salt": 1.8}
_DRINK_RED_PER_PORTION = {"fat": 10.5, "saturates": 3.0, "sugars": 13.5, "salt": 0.9}
FOOD_PORTION_LIMIT_G = 100.0
DRINK_PORTION_LIMIT_ML = 150.0


def _colour(value: float, low: float, high: float) -> str:
    if value <= low:
        return "green"
    if value <= high:
        return "amber"
    return "red"


def traffic_lights(
    *,
    is_drink: bool,
    per_100: dict[str, float | None],
    portion: float | None = None,
) -> dict[str, Any]:
    """Colour fat, saturates, sugars and salt.

    ``per_100`` holds g per 100 g for food, g per 100 ml for drink, keyed by
    NUTRIENTS; a missing or None value is reported as not assessed.
    ``portion`` is in g for food and ml for drink.
    """
    table = _DRINK_PER_100ML if is_drink else _FOOD_PER_100G
    red_per_portion = _DRINK_RED_PER_PORTION if is_drink else _FOOD_RED_PER_PORTION
    limit = DRINK_PORTION_LIMIT_ML if is_drink else FOOD_PORTION_LIMIT_G
    unit = "ml" if is_drink else "g"
    portion_rule = portion is not None and portion > limit

    colours: dict[str, Any] = {}
    for nutrient in NUTRIENTS:
        value = per_100.get(nutrient)
        if value is None:
            colours[nutrient] = {"colour": None, "reason": f"{nutrient} not supplied"}
            continue
        low, high = table[nutrient]
        entry: dict[str, Any] = {
            "colour": _colour(value, low, high),
            "decided_by": f"per_100{unit}",
            f"per_100{unit}": value,
        }
        if portion_rule:
            amount = value * portion / 100.0
            entry["per_portion"] = amount
            if amount > red_per_portion[nutrient]:
                entry["colour"] = "red"
                entry["decided_by"] = "per_portion"
        colours[nutrient] = entry

    return {
        "scheme": "uk-fop-2016",
        "basis": f"per_100{unit}",
        "product_type": "drink" if is_drink else "food",
        "portion": portion,
        "portion_unit": unit,
        "portion_rule_applied": portion_rule,
        "colours": colours,
        "guidance": GUIDANCE,
    }
