"""The page's navigation, framing and copy rules (data-first round)."""
import re
import unittest

from shelfscale import ui_api
from shelfscale.api import WEB

HTML = (WEB / "index.html").read_text(encoding="utf-8")
JS = (WEB / "app.js").read_text(encoding="utf-8")
CSS = (WEB / "app.css").read_text(encoding="utf-8")


class TestNavigation(unittest.TestCase):
    def test_four_destinations_named_for_what_the_visitor_does(self):
        tabs = re.findall(r'<a href="(#/[^"]*)" data-tab="(\w+)">([^<]+)</a>', HTML)
        self.assertEqual([t[2] for t in tabs],
                         ["Browse the data", "Score a product", "Score your range", "Download the data"])
        self.assertEqual([t[0] for t in tabs], ["#/", "#/score", "#/range", "#/download"])

    def test_every_route_lights_one_of_the_four(self):
        route = JS[JS.index("function route() {"):JS.index("function addIngredient")]
        self.assertEqual(set(re.findall(r'tab = "(\w+)"', route)) | {"browse"}, {"browse", "score", "range", "download"})
        for path in ("#/food/", "#/browse/", "#/score/", "#/score", "#/range", "#/download", "#/recipe", "#/label"):
            self.assertIn(f'"{path}"', route)


class TestCopy(unittest.TestCase):
    def test_no_em_dashes_in_any_copy(self):
        for name, text in (("index.html", HTML), ("app.js", JS), ("app.css", CSS)):
            self.assertNotIn("—", text, name)

    def test_home_leads_with_the_data_and_scoring_is_one_panel(self):
        home = JS[JS.index("async function renderHome()"):JS.index("/* ---------- Browse: one food group")]
        order = [home.index(x) for x in ('class="headline home-title"', 'id="groups"', 'id="dl-h"', 'id="can-h"')]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("hero: true", home)

    def test_food_record_leads_with_the_food_unless_opened_to_score(self):
        food = JS[JS.index("async function renderFood("):JS.index("/* ---------- Your range")]
        self.assertIn("scoreFirst ? scorePanel + record : record + scorePanel", food)
        self.assertIn("foodCsvHref(food.food_id)", food)

    def test_range_names_both_modes_in_framing_results_and_export(self):
        self.assertIn("From your own figures", JS)
        self.assertIn("From ShelfScale reference data", JS)
        self.assertIn('"scored_from"', JS)
        self.assertIn("Scored from: ${esc(scoredFrom(r))}", JS)

    def test_ultramarine_is_declared_once_and_only_used_through_the_signal_token(self):
        self.assertEqual(len(re.findall(r"#2537d9", CSS, re.I)), 1)

    def test_food_page_names_its_group(self):
        self.assertEqual(ui_api.food("14-393")["group_name"], "Fruit")


if __name__ == "__main__":
    unittest.main()
