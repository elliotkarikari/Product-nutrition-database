"""NPM 2018 shadow model against DHSC's own documents (27 January 2026).

Worked examples: "Nutrient profiling model 2018: worked examples and further
advice on calculations", examples 1 to 17. Inputs are each example's own
per-100 g column; expected points and scores are the printed ones. Where the
document prints "less than 0.5" or "less than 0.01", the test uses that
bound, which scores 0 either way.

Band tables below are typed from the technical guidance, Tables 1 and 2,
independently of the module's constants.
"""

import unittest

from shelfscale.npm2018 import calculate_npm2018

# name, is_drink, inputs, expected A points, expected C points, score
EXAMPLES = [
    ("1 oat-based drink", True,
     dict(energy_kj=189, saturated_fat_g=0.3, free_sugars_g=4.5, salt_g=0.1, fvns_g=0, fibre_aoac_g=0.5, protein_g=1.3),
     dict(energy=0, saturated_fat=0, free_sugars=4, salt=0), dict(fruit_veg_nuts_seeds=0, fibre=0, protein=0), 4),
    ("2 lemonade", True,
     dict(energy_kj=42, saturated_fat_g=0, free_sugars_g=2.45, salt_g=0.02, fvns_g=5, fibre_aoac_g=0, protein_g=0),
     dict(energy=0, saturated_fat=0, free_sugars=2, salt=0), dict(fruit_veg_nuts_seeds=0, fibre=0, protein=0), 2),
    ("3 dilutable blackcurrant, reconstituted", True,
     dict(energy_kj=120, saturated_fat_g=0, free_sugars_g=7.0, salt_g=0.01, fvns_g=5, fibre_aoac_g=0, protein_g=0),
     dict(energy=0, saturated_fat=0, free_sugars=7, salt=0), dict(fruit_veg_nuts_seeds=0, fibre=0, protein=0), 7),
    ("4 passion fruit yoghurt drink", True,
     dict(energy_kj=200, saturated_fat_g=0.7, free_sugars_g=6.07, salt_g=0.1, fvns_g=10, fibre_aoac_g=0, protein_g=3.1),
     dict(energy=0, saturated_fat=0, free_sugars=6, salt=0), dict(fruit_veg_nuts_seeds=0, fibre=0, protein=1), 5),
    ("5 chocolate milk-based drink", True,
     dict(energy_kj=262, saturated_fat_g=1.26, free_sugars_g=5.83, salt_g=0.13, fvns_g=0, fibre_aoac_g=0, protein_g=3.0),
     dict(energy=0, saturated_fat=1, free_sugars=6, salt=0), dict(fruit_veg_nuts_seeds=0, fibre=0, protein=1), 6),
    ("6 strawberry milkshake, reconstituted", True,
     dict(energy_kj=294, saturated_fat_g=1.1, free_sugars_g=6.24, salt_g=0.05, fvns_g=0, fibre_aoac_g=0.1, protein_g=3.3),
     dict(energy=0, saturated_fat=1, free_sugars=6, salt=0), dict(fruit_veg_nuts_seeds=0, fibre=0, protein=1), 6),
    ("7 canned pineapple in juice", False,
     dict(energy_kj=219, saturated_fat_g=0.5, free_sugars_g=4.62, salt_g=0.01, fvns_g=100, fibre_aoac_g=0.6, protein_g=0.3),
     dict(energy=0, saturated_fat=0, free_sugars=5, salt=0), dict(fruit_veg_nuts_seeds=5, fibre=0, protein=0), 0),
    ("8 hummus", False,
     dict(energy_kj=1251, saturated_fat_g=2.6, free_sugars_g=0.48, salt_g=0.9, fvns_g=73, fibre_aoac_g=4.9, protein_g=6.9),
     dict(energy=3, saturated_fat=2, free_sugars=0, salt=3), dict(fruit_veg_nuts_seeds=2, fibre=8, protein=4), -6),
    ("9 chunky vegetable soup", False,
     dict(energy_kj=212, saturated_fat_g=0.1, free_sugars_g=2.01, salt_g=0.40, fvns_g=59, fibre_aoac_g=2.3, protein_g=2.8),
     dict(energy=0, saturated_fat=0, free_sugars=2, salt=1), dict(fruit_veg_nuts_seeds=1, fibre=3, protein=1), -2),
    ("10 chicken korma and rice", False,
     dict(energy_kj=591, saturated_fat_g=2.4, free_sugars_g=0.51, salt_g=0.45, fvns_g=9.7, fibre_aoac_g=2.9, protein_g=8.3),
     dict(energy=1, saturated_fat=2, free_sugars=0, salt=1), dict(fruit_veg_nuts_seeds=0, fibre=4, protein=4), -4),
    ("11 strawberry fromage frais (50 g pot, per 100 g)", False,
     dict(energy_kj=368, saturated_fat_g=1.8, free_sugars_g=7.49, salt_g=0.16, fvns_g=8, fibre_aoac_g=0, protein_g=5.2),
     dict(energy=1, saturated_fat=1, free_sugars=8, salt=0), dict(fruit_veg_nuts_seeds=0, fibre=0, protein=3), 7),
    ("12 cereal bar (protein rule)", False,
     dict(energy_kj=1495, saturated_fat_g=1.1, free_sugars_g=28.36, salt_g=0.49, fvns_g=21, fibre_aoac_g=2.6, protein_g=4.2),
     dict(energy=4, saturated_fat=1, free_sugars=10, salt=1), dict(fruit_veg_nuts_seeds=0, fibre=4, protein=0), 12),
    ("13 teacake", False,
     dict(energy_kj=1146, saturated_fat_g=1.4, free_sugars_g=4.0, salt_g=0.65, fvns_g=43, fibre_aoac_g=3.5, protein_g=7.5),
     dict(energy=3, saturated_fat=1, free_sugars=4, salt=2), dict(fruit_veg_nuts_seeds=1, fibre=5, protein=4), 0),
    ("14 cheese containing fruit (protein rule)", False,
     dict(energy_kj=1531, saturated_fat_g=17.1, free_sugars_g=4.2, salt_g=1.0, fvns_g=25, fibre_aoac_g=1.7, protein_g=17.5),
     dict(energy=4, saturated_fat=10, free_sugars=4, salt=4), dict(fruit_veg_nuts_seeds=0, fibre=2, protein=0), 20),
    ("15 chocolate covered biscuit (protein rule)", False,
     dict(energy_kj=2044, saturated_fat_g=11.4, free_sugars_g=25, salt_g=0.83, fvns_g=0, fibre_aoac_g=2.3, protein_g=6.5),
     dict(energy=6, saturated_fat=10, free_sugars=10, salt=3), dict(fruit_veg_nuts_seeds=0, fibre=3, protein=0), 26),
    ("16 strawberry jelly, reconstituted", False,
     dict(energy_kj=287, saturated_fat_g=0, free_sugars_g=13.65, salt_g=0.07, fvns_g=0, fibre_aoac_g=0, protein_g=1.2),
     dict(energy=0, saturated_fat=0, free_sugars=10, salt=0), dict(fruit_veg_nuts_seeds=0, fibre=0, protein=0), 10),
    ("17 vanilla ice cream (protein rule)", False,
     dict(energy_kj=644, saturated_fat_g=3.6, free_sugars_g=21.5, salt_g=0.10, fvns_g=0, fibre_aoac_g=0.3, protein_g=1.8),
     dict(energy=2, saturated_fat=3, free_sugars=10, salt=0), dict(fruit_veg_nuts_seeds=0, fibre=0, protein=0), 15),
]

