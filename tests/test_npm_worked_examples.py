"""NPM 2004/05 worked examples from the Department of Health guidance.

Source: "Nutrient Profiling Technical Guidance", Department of Health,
January 2011, section 4 (worked examples 1 to 6), pages 14 to 18.
Retrieved 2026-11-05 from GOV.UK:
https://assets.publishing.service.gov.uk/media/695e87982a4a53b73d513855/NutrientProfilingModel_2004_2005_TechnicalGuidance.pdf
sha256 14ae1fe9bcac3a7a92e830566f899414c75e6d3a934a088456f83999a39ac71c

Inputs are the guidance's own per-100 g column for each example. The
guidance scores per 100 g for food and drink alike; examples 2 and 6
convert per-100 ml label values to per 100 g by specific gravity first.

Expected values are the guidance's printed points, not recomputed ones.
"""

import unittest

from shelfscale.npm import calculate_npm

# (name, inputs, expected A points by nutrient, expected C points, score, is_drink, less_healthy)
WORKED_EXAMPLES = [
    (
        "1 fruit fromage frais (portion < 100 g)",
        dict(energy_kj=459, saturated_fat_g=1.8, total_sugars_g=13.4,
             sodium_mg=0.1, fruit_veg_nuts_percent=8, fibre_aoac_g=0.6,
             protein_g=6.5),
        dict(energy=1, saturated_fat=1, total_sugars=2, sodium=0),
        dict(fruit_veg_nuts=0, fibre=0, protein=4),
        0, False, False,
    ),
    (
        "2 vanilla ice cream (per 100 ml converted, NSP fibre)",
        dict(energy_kj=741, saturated_fat_g=6.1, total_sugars_g=18.7,
             sodium_mg=60, fruit_veg_nuts_percent=0, fibre_nsp_g=0,
             protein_g=3.6),
        dict(energy=2, saturated_fat=6, total_sugars=4, sodium=0),
        dict(fruit_veg_nuts=0, fibre=0, protein=0),
        12, False, True,
    ),
    (
        "3 powdered milkshake, reconstituted (drink)",
        dict(energy_kj=299, saturated_fat_g=1.0, total_sugars_g=8.9,
             sodium_mg=41, fruit_veg_nuts_percent=0, fibre_aoac_g=0.5,
             protein_g=3.2),
        dict(energy=0, saturated_fat=0, total_sugars=1, sodium=0),
        dict(fruit_veg_nuts=0, fibre=0, protein=1),
        0, True, False,
    ),
    (
        "4 tomato cup soup, reconstituted",
        dict(energy_kj=155, saturated_fat_g=0.4, total_sugars_g=3.6,
             sodium_mg=471, fruit_veg_nuts_percent=0, fibre_aoac_g=0.2,
             protein_g=0.3),
        dict(energy=0, saturated_fat=0, total_sugars=0, sodium=5),
        dict(fruit_veg_nuts=0, fibre=0, protein=0),
        5, False, True,
    ),
    (
        "5 fruit and nut cereal bar (dried fruit doubled)",
        dict(energy_kj=1504, saturated_fat_g=1.4, total_sugars_g=35.7,
             sodium_mg=0, fruit_veg_nuts_percent=46, fibre_aoac_g=4.8,
             protein_g=4.3),
        dict(energy=4, saturated_fat=1, total_sugars=7, sodium=0),
        dict(fruit_veg_nuts=1, fibre=5, protein=0),
        6, False, True,
    ),
    (
        "6 raspberry and cranberry juice drink (drink)",
        dict(energy_kj=184, saturated_fat_g=0, total_sugars_g=10.3,
             sodium_mg=0, fruit_veg_nuts_percent=15, fibre_aoac_g=0,
             protein_g=0.1),
        dict(energy=0, saturated_fat=0, total_sugars=2, sodium=0),
        dict(fruit_veg_nuts=0, fibre=0, protein=0),
        2, True, True,
    ),
]


