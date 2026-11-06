"""UK Nutrient Profiling Model 2018: SHADOW MODEL, NOT IN FORCE.

The law in force uses NPM 2004/05 (npm.py). DHSC published the 2018 model
on 27 January 2026 and consulted (to June 2026) on applying it to the
advertising and promotion restrictions; the outcome is pending. Every
output from this module is labelled as the 2018 shadow model.

Source of every rule: DHSC, "Nutrient profiling model 2018: technical
guidance", GOV.UK, published 27 January 2026 (OGL v3.0):
https://www.gov.uk/government/publications/nutrient-profiling-model-2018/nutrient-profiling-model-2018-technical-guidance
Validated against DHSC, "Nutrient profiling model 2018: worked examples and
further advice on calculations", same date (all 17 worked examples).

Rules, with their place in the technical guidance:

- Scope: all foods and non-alcoholic drinks ("Nutrient profiling model
  2018"). Points per 100 g ("Nutrient profiling model 2018").
- A points, Table 1: energy (kJ), saturated fats (g), free sugars (g),
  salt (g), each 0 to 10. Note: salt, not sodium.
- C points, Table 2: protein (g, 0 to 5), fruit, vegetables, nuts and seeds
  (g per 100 g, 0, 1, 2 or 5), fibre by the AOAC method (g, 0 to 10).
- Points: a value scores a band when it is more than (>) the band's lower
  bound ("Calculating 'A' points").
- Protein rule ("Calculating the overall score"): with 11 or more A points,
  protein counts only if fruit, vegetables, nuts and seeds score 5.
- Less healthy: food 4 or more, drink 1 or more ("Calculating the overall
  score").
- Fibre is AOAC ("Fibre values"). Where only NSP is known the guidance says
  to convert "using an appropriate conversion factor" but gives none, so
  this module takes AOAC fibre only.
- Free sugars are an input: the guidance computes them from ingredients
  ("How to calculate free sugars"). Total sugars are never used in their
  place.
"""

from __future__ import annotations

from dataclasses import dataclass

from .validation import number

MODEL_ID = "uk-npm-2018"
STATUS = "shadow model, not in force"
GUIDANCE = {
    "title": "Nutrient profiling model 2018: technical guidance",
    "publisher": "Department of Health and Social Care (DHSC)",
    "published": "2026-01-27",
    "url": "https://www.gov.uk/government/publications/nutrient-profiling-model-2018/"
           "nutrient-profiling-model-2018-technical-guidance",
    "status": "Shadow model, not in force. Consultation on applying it closed June 2026; outcome pending.",
}

# Table 1: 'A' points per 100 g. Lower bounds of points 1 to 10 (score if value > bound).
_ENERGY_KJ = [315, 630, 945, 1260, 1575, 1890, 2205, 2520, 2835, 3150]
_SATURATED_FAT_G = [0.9, 1.9, 2.8, 3.7, 4.7, 5.6, 6.6, 7.5, 8.4, 9.4]
_FREE_SUGARS_G = [0.9, 1.9, 2.8, 3.7, 4.6, 5.6, 6.5, 7.4, 8.3, 9.3]
_SALT_G = [0.2, 0.5, 0.7, 0.9, 1.1, 1.4, 1.6, 1.8, 2.0, 2.3]
# Table 2: 'C' points per 100 g.
_PROTEIN_G = [1.7, 3.4, 5.1, 6.8, 8.5]
_FIBRE_AOAC_G = [0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8, 5.4, 6.0]


def _points(value: float, bounds: list[float]) -> int:
    return sum(1 for bound in bounds if value > bound)


def _fvns_points(grams_per_100g: float) -> int:
    # Table 2: > 40 -> 1, > 60 -> 2, > 80 -> 5 (3 and 4 "Not applicable").
    if grams_per_100g > 80:
        return 5
    if grams_per_100g > 60:
        return 2
    if grams_per_100g > 40:
        return 1
    return 0


@dataclass(frozen=True)
class NPM2018Result:
    a_points: dict[str, int]
    c_points: dict[str, int]
    protein_counted: bool
    score: int
    is_drink: bool
    less_healthy: bool

    @property
    def total_a(self) -> int:
        return sum(self.a_points.values())

    @property
    def total_c(self) -> int:
        return sum(self.c_points.values())


def calculate_npm2018(
    *,
    energy_kj: float,
    saturated_fat_g: float,
    free_sugars_g: float,
    salt_g: float,
    protein_g: float,
    fvns_g: float,
    fibre_aoac_g: float,
    is_drink: bool = False,
) -> NPM2018Result:
    """Score per-100 g values under the NPM 2018 shadow model."""
    if not isinstance(is_drink, bool):
        raise ValueError("is_drink must be a boolean.")
    values = dict(energy_kj=energy_kj, saturated_fat_g=saturated_fat_g,
                  free_sugars_g=free_sugars_g, salt_g=salt_g, protein_g=protein_g,
                  fvns_g=fvns_g, fibre_aoac_g=fibre_aoac_g)
    for name, value in values.items():
        number(value, name)
    if fvns_g > 100:
        raise ValueError("fvns_g cannot exceed 100 g per 100 g.")

    a_points = {
        "energy": _points(energy_kj, _ENERGY_KJ),
        "saturated_fat": _points(saturated_fat_g, _SATURATED_FAT_G),
        "free_sugars": _points(free_sugars_g, _FREE_SUGARS_G),
        "salt": _points(salt_g, _SALT_G),
    }
    total_a = sum(a_points.values())
    fvns = _fvns_points(fvns_g)
    protein_counted = not (total_a >= 11 and fvns < 5)
    c_points = {
        "fruit_veg_nuts_seeds": fvns,
        "fibre": _points(fibre_aoac_g, _FIBRE_AOAC_G),
        "protein": _points(protein_g, _PROTEIN_G) if protein_counted else 0,
    }
    score = total_a - sum(c_points.values())
    return NPM2018Result(
        a_points=a_points,
        c_points=c_points,
        protein_counted=protein_counted,
        score=score,
        is_drink=is_drink,
        less_healthy=score >= (1 if is_drink else 4),
    )
