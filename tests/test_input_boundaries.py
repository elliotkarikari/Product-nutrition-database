"""Regression coverage for the independent audit's numeric and HTTP failures."""
import copy
import http.client
import json
import threading
import unittest

from shelfscale.api import ShelfScaleServer
from shelfscale.cofid_assess import lookup_and_assess, lookup_bulk
from shelfscale.service import assess_product, assess_bulk
from shelfscale.npm import calculate_npm
from shelfscale.npm2018 import calculate_npm2018
from shelfscale.traffic_lights import traffic_lights

PRODUCT = {'id': 'boundary', 'nutrients': dict(energy_kj=100, saturated_fat_g=0,
    total_sugars_g=0, sodium_mg=0, protein_g=0, fruit_veg_nuts_percent=0, fibre_aoac_g=0)}
BAD = (float('nan'), float('inf'), -float('inf'), 10**400, -1, True, '1')

class TestNumericBoundaries(unittest.TestCase):
    def test_supplied_and_bulk_reject_bad_nutrients(self):
        for field in (*PRODUCT['nutrients'], 'fat_g', 'free_sugars_g', 'fvns_g'):
            for value in BAD:
                with self.subTest(field=field, value=str(value)[:20]):
                    p = copy.deepcopy(PRODUCT); p['nutrients'][field] = value
                    with self.assertRaises(ValueError): assess_product(p)
                    r = assess_bulk({'products': [p, PRODUCT]})
                    self.assertEqual((r['summary']['assessed'], r['summary']['failed']), (1, 1))

    def test_lookup_and_bulk_reject_bad_numbers(self):
        for field in ('fvn_percent', 'free_sugars_g', 'fvns_g', 'portion_g'):
            for value in BAD:
                p = {'code': '14-834', field: value}
                with self.subTest(field=field, value=str(value)[:20]):
                    with self.assertRaises(ValueError): lookup_and_assess(p)
                    self.assertEqual(lookup_bulk({'items': [p]})['summary']['failed'], 1)

    def test_portions_density_and_overflow(self):
        for field in ('portion_g', 'specific_gravity'):
            for value in (*BAD, 0):
                p = {**PRODUCT, field: value}
                if field == 'specific_gravity': p['basis'] = 'per_100ml'
                with self.assertRaises(ValueError): assess_product(p)
        for p in ({**PRODUCT, 'basis': 'per_100ml', 'specific_gravity': 5e-324},
                  {**PRODUCT, 'portion_g': 1e308, 'nutrients': {**PRODUCT['nutrients'], 'energy_kj': 1000}}):
            with self.assertRaises(ValueError): assess_product(p)

    def test_bulk_limit_and_invalid_shapes(self):
        for fn,key,item in ((assess_bulk,'products',PRODUCT),(lookup_bulk,'items',{'code':'14-834'})):
            with self.assertRaisesRegex(ValueError, '1000'): fn({key:[item]*1001})
            for payload in (None, [], {key:[]}, {key:{}}):
                with self.assertRaises(ValueError): fn(payload)
        for item in (None, [], 'x', 1, {'id':[]}, {'id':42}):
            with self.assertRaises(ValueError): assess_product(item)

    def test_direct_scorers_and_colours(self):
        for value in BAD:
            with self.assertRaises(ValueError): calculate_npm(**{**PRODUCT['nutrients'],'energy_kj':value})
            with self.assertRaises(ValueError): calculate_npm2018(energy_kj=value,saturated_fat_g=0,
                free_sugars_g=0,salt_g=0,protein_g=0,fvns_g=0,fibre_aoac_g=0)
            with self.assertRaises(ValueError): traffic_lights(is_drink=False,per_100={'fat':value})

class TestFraming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ShelfScaleServer(('127.0.0.1',0),api_key='test-key')
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def request(self,body,headers=()):
        conn=http.client.HTTPConnection(*self.server.server_address,timeout=5)
        try:
            conn.putrequest('POST','/v1/assess')
            conn.putheader('X-API-Key', 'test-key')
            for k,v in headers: conn.putheader(k,v)
            conn.endheaders(body)
            r=conn.getresponse(); return r.status,json.loads(r.read())
        finally: conn.close()
    def test_bad_lengths_and_transfer_encoding(self):
        for h in ([], [('Content-Length','abc')],[('Content-Length','-1')],
                  [('Content-Length','5000001')], [('Content-Length','2'),('Content-Length','2')],
                  [('Transfer-Encoding','chunked'),('Content-Length','2')]):
            self.assertEqual(self.request(b'{}',h)[0],400)
    def test_bad_json_and_utf8(self):
        for raw in (b'\xff',b'{',b'{"x":NaN}', b'['*1100+b']'*1100):
            self.assertEqual(self.request(raw,[('Content-Length',str(len(raw)))])[0],400)
    def test_overflow_is_client_error(self):
        p=copy.deepcopy(PRODUCT);p['nutrients']['energy_kj']=10**400
        raw=json.dumps(p).encode()
        self.assertEqual(self.request(raw,[('Content-Length',str(len(raw)))])[0],400)
