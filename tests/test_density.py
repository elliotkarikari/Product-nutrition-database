"""Per-100 ml to per-100 g conversion, reconciled with the NPM guidance.

Physics: 100 ml of a product with specific gravity G (g/ml) weighs 100 G g,
so value per 100 g = value per 100 ml / G. ShelfScale divides.

Worked example 3 (powdered milkshake) converts 200 ml of semi-skimmed milk
to grams by multiplying by the gravity (200 ml x 1.034 = 206.8 g; the
guidance prints the gravity as "0.034", a typo its own arithmetic
contradicts). Volume times density is mass, which is right, and dividing
per-100 ml values reproduces the example's per-100 g figures exactly.

Worked examples 2 and 6 instead multiply per-100 ml nutrient values by the
gravity to get per-100 g values. That inverts the conversion. For example 6
the score is the same either way; the per-100 g values are not.
"""

import unittest

from shelfscale.npm import calculate_npm
from shelfscale.service import assess_product

MILK_GRAVITY = 1.034
# Guidance example 3, column B: 200 ml semi-skimmed milk (206.8 g).
MILK_PER_200ML = dict(energy_kj=417, saturated_fat_g=2.3, total_sugars_g=5,
                      sodium_mg=91, protein_g=7)
# Column A: 15 g milkshake powder.
POWDER_15G = dict(energy_kj=247, saturated_fat_g=0, total_sugars_g=14.7,
                  sodium_mg=0, protein_g=0)


def _milk_payload():
    per_100ml = {k: v / 2 for k, v in MILK_PER_200ML.items()}
    return {
        "id": "semi-skimmed-milk",
        "is_drink": True,
        "basis": "per_100ml",
        "specific_gravity": MILK_GRAVITY,
        "nutrients": {**per_100ml, "fruit_veg_nuts_percent": 0, "fibre_aoac_g": 0},
    }


class TestExample3Reconciliation(unittest.TestCase):
    def test_dividing_reproduces_the_guidance_milk_per_100g(self):
        result = assess_product(_milk_payload())
        conversion = result["input_conversion"]
        self.assertEqual(conversion["specific_gravity"], MILK_GRAVITY)
        grams_of_milk = 200 * MILK_GRAVITY  # 206.8 g, as the guidance says
        self.assertAlmostEqual(grams_of_milk, 206.8)
        for name, amount in MILK_PER_200ML.items():
            with self.subTest(nutrient=name):
                guidance_per_100g = amount / grams_of_milk * 100
                self.assertAlmostEqual(
                    conversion["values"][name]["per_100g"], guidance_per_100g, places=9)

    def test_example_3_end_to_end(self):
        milk_per_100g = assess_product(_milk_payload())["input_conversion"]["values"]
        grams_of_milk = 200 * MILK_GRAVITY
        total_g = 15 + grams_of_milk
        mixed = {
            name: (POWDER_15G[name] + milk_per_100g[name]["per_100g"] * grams_of_milk / 100)
            / total_g * 100
            for name in POWDER_15G
        }
        # Guidance column D, rounded as printed.
        self.assertEqual(round(mixed["energy_kj"]), 299)
        self.assertEqual(round(mixed["saturated_fat_g"], 1), 1.0)
        self.assertEqual(round(mixed["total_sugars_g"], 1), 8.9)
        self.assertEqual(round(mixed["sodium_mg"]), 41)
        self.assertEqual(round(mixed["protein_g"], 1), 3.2)
        # Scored on the guidance's printed (1-decimal) column D: A 1, C 1, score 0.
        printed = {name: round(value, 1) for name, value in mixed.items()}
        rounded = calculate_npm(**printed, fruit_veg_nuts_percent=0, fibre_aoac_g=0.5,
                                is_drink=True)
        self.assertEqual((rounded.total_a, rounded.total_c, rounded.score), (1, 1, 0))
        self.assertFalse(rounded.less_healthy)
        # Scored unrounded, saturated fat is 2.3 / 221.8 x 100 = 1.037 g, over the
        # 1 g band edge: A 2, score 1, and as a drink that is "less healthy".
        # The guidance never states a rounding rule; its result depends on one.
        # ShelfScale scores values as supplied until Elliot decides (SPEC s.7).
        exact = calculate_npm(**mixed, fruit_veg_nuts_percent=0, fibre_aoac_g=0.5,
                              is_drink=True)
        self.assertAlmostEqual(mixed["saturated_fat_g"], 1.037, places=3)
        self.assertEqual((exact.total_a, exact.total_c, exact.score), (2, 1, 1))
        self.assertTrue(exact.less_healthy)


class TestExample6UnderDivision(unittest.TestCase):
    def test_same_score_different_values(self):
        result = assess_product({
            "id": "raspberry-cranberry-juice-drink",
            "is_drink": True,
            "basis": "per_100ml",
            "specific_gravity": 1.04,
            "nutrients": {"energy_kj": 177, "saturated_fat_g": 0, "total_sugars_g": 9.9,
                          "sodium_mg": 0, "protein_g": 0.1,
                          "fruit_veg_nuts_percent": 15, "fibre_aoac_g": 0},
        })
        values = result["input_conversion"]["values"]
        self.assertAlmostEqual(values["energy_kj"]["per_100g"], 177 / 1.04)   # 170.2
        self.assertAlmostEqual(values["total_sugars_g"]["per_100g"], 9.9 / 1.04)
        # The guidance's own column reads 184 kJ and 10.3 g (multiplied).
        self.assertNotAlmostEqual(values["energy_kj"]["per_100g"], 184, places=0)
        self.assertEqual(result["score"], 2)
        self.assertTrue(result["less_healthy"])
        self.assertEqual(result["input_conversion"]["unchanged"], ["fruit_veg_nuts_percent"])


if __name__ == "__main__":
    unittest.main()
