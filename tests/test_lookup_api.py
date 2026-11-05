"""Lookup mode through the HTTP API, end to end.

Hand-checked scores (CoFID 2021 values, NPM 2004/05 bands):

Aubergine, flesh and skin, roasted in rapeseed oil (13-669, row 55):
  KJ 260 -> 0; SATFOD 0.35 -> 0; TOTSUG 4.6 -> 1 (> 4.5); NA 2 -> 0.  A = 1.
  FVN 100% (group DG) -> 5; ENGFIB 5.7 -> 5 (> 3.5); PROT 2.1 -> 1 (> 1.6).  C = 11.
  Score 1 - 11 = -10.
Milk, whole, pasteurised, average (12-596), caller-supplied FVN 0:
  KJ 265 -> 0; SATFOD 2.29 -> 2; TOTSUG 4.6 -> 1; NA 42 -> 0.  A = 3.
  FVN 0 -> 0; ENGFIB 0.0 -> 0; PROT 3.4 -> 2 (> 3.2).  C = 2.  Score 1, food, not less healthy.
Potato chips, fine cut, from fast food outlets (13-486), group DAP:
  KJ 1219 -> 3; SATFOD 2.5 -> 2; TOTSUG 0.3 -> 0; NA 193 -> 2.  A = 7.
  FVN 0 (potatoes, excluded_by_guidance) -> 0; ENGFIB 3.2 -> 4; PROT 3.5 -> 2.  C = 6.
  Score +1 (was -4 when the group rule gave potatoes 100%).
"""

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from shelfscale.api import Handler
from shelfscale.lookup import cofid_release

OLD, NEW = "uk-npm-2004/05", "uk-npm-2018"


def setUpModule():
    cofid_release()   # build the import once, before the server times requests


class TestLookupApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _post(self, path, payload):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_duplicate_code_returns_both_and_scores_the_hand_checked_one(self):
        status, body = self._post("/v1/lookup", {"code": "13-669"})
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "lookup")
        self.assertEqual(len(body["matches"]), 2)
        self.assertIn("share this food code", body["note"])
        aubergine = next(m for m in body["matches"] if m["food_id"] == "13-669@row55")
        a = aubergine["assessment"]
        m = a["models"][OLD]
        self.assertTrue(m["scorable"])
        self.assertEqual(m["a_points"], {"energy": 0, "saturated_fat": 0, "total_sugars": 1, "sodium": 0})
        self.assertEqual(m["c_points"], {"fruit_veg_nuts": 5, "fibre": 5, "protein": 1})
        self.assertEqual(m["score"], -10)
        self.assertEqual(m["fibre_method"], "nsp")
        self.assertEqual(a["inputs"]["fibre"]["cofid_code"], "ENGFIB")
        self.assertEqual(a["inputs"]["fruit_veg_nuts_percent"]["source"], "derived_from_group")
        self.assertFalse(a["is_drink"])
        self.assertIn("CoFID group is DG", a["drink_status"])
        # Provenance travels with the observations and the release.
        kj = next(o for o in aubergine["observations"] if o["nutrient_code"] == "KJ")
        self.assertEqual((kj["source_id"], kj["edition"], kj["food_code"]),
                         ("uk-cofid-2021", "CoFID 2021", "13-669"))
        self.assertEqual(body["release"]["source_id"], "uk-cofid-2021")
        self.assertTrue(body["release"]["sha256"])
        # Food traffic lights come from the same values (FAT 3.8 g/100 g: amber).
        self.assertEqual(a["traffic_lights"]["colours"]["fat"]["colour"], "amber")

    def test_not_yet_scorable_names_fvn(self):
        status, body = self._post("/v1/lookup", {"code": "12-596"})
        self.assertEqual(status, 200)
        a = body["matches"][0]["assessment"]
        m = a["models"][OLD]
        self.assertFalse(m["scorable"])
        self.assertEqual(len(m["missing_inputs"]), 1)
        self.assertTrue(m["missing_inputs"][0].startswith("fruit_veg_nuts_percent"))
        self.assertNotIn("score", m)
        self.assertIsNone(a["verdict_changes_under_2018"])
        self.assertEqual(a["inputs"]["fruit_veg_nuts_percent"]["source"], "not available")

    def test_caller_supplied_fvn(self):
        status, body = self._post("/v1/lookup", {"code": "12-596", "fvn_percent": 0})
        self.assertEqual(status, 200)
        a = body["matches"][0]["assessment"]
        m = a["models"][OLD]
        self.assertTrue(m["scorable"])
        self.assertEqual(a["inputs"]["fruit_veg_nuts_percent"],
                         {"value": 0.0, "source": "caller_supplied"})
        self.assertEqual((m["total_a"], m["total_c"], m["score"]), (3, 2, 1))
        self.assertFalse(m["less_healthy"])

    def test_potatoes_score_with_fvn_zero_excluded_by_guidance(self):
        status, body = self._post("/v1/lookup", {"code": "13-486"})
        a = body["matches"][0]["assessment"]
        m = a["models"][OLD]
        self.assertTrue(m["scorable"])
        fvn = a["inputs"]["fruit_veg_nuts_percent"]
        self.assertEqual((fvn["value"], fvn["source"]), (0.0, "excluded_by_guidance"))
        self.assertEqual((m["total_a"], m["total_c"], m["score"]), (7, 6, 1))
        self.assertFalse(m["less_healthy"])

    def test_potato_fvn_can_be_overridden_by_the_caller(self):
        status, body = self._post("/v1/lookup", {"code": "13-486", "fvn_percent": 100})
        a = body["matches"][0]["assessment"]
        self.assertEqual(a["inputs"]["fruit_veg_nuts_percent"]["source"], "caller_supplied")
        self.assertEqual(a["models"][OLD]["score"], -4)

    def test_protein_rule_applies_once_potato_fvn_is_zero(self):
        # Chips fried in dripping: A = 15, so with FVN below 5 protein cannot count.
        status, body = self._post("/v1/lookup", {"code": "50-686"})
        m = body["matches"][0]["assessment"]["models"][OLD]
        self.assertEqual((m["total_a"], m["protein_counted"], m["score"]), (15, False, 12))
        self.assertTrue(m["less_healthy"])

    def test_vegetable_dishes_need_caller_fvn(self):
        status, body = self._post("/v1/lookup", {"name": "Aubergine, stuffed with rice"})
        a = body["matches"][0]["assessment"]
        self.assertFalse(a["models"][OLD]["scorable"])
        self.assertIn("vegetable dishes", a["models"][OLD]["missing_inputs"][0])
        status, body = self._post("/v1/lookup", {"name": "Aubergine, stuffed with rice",
                                                 "fvn_percent": 60})
        self.assertTrue(body["matches"][0]["assessment"]["models"][OLD]["scorable"])

    def test_alcoholic_drink_without_gravity_names_it(self):
        status, body = self._post("/v1/lookup", {"code": "17-506", "fvn_percent": 0})
        a = body["matches"][0]["assessment"]
        self.assertTrue(a["is_drink"])
        self.assertFalse(a["models"][OLD]["scorable"])
        self.assertTrue(any("specific gravity" in m for m in a["models"][OLD]["missing_inputs"]))
        self.assertFalse(a["models"][NEW]["applicable"])     # alcoholic: outside NPM 2018

    def test_bulk_partial_success(self):
        status, body = self._post("/v1/lookup/bulk", {"items": [
            {"code": "13-669"},
            {"code": "12-596", "fvn_percent": 0},
            {"code": "99-999"},
            {"code": 12596},
            {"code": "12-596", "name": "Milk, whole, pasteurised, average"},
        ]})
        self.assertEqual(status, 200)
        self.assertEqual(body["summary"], {
            "received": 5, "looked_up": 3, "failed": 2, "no_match": 1,
            "foods_matched": 3,
            "less_healthy": {OLD: 0, NEW: 0},
            "scorable": {OLD: 3, NEW: 0},
            "verdict_changes_under_2018": 0,
        })
        self.assertEqual([e["index"] for e in body["errors"]], [3, 4])
        self.assertIn("string", body["errors"][0]["error"])
        self.assertIn("gap", body["results"][2]["note"])

    def test_bad_requests(self):
        for payload in ({}, {"code": "12-596", "fvn_percent": 101},
                        {"code": "12-596", "portion_g": 0}):
            with self.subTest(payload=payload):
                status, body = self._post("/v1/lookup", payload)
                self.assertEqual(status, 400)
        status, _ = self._post("/v1/lookup/bulk", {"items": []})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
