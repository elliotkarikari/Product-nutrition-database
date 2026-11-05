"""Dual scoring: NPM 2004/05 (in force) beside NPM 2018 (shadow model).

Free sugars honesty rule (Elliot, November 5, 2026): total sugars are never
used for free sugars; without caller-supplied free_sugars_g there is no
2018 score.

Real verdict change (CoFID 2021, 14-834 Peanuts, roasted and salted,
caller says free sugars 0 g; sugars in whole nuts are not free sugars):
  2004/05: A 7+9+0+4 = 20; C FVN 5, NSP fibre 6.0 -> 5, protein 5 = 15; score 5, less healthy.
  2018:    A 7+10+0+4 = 21 (sat fat 9.5 > 9.4); C FVNS 5, AOAC fibre 8.0 -> 10, protein 5 = 20;
           score 1, not less healthy.
"""

import unittest

from shelfscale.cofid_assess import lookup_and_assess, lookup_bulk
from shelfscale.lookup import cofid_release
from shelfscale.service import assess_bulk, assess_product

OLD, NEW = "uk-npm-2004/05", "uk-npm-2018"

# 2018 worked example 12 (cereal bar), per 100 g, with total sugars for 2004/05.
CEREAL_BAR = {
    "id": "cereal-bar",
    "nutrients": {"energy_kj": 1495, "saturated_fat_g": 1.1, "total_sugars_g": 39,
                  "salt_g": 0.49, "fruit_veg_nuts_percent": 21, "fibre_aoac_g": 2.6,
                  "protein_g": 4.2},
}


def setUpModule():
    cofid_release()


class TestSuppliedMode(unittest.TestCase):
    def test_no_free_sugars_means_no_2018_score(self):
        result = assess_product(CEREAL_BAR)
        new = result["models"][NEW]
        self.assertEqual((new["model"], new["status"]), (NEW, "shadow model, not in force"))
        self.assertFalse(new["scorable"])
        self.assertNotIn("score", new)
        self.assertTrue(any(m.startswith("free_sugars_g") for m in new["missing_inputs"]))
        self.assertIsNone(new["inputs"]["free_sugars_g"]["value"])   # total sugars (39) not used
        self.assertIsNone(result["verdict_changes_under_2018"])
        self.assertTrue(result["models"][OLD]["scorable"])

    def test_caller_free_sugars_scores_worked_example_12(self):
        result = assess_product({**CEREAL_BAR, "nutrients": {
            **CEREAL_BAR["nutrients"], "free_sugars_g": 28.36, "fvns_g": 21}})
        new = result["models"][NEW]
        self.assertTrue(new["scorable"])
        self.assertEqual(new["inputs"]["free_sugars_g"], {"value": 28.36, "source": "caller_supplied"})
        self.assertEqual((new["total_a"], new["protein_counted"], new["score"]), (16, False, 12))
        self.assertTrue(new["less_healthy"])
        self.assertIs(result["verdict_changes_under_2018"], False)

    def test_fvn_percent_stands_in_for_fvns_and_says_so(self):
        result = assess_product({**CEREAL_BAR, "nutrients": {
            **CEREAL_BAR["nutrients"], "free_sugars_g": 28.36}})
        self.assertIn("does not count seeds", result["models"][NEW]["inputs"]["fvns_g"]["source"])

    def test_nsp_only_is_not_converted(self):
        nutrients = {k: v for k, v in CEREAL_BAR["nutrients"].items() if k != "fibre_aoac_g"}
        result = assess_product({**CEREAL_BAR, "nutrients": {**nutrients, "fibre_nsp_g": 2.0,
                                                             "free_sugars_g": 28.36}})
        new = result["models"][NEW]
        self.assertFalse(new["scorable"])
        self.assertTrue(any("no conversion factor" in m for m in new["missing_inputs"]))

    def test_sodium_becomes_salt_and_says_so(self):
        nutrients = {k: v for k, v in CEREAL_BAR["nutrients"].items() if k != "salt_g"}
        result = assess_product({**CEREAL_BAR, "nutrients": {**nutrients, "sodium_mg": 196,
                                                             "free_sugars_g": 28.36}})
        salt = result["models"][NEW]["inputs"]["salt_g"]
        self.assertAlmostEqual(salt["value"], 0.49)
        self.assertIn("salt = sodium x 2.5", salt["source"])

    def test_worked_example_17_through_volume_conversion(self):
        # Example 17 divides 393 kJ/100 ml by specific gravity 0.61 (644 kJ/100 g).
        # The other per-100 ml values here are the example's per-100 g column x 0.61.
        g = 0.61
        result = assess_product({
            "id": "vanilla-ice-cream", "basis": "per_100ml", "specific_gravity": g,
            "is_drink": False,
            "nutrients": {"energy_kj": 393, "saturated_fat_g": 3.6 * g, "total_sugars_g": 21.5 * g,
                          "free_sugars_g": 21.5 * g, "salt_g": 0.10 * g, "protein_g": 1.8 * g,
                          "fibre_aoac_g": 0.3 * g, "fruit_veg_nuts_percent": 0, "fvns_g": 0},
        })
        self.assertAlmostEqual(result["input_conversion"]["values"]["energy_kj"]["per_100g"], 393 / g)
        new = result["models"][NEW]
        self.assertEqual(new["a_points"], {"energy": 2, "saturated_fat": 3, "free_sugars": 10, "salt": 0})
        self.assertEqual(new["score"], 15)

    def test_bulk_counts_per_model(self):
        result = assess_bulk({"products": [
            CEREAL_BAR,
            {**CEREAL_BAR, "id": "with-free-sugars",
             "nutrients": {**CEREAL_BAR["nutrients"], "free_sugars_g": 28.36}},
        ]})
        self.assertEqual(result["models"], [OLD, NEW])
        self.assertEqual(result["summary"]["scorable"], {OLD: 2, NEW: 1})
        self.assertEqual(result["summary"]["verdict_changes_under_2018"], 0)


