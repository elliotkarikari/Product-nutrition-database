import json
import threading
import unittest
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

    def test_per_100ml_basis_is_rejected_not_relabelled(self):
        with self.assertRaisesRegex(ValueError, "per_100g"):
            assess_product({**SWEET_DRINK, "basis": "per_100ml"})
        with self.assertRaises(ValueError):
            assess_product({**BEANS, "basis": "per_portion"})
        self.assertEqual(assess_product({**BEANS, "basis": "per_100g"})["score"], -2)

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


if __name__ == "__main__":
    unittest.main()
