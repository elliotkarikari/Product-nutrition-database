"""The browser page, its same-origin routes, recipes and the label engine."""
import http.client
import json
import threading
import unittest

from shelfscale import label, recipe, ui_api
from shelfscale.api import STATIC, UI_RATE_LIMIT, WEB, RateLimiter, ShelfScaleServer
from shelfscale.cofid_assess import lookup_and_assess
from shelfscale.service import assess_product

KEY = 'local-test-token'
FLOUR, BUTTER, SUGAR, EGG, RAISINS = '11-888', '17-661', '17-063', '12-937', '14-393'
CAKE = {'ingredients': [{'food_id': FLOUR, 'grams': 225}, {'food_id': BUTTER, 'grams': 100},
                        {'food_id': SUGAR, 'grams': 75}, {'food_id': EGG, 'grams': 50},
                        {'food_id': RAISINS, 'grams': 100}], 'servings': 12}


class TestServing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ShelfScaleServer(('127.0.0.1', 0), api_key=KEY)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.now = [100.]
        self.server.limiter = RateLimiter(clock=lambda: self.now[0])
        self.server.ui_limiter = RateLimiter(clock=lambda: self.now[0], limit=UI_RATE_LIMIT)

    def raw(self, path, *, method='GET', body=None, keys=()):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=10)
        try:
            conn.putrequest(method, path)
            for key in keys:
                conn.putheader('X-API-Key', key)
            if body is not None:
                conn.putheader('Content-Length', str(len(body)))
            conn.endheaders(body)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def json(self, path, payload=None, **kw):
        body = None if payload is None else json.dumps(payload).encode()
        status, headers, raw = self.raw(path, method='POST' if body is not None else 'GET', body=body, **kw)
        return status, headers, json.loads(raw)

    def test_root_is_the_page_and_files_are_a_fixed_list(self):
        for path, (name, ctype) in STATIC.items():
            status, headers, raw = self.raw(path)
            self.assertEqual(status, 200, path)
            self.assertEqual(headers['Content-Type'], ctype)
            self.assertEqual(raw, (WEB / name).read_bytes())
            self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
            self.assertNotIn(KEY.encode(), raw)
        for path in ('/static/../api.py', '/static/', '/static/index.html', '/web/app.js', '/index.html'):
            self.assertEqual(self.raw(path)[0], 404, path)

    def test_summary_moved_to_api_and_health_unchanged(self):
        status, _, body = self.json('/api')
        self.assertEqual((status, body['service']), (200, 'ShelfScale Open'))
        self.assertIn('POST /ui/recipe', body['endpoints']['page'])
        self.assertEqual(self.json('/health')[2]['status'], 'ok')

    def test_page_routes_need_no_key_and_keyed_routes_still_do(self):
        status, _, body = self.json('/ui/search?q=jaffa')
        self.assertEqual((status, body['results'][0]['food_id']), (200, '11-739'))
        self.assertEqual(self.json('/ui/food/11-739')[0], 200)
        self.assertEqual(self.json('/ui/food/no-such-food')[0], 404)
        self.assertEqual(self.json('/ui/food/11-739?portion_g=-3')[0], 400)
        self.assertEqual(self.json('/ui/recipe', CAKE)[0], 200)
        self.assertEqual(self.json('/ui/recipe', {'ingredients': []})[0], 400)
        for route in ('/v1/lookup', '/v1/assess', '/v1/lookup/bulk', '/v1/assess/bulk'):
            self.assertEqual(self.json(route, {})[0], 401, route)
        self.assertEqual(len(self.server.limiter.requests), 0)

    def test_page_quota_is_separate_from_the_key_quota(self):
        for _ in range(UI_RATE_LIMIT):
            self.assertEqual(self.json('/ui/search?q=x')[0], 200)
        status, headers, _ = self.json('/ui/search?q=jaffa')
        self.assertEqual(status, 429)
        self.assertIn('Retry-After', headers)
        self.assertEqual(self.json('/ui/recipe', CAKE)[0], 429)
        self.assertEqual(self.json('/v1/lookup', {'code': '11-739'}, keys=(KEY,))[0], 200)
        self.assertEqual(self.json('/', None)[0] if False else self.raw('/')[0], 200)
        self.assertEqual(len(self.server.limiter.requests), 1)

    def test_page_recipe_body_is_bounded(self):
        body = json.dumps({'ingredients': [{'food_id': FLOUR, 'grams': 1}] * 4000}).encode()
        self.assertEqual(self.raw('/ui/recipe', method='POST', body=body)[0], 400)


