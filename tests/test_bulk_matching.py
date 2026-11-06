"""Bulk scoring, the matching assistant and products as sold."""
import os
import unittest
from unittest.mock import patch

from shelfscale import as_sold, bulk, matching, ui_api
from shelfscale.cofid_assess import lookup_and_assess
from shelfscale.retail_core import retail_core

OLD, NEW = "uk-npm-2004/05", "uk-npm-2018"
MANGO_WHOLE = "14-379"


def fake_jev(probabilities, model="jev-1.13.0"):
    calls = []

    def post(url, key, body, timeout):
        calls.append((url, key, body))
        return {"model": model, "usage": {"input_tokens": 10, "output_tokens": 2},
                "answers": {q: {"type": "noul", "noul": probabilities[int(q[1:])] if int(q[1:]) < len(probabilities) else 0.0}
                            for q in body["questions"]}}
    return post, calls


class TestMatching(unittest.TestCase):
    def test_without_key_degrades_to_deterministic_and_says_so(self):
        with patch.dict(os.environ, {}, clear=True):
            r = matching.propose("Bananas, raw, flesh only")
        self.assertEqual(r["engine"]["engine"], "deterministic")
        self.assertIn("TYPESAFE_API_KEY is not set", r["engine"]["reason"])
        self.assertEqual(r["candidates"][0]["name"], "Bananas, flesh only")
        self.assertTrue(all(c["verdict"] == "possible" and c["probability"] is None for c in r["candidates"]))
        self.assertEqual(r["status"], "unconfirmed")

    def test_jev_probabilities_gate_proposals_and_name_the_model(self):
        post, calls = fake_jev([0.95, 0.5, 0.05])
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "secret-test-key"}):
            r = matching.propose("Bananas, raw, flesh only", post=post)
        (url, key, body), = calls
        self.assertEqual(url, "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(key, "secret-test-key")
        self.assertEqual(body["model"], "jev-latest")
        self.assertTrue(all(q["type"] == "noul" for q in body["questions"].values()))
        self.assertEqual(r["engine"], {"engine": "jev", "model": "jev-1.13.0"})
        self.assertEqual([c["verdict"] for c in r["candidates"][:3]], ["proposed", "possible", "abstain"])
        self.assertNotIn("secret-test-key", str(r))

    def test_jev_failure_or_bad_answer_degrades(self):
        def broken(*_):
            raise OSError("down")
        bad, _ = fake_jev([1.7])
        for post in (broken, bad):
            with patch.dict(os.environ, {"TYPESAFE_API_KEY": "k"}), self.subTest(post=post):
                r = matching.propose("Leeks, fresh, raw", post=post)
                self.assertEqual(r["engine"]["engine"], "deterministic")
                self.assertNotIn("k", r["engine"].get("model", ""))

    def test_confirmation_records_basis(self):
        food_id = matching.retrieve("Leeks, fresh, raw", 1)[0]["food_id"]
        jev = matching.confirmation({"query": "Leeks, fresh, raw", "food_id": food_id,
                                     "engine": {"engine": "jev", "model": "jev-1.13.0"}, "probability": 0.91})
        self.assertEqual(jev["basis"], "model-proposed (Jev jev-1.13.0, p=0.910), user-confirmed")
        plain = matching.confirmation({"query": "Leeks, fresh, raw", "food_id": food_id})
        self.assertEqual(plain["basis"], "user-selected from deterministic candidates, user-confirmed")
        for bad in ({"query": "x", "food_id": "nope"}, {"query": "", "food_id": food_id},
                    {"query": "x", "food_id": food_id, "engine": {"engine": "jev"}}):
            with self.assertRaises(ValueError):
                matching.confirmation(bad)


class TestBulk(unittest.TestCase):
    ROWS = [{"name": "Jaffa cakes"}, {"name": "Raisins, dried", "free_sugars_g": 0},
            {"code": "11-739", "fvn_percent": 5, "free_sugars_g": 40}, {"name": "rock cakes"},
            {"name": "My flapjack", "energy_kj": 1900, "fat_g": 20, "saturated_fat_g": 9, "total_sugars_g": 30,
             "free_sugars_g": 28, "salt_g": 0.3, "protein_g": 6, "fibre_aoac_g": 4, "fruit_veg_nuts_percent": 0},
            {"name": "Half a flapjack", "energy_kj": 1900}]

    def test_flips_first_gaps_kept_errors_reported(self):
        r = bulk.run({"rows": self.ROWS})
        self.assertEqual(r["rows"][0]["input"], "Raisins, dried")
        self.assertTrue(r["rows"][0]["verdict_changes_under_2018"])
        self.assertEqual(r["summary"]["verdict_changes_under_2018"], 1)
        self.assertEqual([g["input"] for g in r["gaps"]], ["rock cakes"])
        self.assertEqual(r["gaps"][0]["candidates"][0]["name"], "Rock cakes, homemade")
        self.assertEqual([e["index"] for e in r["errors"]], [5])
        self.assertEqual(r["summary"]["received"], 6)

    def test_rows_carry_the_engines_scores_and_their_laws(self):
        r = bulk.run({"rows": self.ROWS})
        raisins = r["rows"][0]
        api = lookup_and_assess({"code": "14-393", "free_sugars_g": 0})["matches"][0]["assessment"]["models"]
        for model in (OLD, NEW):
            self.assertEqual(raisins["models"][model]["score"], api[model]["score"])
            self.assertEqual(raisins["models"][model]["law"]["model"], model)
        self.assertEqual(raisins["models"][NEW]["law"]["status"], "shadow")
        jaffa = next(x for x in r["rows"] if x["input"] == "Jaffa cakes")
        self.assertFalse(jaffa["models"][NEW]["scorable"])
        self.assertTrue(any("free_sugars" in m for m in jaffa["models"][NEW]["missing"]))
        mine = next(x for x in r["rows"] if x["input"] == "My flapjack")
        self.assertIn("not verified", mine["sources"][0])

    def test_confirmed_match_resolves_and_records_basis(self):
        food_id = matching.retrieve("rock cakes", 1)[0]["food_id"]
        r = bulk.run({"rows": [{"name": "rock cakes"}],
                      "confirmed": [{"query": "Rock  cakes", "food_id": food_id}]})
        self.assertEqual(r["summary"]["gaps"], 0)
        self.assertIn("user-confirmed", r["rows"][0]["resolved"]["basis"])

    def test_limits(self):
        with self.assertRaises(ValueError):
            bulk.run({"rows": [{"name": "x"}] * 201})
        with self.assertRaises(ValueError):
            bulk.run({"rows": []})


class TestAsSold(unittest.TestCase):
    def test_retail_core_marks_loose_foods(self):
        core = retail_core()
        self.assertTrue(core["foods"][MANGO_WHOLE]["loose"])
        self.assertIn("Author's retail list", core["source"]["label"])

    def test_draft_links_are_never_applied_on_their_own(self):
        view = ui_api.food(MANGO_WHOLE)["as_sold"]
        self.assertIsNone(view["unit"])
        self.assertIn("does not invent", view["note"])
        self.assertEqual(view["proposed_units"][0]["link"], "draft")

    def test_confirmed_band_crosses_a_threshold_and_names_both_ends(self):
        key = ui_api.food(MANGO_WHOLE)["as_sold"]["proposed_units"][0]["key"]
        food = ui_api.food(MANGO_WHOLE, {"unit": key})
        sold = food["as_sold"]
        unit, band = sold["unit"], sold["band"]
        self.assertEqual(unit["link"], "user_confirmed")
        self.assertEqual(unit["n"], 9)
        self.assertEqual(band["crosses"], ["sugars"])
        self.assertEqual(band["ends"]["low"]["colours"]["sugars"], "amber")
        self.assertEqual(band["ends"]["high"]["colours"]["sugars"], "red")
        self.assertTrue(band["ends"]["high"]["portion_rule_applied"])
        self.assertEqual(food["assessment"], ui_api.food(MANGO_WHOLE)["assessment"])  # verdict does not move

    def test_exact_name_unit_has_a_measured_range(self):
        onion = ui_api.search("Onions, raw")["results"][0]["food_id"]
        sold = ui_api.food(onion)["as_sold"]
        self.assertEqual(sold["kind"], "loose")
        self.assertLess(sold["unit"]["low_g"], sold["unit"]["typical_g"])
        self.assertLess(sold["unit"]["typical_g"], sold["unit"]["high_g"])
        self.assertIn("purchase averages", sold["unit"]["spread"])

    def test_declared_pack_weight_is_labelled_as_yours(self):
        sold = ui_api.food("11-739", {"pack_g": "150"})["as_sold"]
        self.assertEqual(sold["kind"], "packaged")
        self.assertIn("caller-supplied", sold["unit"]["basis"])

    def test_every_link_resolves(self):
        self.assertGreaterEqual(len(as_sold.sample_units()), 30)


if __name__ == "__main__":
    unittest.main()
