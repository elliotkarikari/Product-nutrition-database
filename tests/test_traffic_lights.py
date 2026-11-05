"""Traffic lights against the FoP guidance (November 2016), Annex 3.

Thresholds below are typed from Tables 2 and 3 independently of the
module's constants.
"""

import unittest

from shelfscale.traffic_lights import traffic_lights

FOOD = {"fat": (3.0, 17.5), "saturates": (1.5, 5.0), "sugars": (5.0, 22.5), "salt": (0.3, 1.5)}
DRINK = {"fat": (1.5, 8.75), "saturates": (0.75, 2.5), "sugars": (2.5, 11.25), "salt": (0.3, 0.75)}
FOOD_PORTION_RED = {"fat": 21, "saturates": 6.0, "sugars": 27, "salt": 1.8}
DRINK_PORTION_RED = {"fat": 10.5, "saturates": 3, "sugars": 13.5, "salt": 0.9}
STEP = 0.001


def _colour(is_drink, nutrient, value, portion=None):
    result = traffic_lights(is_drink=is_drink, per_100={nutrient: value}, portion=portion)
    return result["colours"][nutrient]["colour"]


class TestPer100Edges(unittest.TestCase):
    def test_every_edge(self):
        for is_drink, table in ((False, FOOD), (True, DRINK)):
            for nutrient, (low, high) in table.items():
                with self.subTest(drink=is_drink, nutrient=nutrient):
                    self.assertEqual(_colour(is_drink, nutrient, 0), "green")
                    self.assertEqual(_colour(is_drink, nutrient, low), "green")
                    self.assertEqual(_colour(is_drink, nutrient, low + STEP), "amber")
                    self.assertEqual(_colour(is_drink, nutrient, high), "amber")
                    self.assertEqual(_colour(is_drink, nutrient, high + STEP), "red")


class TestPortionRule(unittest.TestCase):
    def test_red_per_portion_edges(self):
        portion = 200   # above both limits (100 g, 150 ml); amount = 2 x per-100 value
        for is_drink, table in ((False, FOOD_PORTION_RED), (True, DRINK_PORTION_RED)):
            for nutrient, red in table.items():
                with self.subTest(drink=is_drink, nutrient=nutrient):
                    at = red / 2
                    # Exactly at the cut-off per portion is not red by the portion rule.
                    result = traffic_lights(is_drink=is_drink, per_100={nutrient: at}, portion=portion)
                    self.assertEqual(result["colours"][nutrient]["decided_by"],
                                     "per_100ml" if is_drink else "per_100g")
                    over = traffic_lights(is_drink=is_drink, per_100={nutrient: at + STEP},
                                          portion=portion)
                    self.assertEqual(over["colours"][nutrient]["colour"], "red")
                    self.assertEqual(over["colours"][nutrient]["decided_by"], "per_portion")

    def test_portion_condition_is_strictly_more_than(self):
        # Food: rule applies above 100 g only. 2.0 g saturates per 100 g is amber;
        # a 400 g portion carries 8 g (> 6 g), so red, but a 100 g portion does not trigger.
        self.assertEqual(_colour(False, "saturates", 2.0, portion=400), "red")
        self.assertEqual(_colour(False, "saturates", 2.0, portion=100), "amber")
        self.assertFalse(traffic_lights(is_drink=False, per_100={}, portion=100)["portion_rule_applied"])
        self.assertTrue(traffic_lights(is_drink=False, per_100={}, portion=100.1)["portion_rule_applied"])
        # Drinks: above 150 ml only.
        self.assertFalse(traffic_lights(is_drink=True, per_100={}, portion=150)["portion_rule_applied"])
        self.assertTrue(traffic_lights(is_drink=True, per_100={}, portion=150.1)["portion_rule_applied"])

    def test_portion_rule_only_raises_to_red(self):
        # Small portion never lowers a per-100 red, and the rule never gives green or amber.
        result = traffic_lights(is_drink=False, per_100={"salt": 2.0}, portion=150)
        self.assertEqual(result["colours"]["salt"]["colour"], "red")


class TestGuidanceWorkedExamples(unittest.TestCase):
    def test_example_a_ready_meal(self):
        result = traffic_lights(
            is_drink=False,
            per_100={"fat": 2.2, "saturates": 0.4, "sugars": 1.5, "salt": 0.35},
            portion=400,
        )
        colours = {n: c["colour"] for n, c in result["colours"].items()}
        self.assertEqual(colours, {"fat": "green", "saturates": "green",
                                   "sugars": "green", "salt": "amber"})
        self.assertTrue(result["portion_rule_applied"])
        self.assertTrue(all(c["decided_by"] == "per_100g" for c in result["colours"].values()))

    def test_example_b_smoothie(self):
        # Salt is "trace" in the guidance; scored as 0.
        result = traffic_lights(
            is_drink=True,
            per_100={"fat": 0.2, "saturates": 0.1, "sugars": 12.0, "salt": 0},
            portion=200,
        )
        colours = {n: c["colour"] for n, c in result["colours"].items()}
        self.assertEqual(colours, {"fat": "green", "saturates": "green",
                                   "sugars": "red", "salt": "green"})
        self.assertEqual(result["colours"]["sugars"]["decided_by"], "per_portion")


class TestShape(unittest.TestCase):
    def test_missing_nutrient_is_not_assessed(self):
        result = traffic_lights(is_drink=False, per_100={"salt": 0.1})
        self.assertIsNone(result["colours"]["fat"]["colour"])
        self.assertIn("not supplied", result["colours"]["fat"]["reason"])

    def test_no_summary_colour(self):
        result = traffic_lights(is_drink=False, per_100={"salt": 0.1})
        self.assertNotIn("summary", result)
        self.assertEqual(result["guidance"]["edition"], "Updated November 2016")


if __name__ == "__main__":
    unittest.main()
