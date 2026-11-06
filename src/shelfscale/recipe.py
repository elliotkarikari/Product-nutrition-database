"""Recipe calculation: CoFID ingredients by weight, scored by the existing engine.

A recipe is a list of CoFID foods (food_id) with gram weights as used, and
a number of servings. ShelfScale sums each ingredient's current
observations by weight and divides by the total raw weight. No cooking
yield or water loss is applied: the result describes the mix as assembled,
and every response says so.

Scoring reuses service.assess_values and service.npm2018_block, the same
functions behind /v1/assess and /v1/lookup. The rules carried over from
lookup mode, unchanged:

- a nutrient an ingredient does not record (CoFID "N", or not given) makes
  that nutrient unavailable for the recipe, with the ingredient named;
  a trace counts as 0;
- fibre is NSP when every ingredient has NSP, otherwise AOAC when every
  ingredient has AOAC; methods are never mixed;
- fruit, vegetable and nut content: a caller fvn_percent wins; otherwise
  it is the weight share of ingredients the group rule already gives a
  value (F, D, G at 100%, potatoes DA at 0%). If any ingredient has no
  value under that rule, the recipe needs fvn_percent, naming them;
- NPM 2018: free sugars only from the caller (free_sugars_g, per 100 g of
  the recipe); total sugars are never used; the 22 reviewed 2018 tuber
  codes count 0 for fruit, vegetables, nuts and seeds;
- alcoholic drinks (CoFID group Q, recorded per 100 ml) are refused as
  ingredients.

A recipe is a food for scoring and traffic lights.
"""

from __future__ import annotations

from typing import Any

from .cofid_assess import (ALCOHOLIC_GROUP_PREFIX, FVN_EXCLUDED_BY_GUIDANCE, FVN_GROUP_PREFIXES,
                           FVN_NOT_DERIVED, _review_flags)
from .fvn import TUBERS_2018
from .label import GUIDE, ROUNDING, ingredient_label_values, round_declaration
from .lookup import DATA_RELEASE, _index
from .npm2018 import MODEL_ID as NPM2018_ID
from .service import MODEL_ID, assess_values, npm2018_block, verdict_changes
from .ui_api import as_sold_flag, foods_by_id, source_card
from .validation import number

MAX_INGREDIENTS = 60
MAX_GRAMS = 100_000
MAX_SERVINGS = 1000

SCORE_INPUTS = (
    ("energy_kj", "KJ"),
    ("fat_g", "FAT"),
    ("saturated_fat_g", "SATFOD"),
    ("total_sugars_g", "TOTSUG"),
    ("sodium_mg", "NA"),
    ("protein_g", "PROT"),
)
REQUIRED_FOR_NPM = ("energy_kj", "saturated_fat_g", "total_sugars_g", "sodium_mg", "protein_g")
YIELD_NOTE = ("Calculated from raw ingredient weights as used. No cooking yield or water loss is "
              "applied, so per 100 g describes the mix as assembled.")


def _value(o: dict[str, Any] | None) -> tuple[float | None, str]:
    if o is None:
        return None, "not given"
    if o["value_kind"] == "number":
        return o["value"], "number"
    if o["value_kind"] == "trace":
        return 0.0, "trace counted as 0"
    if o["value_kind"] == "present_not_quantified":
        return None, "N (present, amount unknown)"
    return None, o["value_kind"]


def _current(food_id: str) -> dict[str, dict[str, Any]]:
    from .lookup import _observation_dict
    return {o.definition.code: _observation_dict(o) for o in _index()[2].get(food_id, [])
            if o.status == "current"}


def _group_fvn(group: str | None) -> tuple[float | None, str]:
    g = group or ""
    if any(g.startswith(p) for p in FVN_EXCLUDED_BY_GUIDANCE):
        return 0.0, "excluded_by_guidance (potatoes)"
    if any(g.startswith(p) for p in FVN_NOT_DERIVED):
        return None, f"group {g} is vegetable dishes (composite)"
    if any(g.startswith(p) for p in FVN_GROUP_PREFIXES):
        return 100.0, "derived_from_group"
    return None, f"group {g} has no group-derived value"


