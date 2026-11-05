"""Lookup mode: CoFID 2021 foods, with their observations and, where scorable, NPM.

Maps a CoFID food's observations to assessment inputs and runs the same
assess_values used for caller-supplied products. Nothing is filled in:
every input comes from a CoFID observation, from a rule decided by Elliot
(fruit, vegetable and nut content by food group) or from the caller, and
the response says which. An input that cannot be sourced makes the food
"not yet scorable", with the missing inputs named.

Decisions encoded here (each is one table or constant):

- Drink status comes from the CoFID food group (DRINK_GROUP_PREFIXES).
- Fruit, vegetable and nut content: CoFID has no FVN percentage. A food
  whose CoFID group is fruit (F), vegetables (D) or nuts and seeds (G)
  carries 100%, labelled derived_from_group (Elliot, November 5, 2026).
  Any other food needs a caller-supplied fvn_percent. FVN is never
  zero-filled and never estimated from the food's name.
- Fibre: NSP (ENGFIB) where CoFID gives a number, otherwise AOAC (AOACFIB).
- A trace ("Tr") counts as 0 g for banding and is labelled so. A value
  CoFID marks "N" (present, amount unknown) or does not give is missing.
- Alcoholic beverages (group Q) are per 100 ml in CoFID; they are
  converted to per 100 g by dividing by the food's CoFID specific gravity,
  and are not scorable without one. Other foods are per 100 g; a drink
  among them has no per-100 ml values, so its traffic lights are not
  assessed (no density is assumed).
"""

from __future__ import annotations

from typing import Any

from .lookup import lookup_cofid
from .service import assess_values, run_bulk

FVN_GROUP_PREFIXES = ("D", "F", "G")
DRINK_GROUP_PREFIXES = ("P", "Q", "BH", "FC")
ALCOHOLIC_GROUP_PREFIX = "Q"
SPECIFIC_GRAVITY = "FACTOR:Specific gravity"

# CoFID nutrient code -> assessment input.
_INPUTS = {
    "energy_kj": "KJ",
    "fat_g": "FAT",
    "saturated_fat_g": "SATFOD",
    "total_sugars_g": "TOTSUG",
    "sodium_mg": "NA",
    "protein_g": "PROT",
}
_REQUIRED_FOR_NPM = ("energy_kj", "saturated_fat_g", "total_sugars_g", "sodium_mg", "protein_g")


def _value(observation: dict[str, Any] | None) -> tuple[float | None, str]:
    if observation is None:
        return None, "not given"
    kind = observation["value_kind"]
    if kind == "number":
        return observation["value"], "number"
    if kind == "trace":
        return 0.0, "trace counted as 0"
    if kind == "present_not_quantified":
        return None, "N (present, amount unknown)"
    return None, f"{kind} not used for scoring"


def _is_drink(group: str | None) -> bool:
    return any((group or "").startswith(p) for p in DRINK_GROUP_PREFIXES)


