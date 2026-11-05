"""Unit weights from the 2011 and 2015 fruit and vegetable sampling reports.

Counts are reconciled against the report text itself: every "Edible
portion weights" table in each report is either imported or listed as not
imported with a reason, never silently dropped.
"""

import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from shelfscale.fv_samples import (
    SNAPSHOTS,
    WEIGHT_TOLERANCE_G,
    import_all_samples,
    load_snapshot,
)

DATA = None


def setUpModule():
    global DATA
    DATA = import_all_samples()


def _composite(name_start, source_suffix):
    return next(
        o for o in DATA.observations
        if o.composite.food_name.startswith(name_start)
        and o.release.source_id.endswith(source_suffix)
    )


class TestCounts(unittest.TestCase):
    def test_every_table_is_accounted_for(self):
        for folder in SNAPSHOTS:
            release, text = load_snapshot(folder)
            with self.subTest(source=release.source_id):
                tables = text.count("Edible portion weights")
                imported = sum(1 for o in DATA.observations if o.release == release)
                skipped = sum(
                    1 for n in DATA.not_imported
                    if n.release == release and not n.reason.startswith("Edible portions only")
                )
                self.assertEqual(imported + skipped, tables)

    def test_counts(self):
        imported = Counter(o.release.source_id for o in DATA.observations)
        self.assertEqual(imported, {"uk-dh-fv-sampling-2011": 12, "uk-phe-fv-sampling-2015": 32})
        skipped = Counter(
            n.release.source_id for n in DATA.not_imported
            if not n.reason.startswith("Edible portions only")
        )
        self.assertEqual(skipped, {"uk-dh-fv-sampling-2011": 15, "uk-phe-fv-sampling-2015": 10})
        self.assertEqual(sum(len(o.composite.subsamples) for o in DATA.observations), 577)

    def test_every_import_reproduces_the_stated_average(self):
        for o in DATA.observations:
            with self.subTest(food=o.composite.food_name):
                self.assertLessEqual(abs(o.mean_g - o.stated_mean_g), WEIGHT_TOLERANCE_G + 1e-9)
                self.assertLessEqual(o.min_g, o.mean_g)
                self.assertLessEqual(o.mean_g, o.max_g)
                if o.stated_edible_portion is not None:
                    self.assertLessEqual(
                        abs(o.edible_portion_mean - o.stated_edible_portion), 0.01 + 1e-9)


class TestSpotChecks(unittest.TestCase):
    def test_medium_banana(self):
        o = _composite("Bananas, raw, flesh only", "2011")
        self.assertEqual(o.description, "Average weight of whole banana")
        self.assertEqual(o.sample_size, 11)
        self.assertEqual(round(o.mean_g, 2), 153.78)
        self.assertEqual((o.min_g, o.max_g, o.stated_mean_g), (111.9, 215.1, 153.8))
        self.assertEqual(round(o.sd_g, 2), 35.58)
        self.assertEqual((round(o.edible_portion_mean, 2), o.edible_portion_n), (0.63, 11))
        self.assertEqual((o.period_start, o.period_end), ("2011-11-18", "2011-11-21"))
        numbers = [s.number for s in o.composite.subsamples]
        self.assertEqual(numbers, [f"39.{i}" for i in range(1, 12)])
        second = o.composite.subsamples[1]
        self.assertEqual((second.weight_g, second.edible_portion), (161.0, 0.63))
        self.assertEqual(second.purchase.name, "Tesco, keep me, bananas")
        self.assertEqual(second.purchase.purchase_date, "18.11.2011")
        self.assertIn("6 bananas", o.composite.preparation_note)

    def test_other_named_foods(self):
        cases = [
            ("Apples, eating, raw, flesh and skin", "2011", 22, 156.24, 156.2),
            ("Oranges, flesh only", "2011", 22, 218.63, 218.6),
            ("Raisins, dried", "2015", 10, 0.62, 0.6),
            ("Papaya, ripe, raw, flesh only", "2015", 11, 550.94, 550.9),
        ]
        for name, source, n, mean, stated in cases:
            with self.subTest(food=name):
                o = _composite(name, source)
                self.assertEqual(o.sample_size, n)
                self.assertEqual(round(o.mean_g, 2), mean)
                self.assertEqual(o.stated_mean_g, stated)

    def test_report_disagreeing_with_itself_is_not_imported(self):
        kiwi = next(n for n in DATA.not_imported if n.food_name.startswith("Kiwi"))
        self.assertIn("83.8", kiwi.reason)
        self.assertFalse(any(o.composite.food_name.startswith("Kiwi") for o in DATA.observations))


class TestProvenance(unittest.TestCase):
    def test_no_portion_observation_without_source_and_period(self):
        for o in DATA.observations:
            with self.subTest(food=o.composite.food_name):
                self.assertTrue(o.release.source_id)
                self.assertTrue(o.release.edition)
                self.assertTrue(o.release.url.startswith("https://assets.publishing.service.gov.uk/"))
                self.assertTrue(o.release.sha256)
                self.assertRegex(o.period_start, r"^\d{4}-\d{2}-\d{2}$")
                self.assertRegex(o.period_end, r"^\d{4}-\d{2}-\d{2}$")
                self.assertLessEqual(o.period_start, o.period_end)
                self.assertEqual(o.basis, "weighed_sample_mean")
                self.assertTrue(o.composite.subsamples)
                for s in o.composite.subsamples:
                    self.assertTrue(s.row_text.strip())

    def test_manifests_name_the_legacy_route(self):
        for folder in SNAPSHOTS:
            manifest = json.loads((folder / "MANIFEST.json").read_text())
            self.assertTrue(manifest["legacy"]["via_legacy_project"])
            self.assertIn("cfadc8a", manifest["legacy"]["how"])
            self.assertTrue(manifest["legacy"]["why_not_used"])

    def test_refuses_a_file_that_does_not_match_the_manifest(self):
        folder = SNAPSHOTS[1]
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp)
            manifest = json.loads((folder / "MANIFEST.json").read_text())
            for entry in manifest["files"]:
                shutil.copy(folder / entry["name"], copy / entry["name"])
            manifest["files"][1]["sha256"] = "0" * 64
            (copy / "MANIFEST.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Refusing to import"):
                load_snapshot(copy)


if __name__ == "__main__":
    unittest.main()
