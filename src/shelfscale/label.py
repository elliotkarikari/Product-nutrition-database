"""UK nutrition declaration values from CoFID, by the CoFID 2021 user guide's own rules.

CoFID is not label-ready as printed. Its user guide ("Food labelling",
pages 15 to 16) says, for a declaration under retained Regulation (EU)
No 1169/2011:

- protein is declared as total nitrogen x 6.25 (CoFID uses food-specific
  factors);
- carbohydrate is declared by weight, not as monosaccharide equivalents:
  total carbohydrate divide by 1.05 unless it is mainly starch or mainly
  oligosaccharide; starch divide by 1.10; sucrose and lactose divide by
  1.05; glucose and the other sugars as given;
- energy uses the Regulation's factors: carbohydrate 17 kJ / 4 kcal per g,
  protein 17 / 4, fat 37 / 9, fibre 8 / 2, alcohol 29 / 7 (polyols,
  salatrims, organic acids and erythritol have their own factors; CoFID
  has no columns for them, so they are not counted);
- salt is sodium x 2.5.

How the guide's words are applied here (recorded in
memory/decisions/label-from-cofid.md):

- "mainly starch" means starch is more than half of total carbohydrate;
  then starch is divided by 1.10 and the rest by 1.05. Mainly
  oligosaccharide is not detected (CoFID gives OLIGO for few foods), so
  those foods take the 1.05 default.
- sugars by weight = total sugars - (sucrose + lactose) + (sucrose + lactose) / 1.05.
  Maltose is a disaccharide, but the guide names only sucrose and lactose,
  so maltose is taken as given, as the guide's wording says.
- fibre energy uses AOAC fibre. Where AOAC fibre or alcohol is not
  recorded for an ingredient, its energy is left out and the result says
  so by name. No value is assumed.

Conversion is per ingredient, then summed. Display rounding is a separate,
last step (round_declaration) and never feeds a calculation.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

FACTORS_KJ = {"carbohydrate": 17, "protein": 17, "fat": 37, "fibre": 8, "alcohol": 29}
FACTORS_KCAL = {"carbohydrate": 4, "protein": 4, "fat": 9, "fibre": 2, "alcohol": 7}
GUIDE = ("McCance and Widdowson's Composition of Foods Integrated Dataset 2021, user guide, "
         "'Food labelling', pages 15 to 16")
ROUNDING = ("European Commission guidance on tolerances for nutrition labelling (December 2012), "
            "rounding table, as reproduced by the BDA Nutrition and Hydration Digest, appendix 12")

LINES = (
    ("energy_kj", "Energy", "kJ"),
    ("energy_kcal", "", "kcal"),
    ("fat_g", "Fat", "g"),
    ("saturates_g", "of which saturates", "g"),
    ("carbohydrate_g", "Carbohydrate", "g"),
    ("sugars_g", "of which sugars", "g"),
    ("protein_g", "Protein", "g"),
    ("salt_g", "Salt", "g"),
)


def _num(obs: dict[str, dict[str, Any]], code: str) -> float | None:
    o = obs.get(code)
    if o is None:
        return None
    if o["value_kind"] == "number":
        return o["value"]
    if o["value_kind"] == "trace":
        return 0.0
    return None


def ingredient_label_values(obs: dict[str, dict[str, Any]]) -> tuple[dict[str, float | None], list[str], list[str]]:
    """Per-100 g label values for one food: (values, missing, energy_gaps)."""
    values: dict[str, float | None] = {}
    missing: list[str] = []
    gaps: list[str] = []

    nitrogen = _num(obs, "TOTNIT")
    values["protein_g"] = nitrogen * 6.25 if nitrogen is not None else None
    values["fat_g"] = _num(obs, "FAT")
    values["saturates_g"] = _num(obs, "SATFOD")
    sodium = _num(obs, "NA")
    values["salt_g"] = sodium * 2.5 / 1000.0 if sodium is not None else None

    cho, starch = _num(obs, "CHO"), _num(obs, "STAR")
    if cho is None:
        values["carbohydrate_g"] = None
    elif starch is not None and starch > cho / 2:
        values["carbohydrate_g"] = starch / 1.10 + (cho - starch) / 1.05
    else:
        values["carbohydrate_g"] = cho / 1.05

    sugars, sucrose, lactose = _num(obs, "TOTSUG"), _num(obs, "SUCR"), _num(obs, "LACT")
    if None in (sugars, sucrose, lactose):
        values["sugars_g"] = None
    else:
        disaccharides = sucrose + lactose
        values["sugars_g"] = sugars - disaccharides + disaccharides / 1.05

    for name, value in values.items():
        if value is None:
            missing.append(name)

    fibre, alcohol = _num(obs, "AOACFIB"), _num(obs, "ALCO")
    if fibre is None:
        gaps.append("fibre")
    if alcohol is None:
        gaps.append("alcohol")
    core = (values["carbohydrate_g"], values["protein_g"], values["fat_g"])
    if None in core:
        values["energy_kj"] = values["energy_kcal"] = None
        missing.append("energy")
    else:
        carb, protein, fat = core
        parts = {"carbohydrate": carb, "protein": protein, "fat": fat,
                 "fibre": fibre or 0.0, "alcohol": alcohol or 0.0}
        values["energy_kj"] = sum(FACTORS_KJ[k] * v for k, v in parts.items())
        values["energy_kcal"] = sum(FACTORS_KCAL[k] * v for k, v in parts.items())
    return values, missing, gaps


def _half_up(value: float, step: str) -> Decimal:
    return Decimal(repr(value)).quantize(Decimal(step), rounding=ROUND_HALF_UP)


def display(name: str, value: float | None) -> str | None:
    """One declared value as printed, from the rounding table."""
    if value is None:
        return None
    if name in ("energy_kj", "energy_kcal"):
        return str(_half_up(value, "1"))
    if name == "salt_g":
        if value >= 1:
            return str(_half_up(value, "0.1"))
        if value > 0.0125:
            return str(_half_up(value, "0.01"))
        return "0"
    if name == "saturates_g":
        if value >= 10:
            return str(_half_up(value, "1"))
        if value > 0.1:
            return str(_half_up(value, "0.1"))
        return "0"
    if value >= 10:
        return str(_half_up(value, "1"))
    if value > 0.5:
        return str(_half_up(value, "0.1"))
    return "0"


def round_declaration(values: dict[str, float | None]) -> list[dict[str, Any]]:
    return [{"key": key, "label": label, "unit": unit, "value": values.get(key),
             "display": display(key, values.get(key))} for key, label, unit in LINES]
