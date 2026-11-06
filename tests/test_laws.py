"""Law status is configuration: flipping it changes labels and framing, never a score."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shelfscale import laws, recipe
from shelfscale.cofid_assess import lookup_and_assess
from shelfscale.service import assess_product

OLD, NEW = "uk-npm-2004/05", "uk-npm-2018"
PRODUCT = {"id": "flip", "portion_g": 40, "nutrients": {
    "energy_kj": 1090, "fat_g": 1, "saturated_fat_g": 0.15, "total_sugars_g": 62.6, "free_sugars_g": 0,
    "sodium_mg": 17, "fruit_veg_nuts_percent": 100, "fvns_g": 100, "protein_g": 3, "fibre_aoac_g": 2.7}}


def adopted_2018():
    flipped = copy.deepcopy(laws.load())
    flipped[OLD]["status"] = "retired"
    flipped[NEW]["status"] = "in_force"
    return flipped


def strip_law(value):
    """The result with every law label and status text removed."""
    if isinstance(value, dict):
        return {k: strip_law(v) for k, v in value.items() if k not in ("law", "status")}
    if isinstance(value, list):
        return [strip_law(v) for v in value]
    return value


class TestLawConfiguration(unittest.TestCase):
    def test_current_configuration(self):
        self.assertEqual(laws.summary(), {OLD: "in force", NEW: "shadow model, not in force"})
        self.assertEqual((laws.label(OLD)["role"], laws.label(NEW)["role"]), ("today", "coming"))

    def test_adoption_changes_labels_and_framing_not_scores(self):
        before = assess_product(PRODUCT)
        food_before = lookup_and_assess({"code": "14-393", "free_sugars_g": 0})
        cake = {"ingredients": [{"food_id": "11-888", "grams": 200}, {"food_id": "14-393", "grams": 100}],
                "servings": 8, "fvn_percent": 30, "free_sugars_g": 10}
        recipe_before = recipe.calculate(cake)
        with patch.object(laws, "models", adopted_2018):
            after = assess_product(PRODUCT)
            food_after = lookup_and_assess({"code": "14-393", "free_sugars_g": 0})
            recipe_after = recipe.calculate(cake)
            self.assertEqual(laws.summary(), {OLD: "retired, no longer in force", NEW: "in force"})
            self.assertEqual(after["models"][NEW]["law"]["role"], "today")
            self.assertEqual(after["models"][OLD]["law"]["role"], "past")
            self.assertEqual(after["models"][NEW]["status"], "in force")
        self.assertEqual(before["models"][NEW]["law"]["role"], "coming")
        for one, two in ((before, after), (food_before, food_after), (recipe_before, recipe_after)):
            self.assertEqual(strip_law(one), strip_law(two))
        self.assertTrue(before["verdict_changes_under_2018"])  # the fixture is a real flip

    def test_bad_configurations_are_refused(self):
        good = json.loads(laws.CONFIG.read_text())
        cases = []
        two = copy.deepcopy(good); two["models"][NEW]["status"] = "in_force"; cases.append(two)
        odd = copy.deepcopy(good); odd["models"][NEW]["status"] = "pending"; cases.append(odd)
        bare = copy.deepcopy(good); del bare["models"][OLD]["version"]; cases.append(bare)
        for config in cases:
            with tempfile.TemporaryDirectory() as tmp, self.subTest(config=str(config)[:80]):
                path = Path(tmp) / "laws.json"
                path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    laws.load(path)


if __name__ == "__main__":
    unittest.main()
