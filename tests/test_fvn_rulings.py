import unittest
from shelfscale.fvn import TUBERS_2018
from shelfscale.cofid_assess import lookup_and_assess, lookup_bulk

OLD,NEW='uk-npm-2004/05','uk-npm-2018'
class TestRulings(unittest.TestCase):
    def test_all_reviewed_codes_and_original_model_preserved(self):
        self.assertEqual(len(TUBERS_2018),22)
        for code,name in TUBERS_2018.items():
            with self.subTest(code=code):
                food=lookup_and_assess({'code':code,'free_sugars_g':0})['matches'][0]
                self.assertEqual(food['name'],name)
                a=food['assessment']
                self.assertEqual(a['inputs']['fruit_veg_nuts_percent']['value'],100)
                self.assertEqual(a['models'][NEW]['inputs']['fvns_g']['value'],0)
                self.assertIn('excluded_by_guidance',a['models'][NEW]['inputs']['fvns_g']['source'])
    def test_caller_precedence_and_bulk_label(self):
        a=lookup_bulk({'items':[{'code':'13-463','fvn_percent':75,'free_sugars_g':0}]})['results'][0]['matches'][0]['assessment']
        self.assertEqual(a['models'][NEW]['inputs']['fvns_g']['value'],75)
        self.assertIn('caller_supplied',a['models'][NEW]['inputs']['fvns_g']['source'])
        self.assertIn('does not count seeds',a['models'][NEW]['inputs']['fvns_g']['source'])
        a=lookup_and_assess({'code':'13-463','fvns_g':80,'fvn_percent':75})['matches'][0]['assessment']
        self.assertEqual(a['models'][NEW]['inputs']['fvns_g'],{'value':80,'source':'caller_supplied'})
    def test_taro_leaves_are_not_tubers(self):
        a=lookup_and_assess({'code':'13-380'})['matches'][0]['assessment']
        self.assertEqual(a['models'][NEW]['inputs']['fvns_g']['value'],100)
    def test_ga_flags_distinguish_models(self):
        a=lookup_and_assess({'code':'14-834'})['matches'][0]['assessment']
        flags={x['model']:x['reason'] for x in a['review_flags']}
        self.assertIn('do not count',flags[OLD]);self.assertIn('Seeds count',flags[NEW])