class TestSameScores(unittest.TestCase):
    def test_food_view_carries_the_lookup_assessment(self):
        params = {'fvn_percent': '5', 'portion_g': '13', 'free_sugars_g': '40'}
        view = ui_api.food('11-739', params)
        api = lookup_and_assess({'code': '11-739', 'fvn_percent': 5, 'portion_g': 13, 'free_sugars_g': 40})
        self.assertEqual(view['assessment'], api['matches'][0]['assessment'])
        self.assertEqual(view['caller_supplied'], {'fvn_percent': 5.0, 'free_sugars_g': 40.0})

    def test_recipe_scores_equal_assess_on_the_same_unrounded_values(self):
        result = recipe.calculate({**CAKE, 'fvn_percent': 18, 'free_sugars_g': 26})
        v = result['per_100g']
        aoac = result['assessment']['models']['uk-npm-2018']['inputs']['fibre_aoac_g']['value']
        common = {k: v[k] for k in ('energy_kj', 'fat_g', 'saturated_fat_g', 'total_sugars_g',
                                    'sodium_mg', 'protein_g')}
        common.update(fruit_veg_nuts_percent=18, free_sugars_g=26)
        direct = assess_product({'id': 'cake', 'portion_g': result['serving_g'],
                                 'nutrients': {**common, 'fibre_nsp_g': v['fibre_nsp_g']}})
        direct2018 = assess_product({'id': 'cake', 'nutrients': {**common, 'fibre_aoac_g': aoac}})
        for model, other in (('uk-npm-2004/05', direct), ('uk-npm-2018', direct2018)):
            mine, theirs = result['assessment']['models'][model], other['models'][model]
            for field in ('score', 'less_healthy', 'a_points', 'c_points'):
                self.assertEqual(mine[field], theirs[field], (model, field))
        self.assertEqual(result['assessment']['traffic_lights']['colours'],
                         direct['traffic_lights']['colours'])

    def test_weighted_sums_are_exact_and_unrounded(self):
        result = recipe.calculate({'ingredients': [{'food_id': FLOUR, 'grams': 30},
                                                   {'food_id': SUGAR, 'grams': 70}]})
        flour = recipe._current(FLOUR)['KJ']['value']
        sugar = recipe._current(SUGAR)['KJ']['value']
        self.assertEqual(result['per_100g']['energy_kj'], (flour * 30 / 100 + sugar * 70 / 100) / 100 * 100)
        self.assertEqual(result['yield_note'], recipe.YIELD_NOTE)


class TestRecipeRules(unittest.TestCase):
    def test_no_2018_score_without_caller_free_sugars(self):
        result = recipe.calculate({**CAKE, 'fvn_percent': 18})
        new = result['assessment']['models']['uk-npm-2018']
        self.assertFalse(new['scorable'])
        self.assertIsNone(new['inputs']['free_sugars_g']['value'])
        self.assertIn('never used', result['assessment']['models']['uk-npm-2018']['free_sugars_note'])
        self.assertIsNone(result['assessment']['verdict_changes_under_2018'])

    def test_fvn_needs_caller_value_unless_every_ingredient_has_one(self):
        old = recipe.calculate(CAKE)['assessment']['models']['uk-npm-2004/05']
        self.assertFalse(old['scorable'])
        self.assertIn('Butter, unsalted', ' '.join(old['missing_inputs']))
        fruit = recipe.calculate({'ingredients': [{'food_id': RAISINS, 'grams': 50}]})
        self.assertEqual(fruit['fruit_veg_nuts']['source'], 'derived_from_ingredients')
        self.assertEqual(fruit['per_100g']['fruit_veg_nuts_percent'], 100.0)

    def test_fibre_methods_never_mix(self):
        result = recipe.calculate(CAKE)
        self.assertEqual(sum(k in result['per_100g'] for k in ('fibre_nsp_g', 'fibre_aoac_g')), 1)

    def test_refusals(self):
        alcoholic = next(f.food_id for f in ui_api.foods_by_id().values() if (f.group or '').startswith('Q'))
        bad = ({'ingredients': [{'food_id': alcoholic, 'grams': 10}]},
               {'ingredients': [{'food_id': FLOUR, 'grams': 0}]},
               {'ingredients': [{'food_id': FLOUR, 'grams': float('inf')}]},
               {'ingredients': [{'food_id': FLOUR, 'grams': 10}], 'servings': 0},
               {'ingredients': [{'food_id': FLOUR, 'grams': 10}], 'servings': True},
               {'ingredients': [{'food_id': FLOUR, 'grams': 10}] * 61},
               {'ingredients': [{'food_id': 'nope', 'grams': 10}]})
        for payload in bad:
            with self.subTest(payload=str(payload)[:60]), self.assertRaises(ValueError):
                recipe.calculate(payload)

    def test_as_sold_flag(self):
        cocoa = ui_api.search('cocoa powder')['results'][0]
        self.assertIsNotNone(ui_api.food(cocoa['food_id'])['powder'])
        self.assertIsNone(ui_api.as_sold_flag('Sugar, white'))


