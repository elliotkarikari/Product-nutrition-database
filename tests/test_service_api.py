import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from shelfscale.api import Handler
from shelfscale.service import assess_bulk, assess_product

BEANS = {
    "id": "beans-400g",
    "nutrients": {
        "energy_kj": 340,
        "saturated_fat_g": 0.1,
        "total_sugars_g": 5,
        "sodium_mg": 250,
        "fruit_veg_nuts_percent": 50,
        "fibre_aoac_g": 3.7,
        "protein_g": 4.8,
    },
}

SWEET_DRINK = {
    "id": "cola-330ml",
    "is_drink": True,
    "nutrients": {
        "energy_kj": 180,
        "saturated_fat_g": 0,
        "total_sugars_g": 10,
        "salt_g": 0.0,
        "fruit_veg_nuts_percent": 0,
        "fibre_aoac_g": 0,
        "protein_g": 0,
    },
}


class TestService(unittest.TestCase):
    def test_single_assessment(self):
        result = assess_product(BEANS)
        self.assertEqual(result["score"], -2)
        self.assertFalse(result["less_healthy"])
        self.assertEqual(result["model"], "uk-npm-2004/05")

    def test_portion_view(self):
        result = assess_product({**BEANS, "portion_g": 200})
        self.assertEqual(result["per_portion"]["energy_kj"], 680.0)
        self.assertAlmostEqual(result["per_portion"]["salt_g"], 1.25)

    def test_bulk_partial_success(self):
        payload = {
            "products": [
                BEANS,
                SWEET_DRINK,
                {"id": "broken", "nutrients": {"energy_kj": 100}},
            ]
        }
        result = assess_bulk(payload)
        self.assertEqual(result["summary"]["received"], 3)
        self.assertEqual(result["summary"]["assessed"], 2)
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertEqual(result["summary"]["less_healthy"], 1)
        self.assertEqual(result["errors"][0]["id"], "broken")

    def test_basis_is_per_100g_for_drinks_too(self):
        result = assess_product(SWEET_DRINK)
        self.assertEqual(result["basis"], "per_100g")

    def test_per_100ml_needs_specific_gravity(self):
        with self.assertRaisesRegex(ValueError, "specific_gravity"):
            assess_product({**SWEET_DRINK, "basis": "per_100ml"})
        with self.assertRaises(ValueError):
            assess_product({**BEANS, "basis": "per_portion"})
        with self.assertRaisesRegex(ValueError, "only applies"):
            assess_product({**BEANS, "specific_gravity": 1.0})
        for bad in (0, -1, "1.04", True):
            with self.subTest(gravity=bad):
                with self.assertRaisesRegex(ValueError, "specific_gravity"):
                    assess_product({**SWEET_DRINK, "basis": "per_100ml",
                                    "specific_gravity": bad})
        unconverted = assess_product({**BEANS, "basis": "per_100g"})
        self.assertEqual(unconverted["score"], -2)
        self.assertIsNone(unconverted["input_conversion"])

    def test_fibre_nsp_or_aoac_exactly_one(self):
        nsp = assess_product({**BEANS, "nutrients": {
            **{k: v for k, v in BEANS["nutrients"].items() if k != "fibre_aoac_g"},
            "fibre_nsp_g": 3.0}, "portion_g": 100})
        self.assertEqual((nsp["c_points"]["fibre"], nsp["fibre_method"]), (4, "nsp"))
        self.assertEqual(nsp["per_portion"]["fibre_nsp_g"], 3.0)
        aoac = assess_product(BEANS)
        self.assertEqual(aoac["fibre_method"], "aoac")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            assess_product({**BEANS, "nutrients": {**BEANS["nutrients"], "fibre_nsp_g": 3.0}})
        neither = {k: v for k, v in BEANS["nutrients"].items() if k != "fibre_aoac_g"}
        with self.assertRaisesRegex(ValueError, "exactly one"):
            assess_product({**BEANS, "nutrients": neither})

    def test_is_drink_must_be_boolean(self):
        for bad in ("false", "true", 0, 1, None):
            with self.subTest(value=bad):
                with self.assertRaisesRegex(ValueError, "is_drink"):
                    assess_product({**BEANS, "is_drink": bad})
        self.assertFalse(assess_product({**BEANS, "is_drink": False})["less_healthy"])

    def test_bulk_requires_products(self):
        with self.assertRaises(ValueError):
            assess_bulk({"products": []})


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

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
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_health_and_bulk_endpoints(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/health", timeout=5
        ) as response:
            self.assertEqual(json.loads(response.read())["status"], "ok")
        status, body = self._post("/v1/assess/bulk", {"products": [BEANS, SWEET_DRINK]})
        self.assertEqual(status, 200)
        self.assertEqual(body["summary"]["assessed"], 2)
        status, body = self._post("/v1/assess", BEANS)
        self.assertEqual(status, 200)
        self.assertEqual(body["id"], "beans-400g")

    def test_non_boolean_is_drink_is_400(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self._post("/v1/assess", {**BEANS, "is_drink": "false"})
        self.assertEqual(caught.exception.code, 400)
        self.assertIn("is_drink", json.loads(caught.exception.read())["error"])


if __name__ == "__main__":
    unittest.main()
