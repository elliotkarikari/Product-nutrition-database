"""The data release: counts, group browse, the download files and their routes."""
import csv
import gzip
import hashlib
import http.client
import io
import json
import os
import re
import tempfile
import threading
import unittest
from pathlib import Path

from shelfscale import release, ui_api
from shelfscale.api import WEB, RateLimiter, ShelfScaleServer, UI_RATE_LIMIT
from shelfscale.as_sold import sample_units
from shelfscale.cofid_assess import lookup_and_assess
from shelfscale.lookup import DATA_RELEASE, cofid_release

ROOT = Path(__file__).resolve().parent.parent
TMP = tempfile.TemporaryDirectory()
os.environ[release.RELEASE_DIR_VAR] = TMP.name
release.current.cache_clear()


def rows(name):
    directory, _ = release.current()
    with open(directory / name, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class TestCounts(unittest.TestCase):
    def test_counts_are_the_data(self):
        s = release.summary()
        register = re.findall(r"^  - id: (\S+)$", (ROOT / "data" / "source-register.yaml").read_text(), re.M)
        self.assertEqual(s["foods"], len(cofid_release().foods))
        self.assertEqual(s["foods_with_as_sold_unit"],
                         len({f for f, units in sample_units().items() if any(u["applied"] for u in units)}))
        self.assertEqual(s["sources_in_register"], len(register))
        self.assertEqual(s["data_release"], DATA_RELEASE)


    def test_page_shows_the_api_counts_and_no_number_of_its_own(self):
        """The home page shows the release block of GET /api unchanged (TestRoutes checks /api
        against summary()). Its renderer restates no count, so the page cannot drift from the API."""
        js = (WEB / "app.js").read_text(encoding="utf-8")
        home = js[js.index("function countsHtml("):js.index("function filesBrief(")]
        self.assertIn('api("/api")', js)
        self.assertIn("countsHtml(summary.value.release)", js)
        for key in release.COUNT_LABELS:
            self.assertIn(f"release.{key}", home)
            self.assertIn(f'"{key}"', js[js.index("const COUNT_KEYS"):js.index("const whole")])
        self.assertIn("release.labels[k]", home)
        self.assertIn("release.data_release", home)
        self.assertNotRegex(home, r"\d{2,}")
        page = js + (WEB / "index.html").read_text(encoding="utf-8")
        s = release.summary()
        for text in (f"{s['foods']:,}", str(s["foods"])):  # the one count long enough to search for
            self.assertNotRegex(page, rf"(?<![\w.]){re.escape(text)}(?![\w.])")


class TestGroups(unittest.TestCase):
    def test_fourteen_main_groups_cover_every_food(self):
        g = release.groups()
        self.assertEqual([x["code"] for x in g["groups"]], list("ABCDFGHJMOPQSW"))
        self.assertEqual(sum(x["foods"] for x in g["groups"]), release.summary()["foods"])
        self.assertTrue(all(x["foods"] > 0 for x in g["groups"]))

    def test_a_group_lists_its_foods_under_named_subgroups(self):
        fruit = release.group("F")
        self.assertEqual(fruit["foods"], next(x["foods"] for x in release.groups()["groups"] if x["code"] == "F"))
        names = {s["code"]: s["name"] for s in fruit["subgroups"]}
        self.assertEqual(names["FA"], "Fruit, general")
        ids = [f["food_id"] for s in fruit["subgroups"] for f in s["foods"]]
        self.assertIn("14-393", ids)
        with self.assertRaises(LookupError):
            release.group("Z")


class TestFiles(unittest.TestCase):
    def test_manifest_counts_and_checksums_match_the_files(self):
        directory, manifest = release.current()
        self.assertEqual([f["name"] for f in manifest["files"]], list(release.FILES))
        for f in manifest["files"]:
            raw = (directory / f["name"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), f["sha256"], f["name"])
            self.assertEqual(raw.count(b"\n") - 1, f["rows"], f["name"])
            self.assertEqual(gzip.decompress((directory / (f["name"] + ".gz")).read_bytes()), raw)
        self.assertEqual(json.loads((directory / release.MANIFEST).read_text()), manifest)

    def test_manifest_attribution(self):
        _, manifest = release.current()
        by = {a["source_id"]: a for a in manifest["attribution"]}
        self.assertEqual(by["uk-cofid-2021"]["licence"], "Open Government Licence v3.0")
        fps = by["uk-food-portion-sizes-2002"]
        self.assertIn("Crown copyright", fps["licence"])
        self.assertIn("NOT covered by the Open Government Licence", fps["licence"])
        self.assertIn("hand-corrected extraction", fps["extraction"])
        self.assertIn("TSO", fps["attribution"])
        self.assertIn(DATA_RELEASE, manifest["citation"])

    def test_every_observation_row_carries_its_provenance(self):
        obs = rows("nutrient_observations.csv")
        self.assertEqual(len(obs), release.current()[1]["files"][1]["rows"])
        required = ("observation_id", "food_id", "nutrient_code", "value_text", "value_kind", "basis", "state",
                    "value_method", "source_id", "edition", "release_sha256", "confidence", "status", "data_release")
        for row in obs:
            missing = [c for c in required if not row[c]]
            if missing:
                self.fail(f"{row['observation_id']} lacks {missing}")
        self.assertIn("superseded", {r["status"] for r in obs})

    def test_the_lookup_api_and_the_file_hold_the_same_values(self):
        api = lookup_and_assess({"code": "12-596"})["matches"][0]["observations"]
        file = {r["observation_id"]: r for r in rows("nutrient_observations.csv") if r["food_id"] == "12-596"}
        self.assertEqual(len(api), len(file))
        for o in api:
            self.assertEqual(file[o["observation_id"]]["value_text"], o["value_text"])
            self.assertEqual(file[o["observation_id"]]["source_id"], o["source_id"])

    def test_portions_carry_sample_size_spread_and_citation(self):
        portions = rows("portions.csv")
        fps = [r for r in portions if r["source_id"] == "uk-food-portion-sizes-2002"]
        self.assertTrue(fps)
        for r in fps:
            self.assertIn("Food Portion Sizes, 3rd edition", r["citation"])
            self.assertEqual(r["spread"], release.FPS_SPREAD)
        sampled = [r for r in portions if r["sample_size"]]
        self.assertTrue(sampled)
        for r in portions:
            self.assertTrue(r["citation"] and r["spread"], r)

    def test_scores_give_both_laws_and_a_reason_instead_of_a_missing_number(self):
        scores = rows("scores.csv")
        self.assertEqual(len(scores), release.summary()["foods"])
        for model in ("uk_npm_2004_05", "uk_npm_2018"):
            for r in scores:
                self.assertTrue(r[f"{model}_law"] and r[f"{model}_law_status"])
                self.assertTrue(bool(r[f"{model}_score"]) != bool(r[f"{model}_not_scorable_reason"]), r)
        raisins = next(r for r in scores if r["food_id"] == "14-393")
        api = lookup_and_assess({"code": "14-393"})["matches"][0]["assessment"]["models"]
        self.assertEqual(raisins["uk_npm_2004_05_score"], str(api["uk-npm-2004/05"]["score"]))
        self.assertEqual(raisins["uk_npm_2004_05_law_status"], "in force")
        self.assertEqual(raisins["uk_npm_2018_law_status"], "shadow model, not in force")
        self.assertIn("free_sugars_g", raisins["uk_npm_2018_not_scorable_reason"])

    def test_match_decisions_cover_recorded_categories_and_state_empty_ones(self):
        _, manifest = release.current()
        decisions = rows("match_decisions.csv")
        for c in manifest["match_decision_categories"]:
            n = sum(1 for r in decisions if r["category"] == c["category"])
            self.assertEqual(n, c["rows"])
            self.assertEqual(c["statement"] is None, n > 0, c["category"])
        drafts = [r for r in decisions if r["recorded_in"] == "data/mapping/portion_links.json"]
        self.assertTrue(drafts)


class TestRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ShelfScaleServer(("127.0.0.1", 0), api_key="local-test-token")
        cls.server.ui_limiter = RateLimiter(limit=UI_RATE_LIMIT * 10)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def get(self, path, headers=None):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=60)
        try:
            conn.request("GET", path, headers=headers or {})
            r = conn.getresponse()
            return r.status, dict(r.getheaders()), r.read()
        finally:
            conn.close()

    def test_api_publishes_the_release_counts(self):
        status, _, raw = self.get("/api")
        self.assertEqual(status, 200)
        published = json.loads(raw)["release"]
        self.assertEqual(published, json.loads(json.dumps(release.summary())))
        for key in release.COUNT_LABELS:
            self.assertIsInstance(published[key], int)

    def test_group_routes(self):
        status, _, raw = self.get("/ui/groups")
        self.assertEqual((status, len(json.loads(raw)["groups"])), (200, 14))
        self.assertEqual(self.get("/ui/group/F")[0], 200)
        self.assertEqual(self.get("/ui/group/Z")[0], 404)

    def test_release_files_download_without_a_key(self):
        directory, _ = release.current()
        for name in (*release.FILES, release.MANIFEST):
            status, headers, raw = self.get(f"/download/{name}")
            self.assertEqual(status, 200, name)
            self.assertIn("attachment", headers["Content-Disposition"])
            self.assertEqual(raw, (directory / name).read_bytes(), name)
        status, headers, raw = self.get("/download/foods.csv", {"Accept-Encoding": "gzip"})
        self.assertEqual(headers.get("Content-Encoding"), "gzip")
        self.assertEqual(gzip.decompress(raw), (directory / "foods.csv").read_bytes())
        for bad in ("/download/foods.csv.gz", "/download/../SPEC.md", "/download/", "/download/foods"):
            self.assertEqual(self.get(bad)[0], 404, bad)

    def test_one_food_downloads_as_its_page_shows_it(self):
        status, headers, raw = self.get("/download/food/14-393.csv?free_sugars_g=0")
        self.assertEqual(status, 200)
        table = list(csv.DictReader(io.StringIO(raw.decode())))
        page = ui_api.food("14-393", {"free_sugars_g": "0"})
        energy = next(r for r in table if r["section"] == "composition" and r["item"] == "Energy" and r["unit"] == "kJ")
        self.assertEqual(float(energy["value"]), page["panel"][0]["value"])
        self.assertTrue(energy["observation_id"] and energy["citation"])
        scores = [r for r in table if r["section"] == "score" and r["item"].startswith("UK Nutrient")]
        self.assertEqual(len(scores), 2)
        self.assertEqual(scores[1]["value"], str(page["assessment"]["models"]["uk-npm-2018"]["score"]))
        self.assertIn("in force", scores[0]["source"])
        self.assertTrue(any(r["section"] == "your_figures" for r in table))
        self.assertEqual(self.get("/download/food/no-such.csv")[0], 404)
        self.assertEqual(self.get("/download/food/14-393.csv?portion_g=-1")[0], 400)


if __name__ == "__main__":
    unittest.main()
