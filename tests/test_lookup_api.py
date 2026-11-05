"""Lookup mode through the HTTP API, end to end.

Hand-checked scores (CoFID 2021 values, NPM 2004/05 bands):

Aubergine, flesh and skin, roasted in rapeseed oil (13-669, row 55):
  KJ 260 -> 0; SATFOD 0.35 -> 0; TOTSUG 4.6 -> 1 (> 4.5); NA 2 -> 0.  A = 1.
  FVN 100% (group DG) -> 5; ENGFIB 5.7 -> 5 (> 3.5); PROT 2.1 -> 1 (> 1.6).  C = 11.
  Score 1 - 11 = -10.
Milk, whole, pasteurised, average (12-596), caller-supplied FVN 0:
  KJ 265 -> 0; SATFOD 2.29 -> 2; TOTSUG 4.6 -> 1; NA 42 -> 0.  A = 3.
  FVN 0 -> 0; ENGFIB 0.0 -> 0; PROT 3.4 -> 2 (> 3.2).  C = 2.  Score 1, food, not less healthy.
"""

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from shelfscale.api import Handler
from shelfscale.lookup import cofid_release


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
        self.assertTrue(a["scorable"])
        self.assertEqual(a["a_points"], {"energy": 0, "saturated_fat": 0, "total_sugars": 1, "sodium": 0})
        self.assertEqual(a["c_points"], {"fruit_veg_nuts": 5, "fibre": 5, "protein": 1})
        self.assertEqual(a["score"], -10)
        self.assertEqual(a["fibre_method"], "nsp")
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
        self.assertFalse(a["scorable"])
        self.assertEqual(len(a["missing_inputs"]), 1)
        self.assertTrue(a["missing_inputs"][0].startswith("fruit_veg_nuts_percent"))
        self.assertNotIn("score", a)
        self.assertEqual(a["inputs"]["fruit_veg_nuts_percent"]["source"], "not available")

    def test_caller_supplied_fvn(self):
        status, body = self._post("/v1/lookup", {"code": "12-596", "fvn_percent": 0})
        self.assertEqual(status, 200)
        a = body["matches"][0]["assessment"]
        self.assertTrue(a["scorable"])
        self.assertEqual(a["inputs"]["fruit_veg_nuts_percent"],
                         {"value": 0.0, "source": "caller_supplied"})
        self.assertEqual((a["total_a"], a["total_c"], a["score"]), (3, 2, 1))
        self.assertFalse(a["less_healthy"])

    def test_alcoholic_drink_without_gravity_names_it(self):
        status, body = self._post("/v1/lookup", {"code": "17-506", "fvn_percent": 0})
        a = body["matches"][0]["assessment"]
        self.assertTrue(a["is_drink"])
        self.assertFalse(a["scorable"])
        self.assertTrue(any("specific gravity" in m for m in a["missing_inputs"]))

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
            "foods_matched": 3, "scorable": 3,
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
