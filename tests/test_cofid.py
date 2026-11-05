"""CoFID 2021 importer.

Count: the user guide and the GOV.UK page state no total, so the count is
taken from the files themselves and cross-checked: all 13 data sheets list
the same 2,887 foods on the same rows (the importer refuses otherwise), and
2,886 distinct codes, because 13-669 names two different foods.

Spot-check expected values were read from the raw workbook with a second,
independent parser (openpyxl) during development. They prove the importer
reads the file faithfully; they are not an independent check of CoFID.
"""

import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from shelfscale.cofid import DEFAULT_SNAPSHOT, load_release
from shelfscale.cofid import import_cofid

DATA = None


def setUpModule():
    global DATA
    DATA = import_cofid()


def _values(food_id):
    return {
        o.definition.code: o.value_text
        for o in DATA.observations
        if o.food.food_id == food_id
    }


class TestCount(unittest.TestCase):
    def test_food_count_from_the_files(self):
        self.assertEqual(len(DATA.foods), 2887)
        self.assertEqual(len({f.food_id for f in DATA.foods}), 2887)
        codes = Counter(f.source_code for f in DATA.foods)
        self.assertEqual(len(codes), 2886)
        self.assertEqual([c for c, n in codes.items() if n > 1], ["13-669"])

    def test_every_food_has_observations(self):
        with_obs = {o.food.food_id for o in DATA.observations}
        self.assertEqual(with_obs, {f.food_id for f in DATA.foods})

    def test_alcoholic_beverages_are_per_100ml(self):
        alcoholic = {f.food_id for f in DATA.foods if (f.group or "").startswith("Q")}
        self.assertEqual(len(alcoholic), 31)
        for o in DATA.observations:
            if o.food.food_id in alcoholic and o.basis not in ("per_100g_fatty_acids", "food_factor"):
                self.assertEqual(o.basis, "per_100ml")
            if o.basis == "per_100ml":
                self.assertIn(o.food.food_id, alcoholic)


class TestSpotChecks(unittest.TestCase):
    EXPECTED = {
        "13-145": ("Ackee, canned, drained",
                   {"KJ": "625", "PROT": "2.9", "FAT": "15.2", "TOTSUG": "0.8",
                    "ENGFIB": "N", "SATFOD": "N", "NA": "240"}),
        "12-596": ("Milk, whole, pasteurised, average",
                   {"KJ": "265", "PROT": "3.4", "FAT": "3.6", "TOTSUG": "4.6",
                    "SATFOD": "2.29", "NA": "42", "ENGFIB": "0.0", "AOACFIB": "0.0"}),
        "12-313": ("Milk, semi-skimmed, pasteurised, average",
                   {"KJ": "195", "PROT": "3.5", "FAT": "1.7", "TOTSUG": "4.7",
                    "SATFOD": "1.07", "NA": "43"}),
        "12-508": ("Ice cream, dairy, vanilla, soft scoop",
                   {"KJ": "711", "PROT": "3.2", "FAT": "8.2", "TOTSUG": "22.0",
                    "SATFOD": "5.19", "NA": "63", "ENGFIB": "Tr", "AOACFIB": "0.2"}),
    }

    def test_named_foods(self):
        for code, (name, expected) in self.EXPECTED.items():
            with self.subTest(code=code):
                food = next(f for f in DATA.foods if f.food_id == code)
                self.assertEqual(food.name, name)
                values = _values(code)
                for nutrient, text in expected.items():
                    self.assertEqual(values[nutrient], text, nutrient)

    def test_watercress_numeric_cells(self):
        # Corrected in the 2021 update; stored as numeric cells, not text.
        values = _values("13-669@row2827")
        self.assertEqual(float(values["KJ"]), 43)
        self.assertEqual(float(values["ENGFIB"]), 1.5)
        self.assertEqual(float(values["AOACFIB"]), 1.5)
        self.assertEqual(values["TOTSUG"], "Tr")

    def test_value_kinds(self):
        kinds = Counter(o.value_kind for o in DATA.observations)
        self.assertEqual(set(kinds), {"number", "number_bracketed", "trace",
                                      "present_not_quantified"})
        self.assertEqual(kinds["number_bracketed"], 14)
        for o in DATA.observations:
            if o.value_kind in ("trace", "present_not_quantified"):
                self.assertIsNone(o.value)
            else:
                self.assertIsNotNone(o.value)


class TestFibre(unittest.TestCase):
    def test_nsp_and_aoac_stay_separate(self):
        methods = {d.code: d.method for d in DATA.definitions if d.method}
        self.assertEqual(methods, {"ENGFIB": "nsp_englyst", "AOACFIB": "aoac"})
        per_food = Counter(
            (o.food.food_id, o.definition.code)
            for o in DATA.observations if o.definition.method
        )
        self.assertTrue(all(n == 1 for n in per_food.values()))
        # Where both exist they are two observations, each with its own text.
        both = [f for f in DATA.foods
                if (f.food_id, "ENGFIB") in per_food and (f.food_id, "AOACFIB") in per_food]
        self.assertGreater(len(both), 0)
        self.assertEqual(Counter(c for _, c in per_food)["ENGFIB"], 2882)
        self.assertEqual(Counter(c for _, c in per_food)["AOACFIB"], 2019)


class TestProvenance(unittest.TestCase):
    def test_no_observation_without_source_and_edition(self):
        for o in DATA.observations:
            self.assertTrue(o.release.source_id)
            self.assertTrue(o.release.edition)
            self.assertTrue(o.release.sha256)
            self.assertTrue(o.release.url)
            self.assertTrue(o.release.retrieved)
            self.assertTrue(o.food.source_code)
            self.assertTrue(o.definition.code)
            self.assertTrue(o.definition.table)
            self.assertTrue(o.value_text.strip())
            self.assertIn(o.basis, ("per_100g", "per_100ml", "per_100g_fatty_acids",
                                    "food_factor"))
        self.assertEqual(DATA.release.source_id, "uk-cofid-2021")
        self.assertEqual(DATA.release.edition, "CoFID 2021")

    def test_manifest_matches_register_and_files(self):
        manifest = json.loads((DEFAULT_SNAPSHOT / "MANIFEST.json").read_text())
        register = (Path(__file__).resolve().parent.parent / "data" / "source-register.yaml").read_text()
        self.assertIn(f"  - id: {manifest['source_id']}\n", register)
        for entry in manifest["files"]:
            self.assertTrue((DEFAULT_SNAPSHOT / entry["name"]).exists(), entry["name"])

    def test_refuses_a_file_that_does_not_match_the_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            manifest = json.loads((DEFAULT_SNAPSHOT / "MANIFEST.json").read_text())
            for entry in manifest["files"]:
                shutil.copy(DEFAULT_SNAPSHOT / entry["name"], folder / entry["name"])
            manifest["files"][0]["sha256"] = "0" * 64
            (folder / "MANIFEST.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Refusing to import"):
                load_release(folder)


if __name__ == "__main__":
    unittest.main()