class TestLookupMode(unittest.TestCase):
    def test_cofid_food_is_not_scorable_under_2018_without_free_sugars(self):
        a = lookup_and_assess({"code": "14-834"})["matches"][0]["assessment"]
        new = a["models"][NEW]
        self.assertFalse(new["scorable"])
        self.assertEqual(len(new["missing_inputs"]), 1)
        self.assertTrue(new["missing_inputs"][0].startswith("free_sugars_g"))
        self.assertIn("total sugars, not free sugars", new["free_sugars_note"])
        self.assertTrue(a["models"][OLD]["less_healthy"])
        self.assertIsNone(a["verdict_changes_under_2018"])

    def test_real_verdict_change_salted_peanuts(self):
        a = lookup_and_assess({"code": "14-834", "free_sugars_g": 0})["matches"][0]["assessment"]
        old, new = a["models"][OLD], a["models"][NEW]
        self.assertEqual((old["score"], old["less_healthy"]), (5, True))
        self.assertEqual((new["score"], new["less_healthy"]), (1, False))
        self.assertEqual(new["c_points"]["fibre"], 10)
        self.assertEqual(new["inputs"]["fibre_aoac_g"]["source"], "CoFID AOACFIB (number)")
        self.assertEqual(new["inputs"]["free_sugars_g"]["source"], "caller_supplied")
        self.assertIs(a["verdict_changes_under_2018"], True)
        self.assertNotIn("free_sugars_note", new)

    def test_bulk_counts_verdict_changes(self):
        body = lookup_bulk({"items": [{"code": "14-834", "free_sugars_g": 0}, {"code": "14-834"}]})
        self.assertEqual(body["summary"]["verdict_changes_under_2018"], 1)
        self.assertEqual(body["summary"]["scorable"], {OLD: 2, NEW: 1})


if __name__ == "__main__":
    unittest.main()