class TestPortionsAndProvenance(unittest.TestCase):
    def test_fps_citation_travels_with_every_fps_weight(self):
        portions = [p for ps in ui_api._portions().values() for p in ps]
        fps = [p for p in portions if p['source']['label'] == 'Food Portion Sizes 2002']
        self.assertTrue(fps)
        for p in fps:
            self.assertIn('Food Portion Sizes, 3rd edition', p['source']['citation'])
            self.assertIn('NOT covered by the Open Government Licence', p['source']['rights'])
            self.assertEqual(p['tappable'], p['grams'] is not None)

    def test_sample_weights_link_only_by_exact_name_and_use_edible_part(self):
        orange = ui_api.search('Oranges, flesh only')['results'][0]['food_id']
        (p,) = ui_api.portions_for(orange)
        self.assertEqual(p['basis'], 'edible part of each purchase: weight x its edible proportion')
        self.assertTrue(p['range_g'][0] < p['grams'] < p['range_g'][1])
        self.assertAlmostEqual(p['grams'], 218.6 * 0.7064, delta=5)  # per-purchase mean, not mean x mean
        banana = ui_api.search('Bananas, flesh only')['results'][0]['food_id']
        self.assertEqual(ui_api.portions_for(banana), [])  # report name differs; never guessed

    def test_overlay_values_name_their_overlay_and_period(self):
        beef = ui_api.food('18-043')
        labels = {p['code']: p['source']['label'] for p in beef['panel'] if p['source']}
        self.assertTrue(labels['KJ'].startswith('Beef overlay 2024'))
        self.assertEqual(labels['TOTSUG'], 'CoFID 2021')  # unmeasured values stay CoFID
        milk = ui_api.food('12-596')
        self.assertEqual({v['code'] for v in milk['overlay_values']}, {'I', 'RIBO', 'VITB12'})
        self.assertTrue(all(v['source']['label'].startswith('Milk overlay 2022')
                            for v in milk['overlay_values']))


class TestLabel(unittest.TestCase):
    def test_rounding_table_edges(self):
        cases = [('fat_g', 10, '10'), ('fat_g', 9.96, '10.0'), ('fat_g', 9.94, '9.9'),
                 ('fat_g', 0.51, '0.5'), ('fat_g', 0.5, '0'), ('sugars_g', 12.5, '13'),
                 ('saturates_g', 0.1, '0'), ('saturates_g', 0.15, '0.2'), ('saturates_g', 10.4, '10'),
                 ('salt_g', 1.05, '1.1'), ('salt_g', 0.995, '1.00'), ('salt_g', 0.0125, '0'),
                 ('salt_g', 0.013, '0.01'), ('energy_kj', 1649.5, '1650'), ('protein_g', None, None)]
        for name, value, expected in cases:
            with self.subTest(name=name, value=value):
                self.assertEqual(label.display(name, value), expected)

    def test_conversions_follow_the_cofid_guide(self):
        n = lambda v: {'value': v, 'value_kind': 'number'}  # noqa: E731
        obs = {'TOTNIT': n(2.0), 'FAT': n(10.0), 'SATFOD': n(4.0), 'NA': n(400.0),
               'CHO': n(60.0), 'STAR': n(40.0), 'TOTSUG': n(20.0), 'SUCR': n(10.5), 'LACT': n(0.0),
               'AOACFIB': n(3.0), 'ALCO': {'value': 0, 'value_kind': 'trace'}}
        values, missing, gaps = label.ingredient_label_values(obs)
        self.assertEqual(values['protein_g'], 12.5)
        self.assertEqual(values['salt_g'], 1.0)
        self.assertAlmostEqual(values['carbohydrate_g'], 40 / 1.10 + 20 / 1.05)
        self.assertAlmostEqual(values['sugars_g'], 20 - 10.5 + 10.5 / 1.05)
        carb = 40 / 1.10 + 20 / 1.05
        self.assertAlmostEqual(values['energy_kj'], 17 * carb + 17 * 12.5 + 37 * 10 + 8 * 3)
        self.assertAlmostEqual(values['energy_kcal'], 4 * carb + 4 * 12.5 + 9 * 10 + 2 * 3)
        self.assertEqual((missing, gaps), ([], []))
        obs['STAR'] = n(20.0)
        self.assertAlmostEqual(label.ingredient_label_values(obs)[0]['carbohydrate_g'], 60 / 1.05)
        del obs['AOACFIB'], obs['SUCR']
        values, missing, gaps = label.ingredient_label_values(obs)
        self.assertIn('sugars_g', missing)
        self.assertEqual(gaps, ['fibre'])

    def test_recipe_label_is_per_100g_and_per_serving_with_method(self):
        result = recipe.calculate(CAKE)
        lab = result['label']
        self.assertEqual([r['key'] for r in lab['per_100g']],
                         ['energy_kj', 'energy_kcal', 'fat_g', 'saturates_g', 'carbohydrate_g',
                          'sugars_g', 'protein_g', 'salt_g'])
        fat100 = lab['per_100g'][2]['value']
        self.assertAlmostEqual(lab['per_serving'][2]['value'], fat100 * result['serving_g'] / 100)
        self.assertIn('user guide', lab['method'])
        self.assertIn('not laboratory analysis', lab['statement'])


if __name__ == '__main__':
    unittest.main()
