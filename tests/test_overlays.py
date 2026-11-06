import json
from pathlib import Path
import shutil
import tempfile
import unittest
from collections import Counter

from shelfscale.lookup import cofid_release, overlay_release, lookup_cofid
from shelfscale.overlays import ROOT, import_overlays, apply_overlays
from shelfscale.cofid_assess import lookup_and_assess
from shelfscale.source_tables import html_tables, ods_tables

class TestOverlays(unittest.TestCase):
    def test_source_counts_and_explicit_matches(self):
        data=overlay_release()
        self.assertEqual(Counter(o.release.source_id for o in data.observations),
            {'uk-milk-2022-23':24,'uk-beef-2024':689})
        self.assertEqual(len(data.source_only),5013)
        self.assertEqual(len(data.not_measured),153)
        self.assertEqual(len({o.food.food_id for o in data.observations}),11)
        self.assertEqual(len({o.food.food_id for o in data.source_only if o.release.source_id=='uk-beef-2024'}),22)

    def test_milk_updates_only_measured_nutrients(self):
        food=lookup_cofid(code='12-596')['matches'][0]
        current={o['nutrient_code']:o for o in food['observations'] if o['status']=='current'}
        changed={k for k,o in current.items() if o['source_id']=='uk-milk-2022-23'}
        self.assertEqual(changed,{'RIBO','VITB12','I'})
        self.assertEqual([current[k]['value'] for k in ('RIBO','VITB12','I')],[.19,.4,23])
        self.assertEqual(current['KJ']['value'],265)
        self.assertEqual(current['I']['period_start'],'2022-08-10')
        self.assertEqual(current['I']['period_end'],'2023-02-21')

    def test_beef_provenance_in_both_assessment_models(self):
        food=lookup_and_assess({'code':'18-017','fvn_percent':0,'free_sugars_g':0})['matches'][0]
        a=food['assessment']
        self.assertEqual(a['inputs']['energy_kj']['value'],523)
        for model in ('uk-npm-2004/05','uk-npm-2018'):
            p=a['models'][model]['inputs']['energy_kj']['provenance']
            self.assertEqual(p['source_id'],'uk-beef-2024')
            self.assertEqual(p['value_method'],'calculated_from_laboratory_analysis')
            self.assertIn('Macronutrients row 18 column 11',p['source_locator'])
            self.assertTrue(p['release']['sha256'] and p['supersedes'])
        self.assertEqual(a['inputs']['total_sugars_g']['provenance']['source_id'],'uk-cofid-2021')

    def test_supersession_is_per_value_and_base_immutable(self):
        base=cofid_release();merged=apply_overlays(base.observations,overlay_release().observations)
        ids={o.observation_id:o for o in merged}
        self.assertTrue(all(o.status=='current' for o in base.observations))
        for o in merged:
            if o.supersedes:
                old=ids[o.supersedes]
                self.assertEqual(old.status,'superseded')
                self.assertEqual(old.superseded_by,o.observation_id)
                self.assertEqual((old.food.food_id,old.definition.code,old.basis,old.definition.unit),
                                 (o.food.food_id,o.definition.code,o.basis,o.definition.unit))
        current=[(o.food.food_id,o.definition.code) for o in merged if o.status=='current']
        self.assertEqual(len(current),len(set(current)))

    def test_unmeasured_and_different_definitions_not_substituted(self):
        f=lookup_cofid(code='18-017')['matches'][0]
        current={o['nutrient_code']:o for o in f['observations'] if o['status']=='current'}
        self.assertEqual(current['I']['source_id'],'uk-cofid-2021') # beef [x]
        self.assertEqual(current['VITD']['source_id'],'uk-cofid-2021')
        f=lookup_cofid(code='18-043')['matches'][0]
        current={o['nutrient_code']:o for o in f['observations'] if o['status']=='current'}
        self.assertEqual(current['VITD3']['value_kind'],'below_limit')
        self.assertIsNone(current['VITD3']['value'])
        self.assertEqual(current['BEEF:VITD_activity_2.5']['value'],.18)
        self.assertEqual(current['VITD']['source_id'],'uk-cofid-2021') # CoFID multiplier is 5

    def test_every_overlay_value_has_evidence(self):
        data=overlay_release()
        for o in data.observations+data.source_only:
            self.assertTrue(o.period_start and o.period_end and o.analysis_period)
            self.assertTrue(o.source_food and o.source_locator and o.release.url and o.release.sha256)
            self.assertIn(o.method,('laboratory_analysis','calculated_from_laboratory_analysis','published_seasonal_mean'))

    def test_changed_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copytree(ROOT/'overlays',root/'overlays')
            shutil.copytree(ROOT/'raw'/'uk-milk-2022-23',root/'raw'/'uk-milk-2022-23')
            with (root/'raw'/'uk-milk-2022-23'/'report.html').open('a') as f:f.write('changed')
            with self.assertRaisesRegex(ValueError,'Refusing'):import_overlays(cofid_release(),root)

    def test_exact_source_cells(self):
        milk=html_tables(ROOT/'raw'/'uk-milk-2022-23'/'report.html')[3]
        self.assertEqual(milk[1][2::2],['0.19','0.4','23'])
        beef=ods_tables(ROOT/'raw'/'uk-beef-2024'/'results.ods')
        self.assertEqual(beef['Macronutrients'][17][10],'523')
        self.assertEqual(beef['Inorganics'][17][3],'38')