TABLE_1 = {
    "energy_kj": [315, 630, 945, 1260, 1575, 1890, 2205, 2520, 2835, 3150],
    "saturated_fat_g": [0.9, 1.9, 2.8, 3.7, 4.7, 5.6, 6.6, 7.5, 8.4, 9.4],
    "free_sugars_g": [0.9, 1.9, 2.8, 3.7, 4.6, 5.6, 6.5, 7.4, 8.3, 9.3],
    "salt_g": [0.2, 0.5, 0.7, 0.9, 1.1, 1.4, 1.6, 1.8, 2.0, 2.3],
}
TABLE_2 = {
    "protein_g": [1.7, 3.4, 5.1, 6.8, 8.5],
    "fibre_aoac_g": [0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8, 5.4, 6.0],
}
KEY = {"energy_kj": ("a", "energy"), "saturated_fat_g": ("a", "saturated_fat"),
       "free_sugars_g": ("a", "free_sugars"), "salt_g": ("a", "salt"),
       "protein_g": ("c", "protein"), "fibre_aoac_g": ("c", "fibre")}
ZERO = dict(energy_kj=0, saturated_fat_g=0, free_sugars_g=0, salt_g=0, protein_g=0, fvns_g=0, fibre_aoac_g=0)


class TestWorkedExamples(unittest.TestCase):
    def test_all_17(self):
        self.assertEqual(len(EXAMPLES), 17)
        for name, is_drink, inputs, a, c, score in EXAMPLES:
            with self.subTest(example=name):
                result = calculate_npm2018(is_drink=is_drink, **inputs)
                self.assertEqual(result.a_points, a)
                self.assertEqual(result.c_points, c)
                self.assertEqual(result.score, score)
                self.assertEqual(result.less_healthy, score >= (1 if is_drink else 4))