def assess_cofid_food(food: dict[str, Any], *, fvn_percent: float | None,
                      portion_g: float | None) -> dict[str, Any]:
    """Assessment block for one CoFID food (as returned by lookup_cofid)."""
    by_code = {o["nutrient_code"]: o for o in food["observations"]}
    group = food["group"]
    is_drink = _is_drink(group)
    inputs: dict[str, dict[str, Any]] = {}
    missing: list[str] = []

    values: dict[str, float] = {}
    for name, code in _INPUTS.items():
        value, how = _value(by_code.get(code))
        inputs[name] = {"cofid_code": code, "value": value, "source": how}
        if value is None:
            if name in _REQUIRED_FOR_NPM:
                missing.append(f"{name} ({code}: {how})")
        else:
            values[name] = value

    nsp, nsp_how = _value(by_code.get("ENGFIB"))
    aoac, aoac_how = _value(by_code.get("AOACFIB"))
    if by_code.get("ENGFIB", {}).get("value_kind") in ("number", "trace"):
        values["fibre_nsp_g"] = nsp
        inputs["fibre"] = {"cofid_code": "ENGFIB", "method": "nsp_englyst", "value": nsp, "source": nsp_how}
    elif by_code.get("AOACFIB", {}).get("value_kind") in ("number", "trace"):
        values["fibre_aoac_g"] = aoac
        inputs["fibre"] = {"cofid_code": "AOACFIB", "method": "aoac", "value": aoac, "source": aoac_how}
    else:
        inputs["fibre"] = {"cofid_code": None, "method": None, "value": None,
                           "source": f"NSP {nsp_how}; AOAC {aoac_how}"}
        missing.append(f"fibre (ENGFIB: {nsp_how}; AOACFIB: {aoac_how})")

    if fvn_percent is not None:
        values["fruit_veg_nuts_percent"] = fvn_percent
        inputs["fruit_veg_nuts_percent"] = {"value": fvn_percent, "source": "caller_supplied"}
    elif any((group or "").startswith(p) for p in FVN_GROUP_PREFIXES):
        values["fruit_veg_nuts_percent"] = 100.0
        inputs["fruit_veg_nuts_percent"] = {
            "value": 100.0, "source": "derived_from_group",
            "rule": f"CoFID group {group} is fruit (F), vegetables (D) or nuts and seeds (G)",
        }
    else:
        inputs["fruit_veg_nuts_percent"] = {"value": None, "source": "not available"}
        missing.append(
            "fruit_veg_nuts_percent (CoFID has none and group "
            f"{group} is not fruit, vegetables or nuts; supply fvn_percent)"
        )

    alcoholic = (group or "").startswith(ALCOHOLIC_GROUP_PREFIX)
    drink_note = (
        f"Treated as a {'drink' if is_drink else 'food'} because its CoFID group is {group} "
        f"(drink groups: {', '.join(DRINK_GROUP_PREFIXES)})."
    )
    per_100ml = None
    conversion = None
    if alcoholic:
        gravity, how = _value(by_code.get(SPECIFIC_GRAVITY))
        if not gravity:
            missing.append(f"specific gravity (values are per 100 ml; {how})")
        else:
            amounts = [k for k in values if k != "fruit_veg_nuts_percent"]
            per_100ml = {k: values[k] for k in amounts}
            for k in amounts:
                values[k] = values[k] / gravity
            conversion = {"from_basis": "per_100ml", "to_basis": "per_100g",
                          "specific_gravity": gravity, "gravity_source": SPECIFIC_GRAVITY,
                          "rule": "value_per_100g = value_per_100ml / specific_gravity"}

    block: dict[str, Any] = {
        "is_drink": is_drink,
        "drink_status": drink_note,
        "inputs": inputs,
        "input_conversion": conversion,
    }
    if missing:
        block["scorable"] = False
        block["missing_inputs"] = missing
        return block
    block["scorable"] = True
    block.update(assess_values(per_100g=values, is_drink=is_drink, per_100ml=per_100ml,
                               portion_g=portion_g))
    return block


def _number(payload: dict, name: str, *, minimum: float, maximum: float | None = None,
            inclusive_min: bool = True) -> float | None:
    value = payload.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    if value < minimum or (not inclusive_min and value == minimum) or (maximum is not None and value > maximum):
        raise ValueError(f"{name} is out of range.")
    return float(value)


def lookup_and_assess(payload: dict[str, Any]) -> dict[str, Any]:
    """Look up one CoFID food by code or exact name, with assessments."""
    if not isinstance(payload, dict):
        raise ValueError("Lookup payload must be an object.")
    code, name = payload.get("code"), payload.get("name")
    for field, value in (("code", code), ("name", name)):
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field} must be a string.")
    fvn = _number(payload, "fvn_percent", minimum=0, maximum=100)
    portion_g = _number(payload, "portion_g", minimum=0, inclusive_min=False)
    result = lookup_cofid(code=code, name=name)    # raises unless exactly one
    for food in result["matches"]:
        food["assessment"] = assess_cofid_food(food, fvn_percent=fvn, portion_g=portion_g)
    result["mode"] = "lookup"
    result["evidence_note"] = (
        "Values are CoFID 2021 observations with their provenance. Assessment inputs "
        "say where each came from; nothing is estimated."
    )
    return result


def lookup_bulk(payload: dict[str, Any]) -> dict[str, Any]:
    """Many lookups in one call, with the same partial-success rule as assess."""
    results, errors, received = run_bulk(payload, "items", lookup_and_assess)
    matches = [m for r in results for m in r["matches"]]
    return {
        "mode": "lookup",
        "summary": {
            "received": received,
            "looked_up": len(results),
            "failed": len(errors),
            "no_match": sum(1 for r in results if not r["matches"]),
            "foods_matched": len(matches),
            "scorable": sum(1 for m in matches if m["assessment"]["scorable"]),
        },
        "results": results,
        "errors": errors,
    }