def _parse(payload: Any) -> tuple[list[dict[str, Any]], int, dict[str, float]]:
    if not isinstance(payload, dict):
        raise ValueError("Recipe payload must be an object.")
    items = payload.get("ingredients")
    if not isinstance(items, list) or not items:
        raise ValueError("A recipe needs at least one ingredient.")
    if len(items) > MAX_INGREDIENTS:
        raise ValueError(f"A recipe is limited to {MAX_INGREDIENTS} ingredients.")
    foods = foods_by_id()
    parsed = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("food_id"), str):
            raise ValueError(f"ingredients[{index}] needs a food_id.")
        food = foods.get(item["food_id"])
        if food is None:
            raise ValueError(f"ingredients[{index}]: no CoFID 2021 food has id {item['food_id']!r}.")
        if (food.group or "").startswith(ALCOHOLIC_GROUP_PREFIX):
            raise ValueError(f"{food.name}: alcoholic drinks are recorded per 100 ml in CoFID and "
                             "are not supported as recipe ingredients yet.")
        grams = number(item.get("grams"), f"ingredients[{index}].grams", positive=True,
                       maximum=MAX_GRAMS)
        parsed.append({"food": food, "grams": grams})
    servings = payload.get("servings", 1)
    if isinstance(servings, bool) or not isinstance(servings, int) or not 1 <= servings <= MAX_SERVINGS:
        raise ValueError(f"servings must be a whole number from 1 to {MAX_SERVINGS}.")
    extra = {}
    for name, maximum in (("fvn_percent", 100), ("free_sugars_g", 100)):
        if payload.get(name) is not None:
            extra[name] = number(payload[name], name, maximum=maximum)
    return parsed, servings, extra