class TestBandEdges(unittest.TestCase):
    def test_every_edge(self):
        for table in (TABLE_1, TABLE_2):
            for field, bounds in table.items():
                side, key = KEY[field]
                for n, bound in enumerate(bounds):
                    with self.subTest(field=field, bound=bound):
                        at = calculate_npm2018(**{**ZERO, field: bound})
                        over = calculate_npm2018(**{**ZERO, field: bound + 0.001})
                        points = lambda r: (r.a_points if side == "a" else r.c_points)[key]
                        self.assertEqual(points(at), n)
                        self.assertEqual(points(over), n + 1)

    def test_fvns_bands(self):
        for grams, points in [(40, 0), (40.1, 1), (60, 1), (60.1, 2), (80, 2), (80.1, 5), (100, 5)]:
            with self.subTest(grams=grams):
                self.assertEqual(calculate_npm2018(**{**ZERO, "fvns_g": grams}).c_points["fruit_veg_nuts_seeds"], points)

    def test_maximums(self):
        top = calculate_npm2018(energy_kj=9999, saturated_fat_g=99, free_sugars_g=99, salt_g=99,
                                protein_g=99, fvns_g=100, fibre_aoac_g=99)
        self.assertEqual(top.total_a, 40)
        self.assertEqual(top.c_points, {"fruit_veg_nuts_seeds": 5, "fibre": 10, "protein": 5})


class TestRules(unittest.TestCase):
    def test_protein_rule(self):
        high_a = dict(ZERO, energy_kj=3200, free_sugars_g=1.0, protein_g=9)   # A = 10 + 1 = 11
        self.assertFalse(calculate_npm2018(**high_a).protein_counted)
        self.assertTrue(calculate_npm2018(**{**high_a, "fvns_g": 81}).protein_counted)
        self.assertTrue(calculate_npm2018(**{**high_a, "free_sugars_g": 0}).protein_counted)  # A = 10

    def test_thresholds(self):
        self.assertTrue(calculate_npm2018(**{**ZERO, "free_sugars_g": 1.0}, is_drink=True).less_healthy)
        self.assertFalse(calculate_npm2018(**{**ZERO, "free_sugars_g": 3.0}).less_healthy)  # food, 3
        self.assertTrue(calculate_npm2018(**{**ZERO, "free_sugars_g": 3.8}).less_healthy)   # food, 4


if __name__ == "__main__":
    unittest.main()
