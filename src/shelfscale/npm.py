"""UK Nutrient Profiling Model 2004/05.

Implements the points model in the Department of Health technical guidance
published in January 2011, the version cited by the Food (Promotion and
Placement) (England) Regulations 2021.

All nutrient inputs are per 100 g, for food and drink alike, as sold, or as
reconstituted where the guidance requires that basis. Values labelled per
100 ml must be converted to per 100 g before scoring. The guidance's worked
examples 2 and 6 do this with a specific gravity; ShelfScale does not yet
convert (see docs/API.md, "Scoring basis").

Fibre is scored on the NSP (Englyst) scale when the NSP value is known and on
the AOAC scale otherwise (guidance FAQ a). The caller supplies exactly one.

This module is a calculation aid. It is not legal advice, and a score is only
as good as the nutrient values supplied to it.
"""

from __future__ import annotations

from dataclasses import dataclass


def _band_points(value: float, thresholds: list[float]) -> int:
    """Points equal the number of thresholds the value strictly exceeds."""
    return sum(1 for threshold in thresholds if value > threshold)


def _fruit_veg_nut_points(percent: float) -> int:
    if percent > 80:
        return 5
    if percent > 60:
        return 2
    if percent > 40:
        return 1
    return 0


@dataclass(frozen=True)
class NPMResult:
    a_points: dict[str, int]
    c_points: dict[str, int]
    protein_counted: bool
    fibre_method: str
    score: int
    is_drink: bool
    less_healthy: bool

    @property
    def total_a(self) -> int:
        return sum(self.a_points.values())

    @property
    def total_c(self) -> int:
        return sum(self.c_points.values())


_ENERGY_THRESHOLDS = [335, 670, 1005, 1340, 1675, 2010, 2345, 2680, 3015, 3350]
_SATURATED_FAT_THRESHOLDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
_TOTAL_SUGAR_THRESHOLDS = [4.5, 9, 13.5, 18, 22.5, 27, 31, 36, 40, 45]
_SODIUM_THRESHOLDS = [90, 180, 270, 360, 450, 540, 630, 720, 810, 900]
_FIBRE_THRESHOLDS = {
    "nsp": [0.7, 1.4, 2.1, 2.8, 3.5],
    "aoac": [0.9, 1.9, 2.8, 3.7, 4.7],
}
_PROTEIN_THRESHOLDS = [1.6, 3.2, 4.8, 6.4, 8.0]


def sodium_mg_from_salt_g(salt_g: float) -> float:
    """Convert salt (g) to sodium (mg): sodium = salt / 2.5."""
    return salt_g * 400.0


def calculate_npm(
    *,
    energy_kj: float,
    saturated_fat_g: float,
    total_sugars_g: float,
    fruit_veg_nuts_percent: float,
    protein_g: float,
    fibre_nsp_g: float | None = None,
    fibre_aoac_g: float | None = None,
    sodium_mg: float | None = None,
    salt_g: float | None = None,
    is_drink: bool = False,
) -> NPMResult:
    """Calculate an NPM 2004/05 score from per-100 g nutrient values.

    Exactly one of ``sodium_mg`` and ``salt_g`` must be supplied.
    Exactly one of ``fibre_nsp_g`` and ``fibre_aoac_g`` must be supplied;
    the guidance prefers NSP where it is known.
    """
    if (sodium_mg is None) == (salt_g is None):
        raise ValueError("Supply exactly one of sodium_mg or salt_g.")
    if sodium_mg is None:
        sodium_mg = sodium_mg_from_salt_g(float(salt_g))
    if (fibre_nsp_g is None) == (fibre_aoac_g is None):
        raise ValueError("Supply exactly one of fibre_nsp_g or fibre_aoac_g.")
    fibre_method = "nsp" if fibre_nsp_g is not None else "aoac"
    fibre_g = fibre_nsp_g if fibre_nsp_g is not None else fibre_aoac_g

    inputs = {
        "energy_kj": energy_kj,
        "saturated_fat_g": saturated_fat_g,
        "total_sugars_g": total_sugars_g,
        "fruit_veg_nuts_percent": fruit_veg_nuts_percent,
        "fibre_g": fibre_g,
        "protein_g": protein_g,
        "sodium_mg": sodium_mg,
    }
    for name, value in inputs.items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative.")
    if fruit_veg_nuts_percent > 100:
        raise ValueError("fruit_veg_nuts_percent cannot exceed 100.")

    a_points = {
        "energy": _band_points(energy_kj, _ENERGY_THRESHOLDS),
        "saturated_fat": _band_points(saturated_fat_g, _SATURATED_FAT_THRESHOLDS),
        "total_sugars": _band_points(total_sugars_g, _TOTAL_SUGAR_THRESHOLDS),
        "sodium": _band_points(sodium_mg, _SODIUM_THRESHOLDS),
    }
    total_a = sum(a_points.values())

    fvn_points = _fruit_veg_nut_points(fruit_veg_nuts_percent)
    protein_points = _band_points(protein_g, _PROTEIN_THRESHOLDS)
    # The protein rule: at 11+ A points, protein only counts when the food
    # also scores the maximum 5 points for fruit, vegetables and nuts.
    protein_counted = not (total_a >= 11 and fvn_points < 5)
    if not protein_counted:
        protein_points = 0

    c_points = {
        "fruit_veg_nuts": fvn_points,
        "fibre": _band_points(fibre_g, _FIBRE_THRESHOLDS[fibre_method]),
        "protein": protein_points,
    }
    score = total_a - sum(c_points.values())
    threshold = 1 if is_drink else 4

    return NPMResult(
        a_points=a_points,
        c_points=c_points,
        protein_counted=protein_counted,
        fibre_method=fibre_method,
        score=score,
        is_drink=is_drink,
        less_healthy=score >= threshold,
    )