class TestWorkedExamples(unittest.TestCase):
    def test_every_worked_example(self):
        for name, inputs, a, c, score, is_drink, less_healthy in WORKED_EXAMPLES:
            with self.subTest(example=name):
                result = calculate_npm(is_drink=is_drink, **inputs)
                self.assertEqual(result.a_points, a)
                self.assertEqual(result.c_points, c)
                self.assertEqual(result.total_a, sum(a.values()))
                self.assertEqual(result.total_c, sum(c.values()))
                self.assertEqual(result.score, score)
                self.assertEqual(result.less_healthy, less_healthy)

    def test_example_5_fruit_veg_nut_percentage(self):
        # Guidance formula: (fvn + 2 x dried fvn) / (fvn + 2 x dried + other) x 100
        # with 30 g dried fruit and 70 g other ingredients: 60 / 130 = 46%.
        percent = (0 + 2 * 30) / (0 + 2 * 30 + 70) * 100
        self.assertEqual(round(percent), 46)


# Band tables typed from the guidance (pages 5 and 11), independently of the
# constants in npm.py. Points = number of thresholds the value strictly exceeds.
GUIDANCE_BANDS = {
    "energy_kj": [335, 670, 1005, 1340, 1675, 2010, 2345, 2680, 3015, 3350],
    "saturated_fat_g": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "total_sugars_g": [4.5, 9, 13.5, 18, 22.5, 27, 31, 36, 40, 45],
    "sodium_mg": [90, 180, 270, 360, 450, 540, 630, 720, 810, 900],
    "fibre_nsp_g": [0.7, 1.4, 2.1, 2.8, 3.5],
    "fibre_aoac_g": [0.9, 1.9, 2.8, 3.7, 4.7],
    "protein_g": [1.6, 3.2, 4.8, 6.4, 8.0],
}
POINTS_KEY = {
    "energy_kj": ("a", "energy"),
    "saturated_fat_g": ("a", "saturated_fat"),
    "total_sugars_g": ("a", "total_sugars"),
    "sodium_mg": ("a", "sodium"),
    "fibre_nsp_g": ("c", "fibre"),
    "fibre_aoac_g": ("c", "fibre"),
    "protein_g": ("c", "protein"),
}
ZERO = dict(energy_kj=0, saturated_fat_g=0, total_sugars_g=0, sodium_mg=0,
            fruit_veg_nuts_percent=0, protein_g=0)


def _points(field, value):
    inputs = dict(ZERO)
    inputs[field] = value
    if not field.startswith("fibre"):
        inputs["fibre_aoac_g"] = 0
    result = calculate_npm(**inputs)
    side, key = POINTS_KEY[field]
    return (result.a_points if side == "a" else result.c_points)[key]


class TestBandEdges(unittest.TestCase):
    def test_every_band_edge(self):
        step = 0.001
        for field, thresholds in GUIDANCE_BANDS.items():
            for n, threshold in enumerate(thresholds):
                with self.subTest(field=field, threshold=threshold):
                    self.assertEqual(_points(field, threshold), n)
                    self.assertEqual(_points(field, threshold + step), n + 1)

    def test_fruit_veg_nut_bands(self):
        # 1 point > 40%, 2 points > 60%, 5 points > 80%; no 3 or 4.
        for percent, points in [(40, 0), (40.1, 1), (60, 1), (60.1, 2),
                                (80, 2), (80.1, 5), (100, 5)]:
            with self.subTest(percent=percent):
                result = calculate_npm(**{**ZERO, "fruit_veg_nuts_percent": percent},
                                       fibre_aoac_g=0)
                self.assertEqual(result.c_points["fruit_veg_nuts"], points)

    def test_fibre_basis_must_be_unambiguous(self):
        with self.assertRaises(ValueError):
            calculate_npm(**ZERO)
        with self.assertRaises(ValueError):
            calculate_npm(**ZERO, fibre_nsp_g=1.0, fibre_aoac_g=1.0)

    def test_nsp_and_aoac_scales_differ(self):
        # 3.0 g is 4 points on the NSP scale (> 2.8) but 3 on AOAC (> 2.8, <= 3.7).
        nsp = calculate_npm(**ZERO, fibre_nsp_g=3.0)
        aoac = calculate_npm(**ZERO, fibre_aoac_g=3.0)
        self.assertEqual((nsp.c_points["fibre"], nsp.fibre_method), (4, "nsp"))
        self.assertEqual((aoac.c_points["fibre"], aoac.fibre_method), (3, "aoac"))


if __name__ == "__main__":
    unittest.main()
