"""Service-level CoFID lookup (not wired into the HTTP API)."""

import unittest

from shelfscale.lookup import cofid_release, lookup_cofid

DATA = None


def setUpModule():
    global DATA
    DATA = cofid_release()


class TestLookup(unittest.TestCase):
    def test_by_code(self):
        result = lookup_cofid(code="12-596")
        self.assertEqual(len(result["matches"]), 1)
        self.assertIsNone(result["note"])
        food = result["matches"][0]
        self.assertEqual(food["name"], "Milk, whole, pasteurised, average")
        kj = next(o for o in food["observations"] if o["nutrient_code"] == "KJ")
        self.assertEqual((kj["value"], kj["unit"], kj["basis"]), (265.0, "kJ", "per_100g"))
        self.assertEqual((kj["source_id"], kj["edition"]), ("uk-cofid-2021", "CoFID 2021"))
        self.assertEqual(result["release"]["sha256"], DATA.release.sha256)

    def test_by_exact_name(self):
        result = lookup_cofid(name="Ice cream, dairy, vanilla, soft scoop")
        self.assertEqual([m["food_code"] for m in result["matches"]], ["12-508"])
        fibre = {o["nutrient_code"]: (o["method"], o["value_text"])
                 for o in result["matches"][0]["observations"] if o["method"]}
        self.assertEqual(fibre, {"ENGFIB": ("nsp_englyst", "Tr"), "AOACFIB": ("aoac", "0.2")})

    def test_name_is_exact(self):
        self.assertEqual(lookup_cofid(name="milk, whole, pasteurised, average")["matches"], [])

    def test_shared_code_returns_both_foods(self):
        result = lookup_cofid(code="13-669")
        names = sorted(m["name"] for m in result["matches"])
        self.assertEqual(names, ["Aubergine, flesh and skin, roasted in rapeseed oil",
                                 "Watercress, raw"])
        self.assertIn("share this food code", result["note"])

    def test_shared_name_returns_both_foods(self):
        result = lookup_cofid(name="Beef, mince, stewed")
        self.assertEqual(len(result["matches"]), 2)
        self.assertEqual(len({m["food_code"] for m in result["matches"]}), 2)

    def test_unknown_is_a_gap(self):
        result = lookup_cofid(code="99-999")
        self.assertEqual(result["matches"], [])
        self.assertIn("gap", result["note"])

    def test_exactly_one_query(self):
        with self.assertRaises(ValueError):
            lookup_cofid()
        with self.assertRaises(ValueError):
            lookup_cofid(code="12-596", name="Milk, whole, pasteurised, average")


if __name__ == "__main__":
    unittest.main()