def calculate(payload: Any) -> dict[str, Any]:
    items, servings, extra = _parse(payload)
    total_g = sum(i["grams"] for i in items)
    serving_g = total_g / servings
    for item in items:
        item["obs"] = _current(item["food"].food_id)

    # Weighted sums for scoring inputs, with per-ingredient contributions.
    per_100g: dict[str, float] = {}
    missing: list[str] = []
    contributions: dict[str, list[dict[str, Any]]] = {}

    def weigh(name: str, code: str) -> float | None:
        total, gaps, rows = 0.0, [], []
        for item in items:
            o = item["obs"].get(code)
            value, how = _value(o)
            if value is None:
                gaps.append(f"{item['food'].name} ({code}: {how})")
                continue
            amount = value * item["grams"] / 100.0
            total += amount
            rows.append({"food_id": item["food"].food_id, "name": item["food"].name,
                         "grams": item["grams"], "per_100g": value, "amount": amount,
                         "how": how, "source": source_card(o)})
        contributions[name] = rows
        if gaps:
            contributions[name + "_gaps"] = gaps
            return None
        return total / total_g * 100.0

    for name, code in SCORE_INPUTS:
        value = weigh(name, code)
        if value is None:
            if name in REQUIRED_FOR_NPM:
                missing.append(f"{name}: not recorded for " + "; ".join(contributions[name + "_gaps"]))
        else:
            per_100g[name] = value

    fibre = {"method": None}
    nsp = weigh("fibre_nsp_g", "ENGFIB")
    aoac = weigh("fibre_aoac_g", "AOACFIB")
    if nsp is not None:
        per_100g["fibre_nsp_g"] = nsp
        fibre = {"method": "nsp_englyst", "rule": "every ingredient records NSP"}
    elif aoac is not None:
        per_100g["fibre_aoac_g"] = aoac
        fibre = {"method": "aoac", "rule": "not every ingredient records NSP; every one records AOAC"}
    else:
        missing.append("fibre: no single method is recorded for every ingredient (NSP gaps: "
                       + "; ".join(contributions.get("fibre_nsp_g_gaps", [])) + ")")

    # Fruit, vegetables and nuts.
    fvn_rows, fvn_gaps = [], []
    for item in items:
        value, how = _group_fvn(item["food"].group)
        fvn_rows.append({"name": item["food"].name, "grams": item["grams"], "value": value, "how": how})
        if value is None:
            fvn_gaps.append(f"{item['food'].name} ({how})")
    if "fvn_percent" in extra:
        fvn = {"value": extra["fvn_percent"], "source": "caller_supplied"}
        per_100g["fruit_veg_nuts_percent"] = extra["fvn_percent"]
    elif fvn_gaps:
        fvn = {"value": None, "source": "not available", "needs": fvn_gaps}
        missing.append("fruit_veg_nuts_percent: no group-derived value for " + "; ".join(fvn_gaps)
                       + ". Supply fvn_percent for the recipe.")
    else:
        value = sum(r["value"] * r["grams"] for r in fvn_rows) / total_g
        fvn = {"value": value, "source": "derived_from_ingredients",
               "rule": "weight share of ingredients with a group-derived value (F, D, G 100%; DA 0%)"}
        per_100g["fruit_veg_nuts_percent"] = value
    fvn["ingredients"] = fvn_rows
    known = [r for r in fvn_rows if r["value"] is not None]
    fvn["known"] = {
        "share_of_weight_percent": sum(r["grams"] for r in known) / total_g * 100.0,
        "fvn_percent_from_known": sum(r["value"] * r["grams"] for r in known) / total_g,
        "note": ("Weight share of ingredients the group rule gives a value. A guide for the "
                 "figure you supply, not a substitute for it."),
    }

    # NPM 2018 inputs: same values, the caller's free sugars, the 2018 FVNS rule.
    values_2018 = {k: per_100g[k] for k in ("energy_kj", "saturated_fat_g", "protein_g", "sodium_mg")
                   if k in per_100g}
    labels = {k: "recipe (weighted CoFID values)" for k in values_2018}
    if aoac is not None:
        values_2018["fibre_aoac_g"] = aoac
        labels["fibre_aoac_g"] = "recipe (weighted CoFID AOACFIB)"
    elif nsp is not None:
        values_2018["fibre_nsp_g"] = nsp
    if "free_sugars_g" in extra:
        values_2018["free_sugars_g"] = extra["free_sugars_g"]
    if "fvn_percent" in extra:
        values_2018["fruit_veg_nuts_percent"] = extra["fvn_percent"]
    elif not fvn_gaps:
        values_2018["fvns_g"] = sum(
            (0.0 if item["food"].food_id in TUBERS_2018 else row["value"]) * row["grams"]
            for item, row in zip(items, fvn_rows)) / total_g
        labels["fvns_g"] = "derived_from_ingredients (2018 tuber exclusions applied)"
    npm2018 = npm2018_block(values_2018, is_drink=False, labels=labels)
    if "free_sugars_g" not in extra:
        npm2018["free_sugars_note"] = (
            "CoFID records total sugars, not free sugars. Enter free sugars per 100 g of the "
            "recipe for a 2018 score; total sugars are never used instead.")

    review = []
    for item in items:
        for flag in _review_flags(item["food"].group, "fvn_percent" in extra, False):
            review.append({**flag, "ingredient": item["food"].name})

    if missing:
        models = {
            MODEL_ID: {"model": MODEL_ID, "status": "in force", "scorable": False,
                       "missing_inputs": missing},
            NPM2018_ID: npm2018,
        }
        assessment: dict[str, Any] = {"basis": "per_100g", "models": models,
                                      "verdict_changes_under_2018": verdict_changes(models),
                                      "traffic_lights": None}
    else:
        assessment = assess_values(per_100g=per_100g, is_drink=False, portion_g=serving_g,
                                   npm2018=npm2018)

    # Label values, per ingredient then summed.
    label_totals: dict[str, float] = {}
    label_missing: dict[str, list[str]] = {}
    energy_gaps: dict[str, list[str]] = {}
    for item in items:
        values, gaps_here, energy_here = ingredient_label_values(item["obs"])
        for key, value in values.items():
            if value is None:
                label_missing.setdefault(key, []).append(item["food"].name)
            else:
                label_totals[key] = label_totals.get(key, 0.0) + value * item["grams"] / 100.0
        for part in energy_here:
            energy_gaps.setdefault(part, []).append(item["food"].name)
    label_100 = {k: (None if k in label_missing else v / total_g * 100.0) for k, v in label_totals.items()}
    label_serving = {k: (None if v is None else v * serving_g / 100.0) for k, v in label_100.items()}
    for key in label_missing:
        label_100[key] = label_serving[key] = None

    return {
        "mode": "recipe",
        "data_release": DATA_RELEASE,
        "name": payload.get("name") if isinstance(payload.get("name"), str) else None,
        "total_g": total_g,
        "servings": servings,
        "serving_g": serving_g,
        "yield_note": YIELD_NOTE,
        "ingredients": [{
            "food_id": i["food"].food_id, "code": i["food"].source_code, "name": i["food"].name,
            "group": i["food"].group, "grams": i["grams"], "as_sold": as_sold_flag(i["food"].name),
        } for i in items],
        "per_100g": per_100g,
        "per_serving": {k: v * serving_g / 100.0 for k, v in per_100g.items()
                        if k != "fruit_veg_nuts_percent"},
        "fibre": fibre,
        "fruit_veg_nuts": fvn,
        "review_flags": review,
        "assessment": assessment,
        "contributions": {k: v for k, v in contributions.items() if not k.endswith("_gaps")},
        "label": {
            "per_100g": round_declaration(label_100),
            "per_serving": round_declaration(label_serving),
            "serving_g": serving_g,
            "missing": label_missing,
            "energy_excludes": energy_gaps,
            "method": GUIDE,
            "rounding": ROUNDING,
            "statement": ("Values calculated from generally established and accepted data "
                          "(CoFID 2021 with official overlays), not laboratory analysis."),
        },
    }
