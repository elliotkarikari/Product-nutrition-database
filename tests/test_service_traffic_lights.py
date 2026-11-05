"""Traffic lights in the assessment service output."""

import unittest

from shelfscale.service import assess_product

MEAL = {
    "id": "ready-meal",
    "portion_g": 400,
    "nutrients": {"energy_kj": 353, "fat_g": 2.2, "saturated_fat_g": 0.4,
                  "total_sugars_g": 1.5, "salt_g": 0.35, "fruit_veg_nuts_percent": 0,
                  "fibre_aoac_g": 1.0, "protein_g": 4.0},
}
SMOOTHIE_PER_100ML = {
    "id": "smoothie", "is_drink": True, "basis": "per_100ml", "specific_gravity": 1.05,
    "portion_ml": 200,
    "nutrients": {"energy_kj": 260, "fat_g": 0.2, "saturated_fat_g": 0.1,
                  "total_sugars_g": 12.0, "salt_g": 0, "fruit_veg_nuts_percent": 100,
                  "fibre_aoac_g": 1.0, "protein_g": 0.7},
}


def colours(result):
    return {n: c["colour"] for n, c in result["traffic_lights"]["colours"].items()}


class TestServiceTrafficLights(unittest.TestCase):
    def test_food_matches_guidance_example_a(self):
        result = assess_product(MEAL)
        self.assertEqual(colours(result), {"fat": "green", "saturates": "green",
                                           "sugars": "green", "salt": "amber"})
        self.assertTrue(result["traffic_lights"]["portion_rule_applied"])
        self.assertEqual(result["per_portion"]["fat_g"], 8.8)

    def test_salt_from_sodium(self):
        nutrients = {k: v for k, v in MEAL["nutrients"].items() if k != "salt_g"}
        result = assess_product({**MEAL, "nutrients": {**nutrients, "sodium_mg": 140}})
        self.assertAlmostEqual(result["traffic_lights"]["colours"]["salt"]["per_100g"], 0.35)

    def test_drink_uses_per_100ml_values(self):
        result = assess_product(SMOOTHIE_PER_100ML)
        self.assertEqual(colours(result), {"fat": "green", "saturates": "green",
                                           "sugars": "red", "salt": "green"})
        sugars = result["traffic_lights"]["colours"]["sugars"]
        self.assertEqual((sugars["per_100ml"], sugars["decided_by"]), (12.0, "per_portion"))
        # NPM still scored per 100 g from the converted values.
        self.assertAlmostEqual(result["input_conversion"]["values"]["fat_g"]["per_100g"], 0.2 / 1.05)

    def test_drink_per_100g_is_not_assessed(self):
        payload = {**SMOOTHIE_PER_100ML, "basis": "per_100g"}
        del payload["specific_gravity"]
        result = assess_product(payload)
        self.assertIsNone(result["traffic_lights"]["colours"])
        self.assertIn("per 100 ml", result["traffic_lights"]["not_assessed"])

    def test_missing_fat_is_named(self):
        nutrients = {k: v for k, v in MEAL["nutrients"].items() if k != "fat_g"}
        result = assess_product({**MEAL, "nutrients": nutrients})
        self.assertIsNone(result["traffic_lights"]["colours"]["fat"]["colour"])
        self.assertEqual(result["traffic_lights"]["colours"]["salt"]["colour"], "amber")

    def test_portion_ml_is_for_drinks_only(self):
        with self.assertRaisesRegex(ValueError, "portion_ml"):
            assess_product({**MEAL, "portion_ml": 250})


if __name__ == "__main__":
    unittest.main()
