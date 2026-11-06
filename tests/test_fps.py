"""Food Portion Sizes import from Elliot's transcription.

Spot-check values are the book values as transcribed in the source file.
"""

import csv
import io
import json
import re
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from shelfscale.fps import SNAPSHOT, import_fps, load_release, read_weight
from shelfscale.lookup import cofid_release

ROOT = Path(__file__).resolve().parent.parent
DATA = None


def setUpModule():
    global DATA
    DATA = import_fps(cofid_release().foods)


def _row(index):
    return next(p for p in DATA.portions if p.source_row == index)


class TestCounts(unittest.TestCase):
    def test_reconciled_with_the_source_file(self):
        _, raw = load_release()
        body = list(csv.reader(io.StringIO(raw.decode("cp1252"))))[1:]
        self.assertEqual(len(body), 2652)
        self.assertEqual(len(DATA.portions) + len(DATA.not_imported), len(body))
        self.assertEqual(len(DATA.portions), 2606)
        self.assertEqual(Counter(p.value_kind for p in DATA.portions),
                         {"single": 2575, "alternatives": 19, "volume_ml": 11, "range": 1})
        self.assertEqual(Counter(n["reason"] for n in DATA.not_imported), {
            "cross-reference": 41,
            "weight not readable as written; not corrected": 4,
            "no weight given": 1,
        })

    def test_cofid_matches_are_exact_names_only(self):
        matched = [p for p in DATA.portions if p.cofid_food_id]
        self.assertEqual(len(matched), 69)
        self.assertEqual(len({p.cofid_food_id for p in matched}), 42)
        names = {f.food_id: f.name for f in cofid_release().foods}
        for p in matched:
            self.assertEqual(p.cofid_match, "exact_name")
            self.assertEqual(p.food_name.strip().casefold(), names[p.cofid_food_id].casefold())
        self.assertEqual(sum(1 for p in DATA.portions if p.cofid_match == "none"), 2537)


class TestSpotChecks(unittest.TestCase):
    def test_named_portions(self):
        first = _row("1")
        self.assertEqual((first.group, first.brand, first.food_name, first.grams),
                         ("BABY FOODS", "Boots", "First Harvest,Dessert starter", 125.0))
        spirits = _row("46")
        self.assertEqual((spirits.portion_description, spirits.grams),
                         ("1 measure, (England and Wales)", 23.0))
        jaffa = next(p for p in DATA.portions if p.food_name == "Jaffa cakes")
        self.assertEqual((jaffa.grams, jaffa.cofid_food_id), (13.0, "11-739"))

    def test_weights_are_read_not_corrected(self):
        wine = _row("55")
        self.assertEqual((wine.value_kind, wine.amounts, wine.unit, wine.grams),
                         ("volume_ml", (750.0,), "ml", None))
        beer = _row("40")
        self.assertEqual((beer.weight_text, beer.value_kind, beer.amounts, beer.grams),
                         ("250/300g", "alternatives", (250.0, 300.0), None))
        pizza = _row("604")
        self.assertEqual((pizza.value_kind, pizza.amounts), ("range", (350.0, 500.0)))
        unreadable = {n["row"]: n["weight_text"] for n in DATA.not_imported if "weight_text" in n}
        self.assertEqual(unreadable, {"24": "3. 8g", "45": "l00g", "2258": "50g/l00g",
                                      "2261": "25g/50g/l00g"})
        self.assertEqual(read_weight("l00g"), ("unreadable", (), None))


class TestProvenance(unittest.TestCase):
    def test_every_portion_carries_the_book(self):
        for p in DATA.portions:
            self.assertEqual(p.release.source_id, "uk-food-portion-sizes-2002")
            self.assertIn("Food Portion Sizes, 3rd edition", p.release.attribution)
            self.assertIn("9780112429616", p.release.attribution)
            self.assertIn("NOT covered by the Open Government Licence", p.release.licence)
            self.assertTrue(p.source_row and p.weight_text.strip())
            self.assertEqual(p.basis, "typical_portion")

    def test_fps_is_never_called_ogl_or_licensed(self):
        mentions = re.compile(r"food portion sizes|uk-food-portion-sizes|\bFPS\b", re.I)
        claims = re.compile(r"\bOGL\b|Open Government Licence|licensed", re.I)
        offenders = []
        for path in [ROOT / "SPEC.md", ROOT / "README.md", ROOT / "data" / "source-register.yaml",
                     *ROOT.glob("docs/*.md"), SNAPSHOT / "MANIFEST.json", SNAPSHOT / "DECISION.md"]:
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if mentions.search(line) and claims.search(line) and not re.search(r"\bNOT\b|never|not a licence|not OGL", line):
                    offenders.append(f"{path.name}:{n}")
        self.assertEqual(offenders, [])

    def test_refuses_a_file_that_does_not_match_the_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp)
            manifest = json.loads((SNAPSHOT / "MANIFEST.json").read_text())
            shutil.copy(SNAPSHOT / manifest["files"][0]["name"], copy)
            manifest["files"][0]["sha256"] = "0" * 64
            (copy / "MANIFEST.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Refusing to import"):
                load_release(copy)


class TestReconciliationReport(unittest.TestCase):
    def test_report_is_complete_and_consistent(self):
        rows = list(csv.DictReader((ROOT / "docs" / "fps_reconciliation.csv").open(encoding="utf-8")))
        transcription_rows = [r for r in rows if r["transcription_row"]]
        self.assertEqual(len(transcription_rows), 2652)
        self.assertEqual(Counter(r["result"] for r in rows), {
            "agree (same words, same weight)": 793,
            "agree (reviewed food and portion)": 3,
            "OCR-character difference only": 58,
            "one side has no weight": 19,
            "DIFFERENT WEIGHT, same food and portion": 2,
            "not located in extraction": 1765,
            "only in extraction": 1550,
            "ambiguous extraction matches": 8,
            "ambiguous portion; book check required": 4,
        })
        matched = [(r["group"], r["extraction_row"]) for r in transcription_rows if r["extraction_row"]]
        self.assertEqual(len(matched), len(set(matched)))
        for r in transcription_rows:
            self.assertEqual(json.loads(r["identity_key"]), [r["group"], r["transcription_brand"].strip().casefold(),
                r["transcription_food"].strip().casefold(), r["transcription_portion"].strip().casefold()])
        reviews = [r for r in rows if r["result"] == "agree (reviewed food and portion)"]
        self.assertEqual({r["extraction_row"] for r in reviews}, {"1727", "1731", "2527"})
        self.assertTrue(all(r["transcription_weight"] == r["extraction_weight"] == "55g" for r in reviews))



if __name__ == "__main__":
    unittest.main()
