"""One-variable pie-menu smoke test: class category registration on Mac.

Tests are static. Real pie-menu recognition still requires opening the
game, verifying no UI Exception and inspecting the single new option.
"""
import struct
import unittest
import xml.etree.ElementTree as ET

from tooling.build_m35_category_smoke import (
    CATEGORY_ID,CATEGORY_NAME,CATEGORY_KEY,BASE_CATEGORY,
    VIEW_ONLY_INTERACTION,TYPE_CATEGORY,TYPE_SIMDATA,SIMDATA_GROUP,
    TYPE_INTERACTION,TYPE_STBL,package_bytes)
from tooling.build_m34_settings import package_bytes as build_m34
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes


class M35SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=resources(build_m34())
        cls.new=resources(package_bytes())
        cls.lookup={(t,g,i):raw for t,g,i,raw in cls.new}

    def test_only_one_extra_category_compared_to_m34(self):
        audit=inspect_bytes(package_bytes())
        self.assertEqual(audit['status'],'STATIC_GATE_PASSED')
        self.assertEqual(audit['category_count'],2)
        self.assertEqual(audit['simdata_count'],2)
        self.assertEqual(len(self.new),29)

    def test_unique_category_has_matching_companion(self):
        categories={iid for typ,g,iid,raw in self.new
                    if typ==TYPE_CATEGORY}
        self.assertEqual(categories,{BASE_CATEGORY,CATEGORY_ID})
        new_xml=ET.fromstring(self.lookup[(TYPE_CATEGORY,0,CATEGORY_ID)])
        self.assertEqual(new_xml.get('s'),str(CATEGORY_ID))
        self.assertEqual(new_xml.get('n'),CATEGORY_NAME)
        self.assertEqual(new_xml.find('./T[@n="_display_name"]').text,
                         '0x{:08X}'.format(CATEGORY_KEY))
        self.assertIsNone(new_xml.find('./T[@n="_parent"]'))
        simdata=self.lookup[(TYPE_SIMDATA,SIMDATA_GROUP,CATEGORY_ID)]
        self.assertEqual(struct.unpack_from('<I',simdata,0x44)[0],CATEGORY_KEY)
        self.assertEqual(struct.unpack_from('<Q',simdata,0x5c)[0],0)
        self.assertTrue(simdata.endswith(CATEGORY_NAME.encode('ascii')+b'\x00'))

    def test_only_class1_consulta_uses_new_category(self):
        cat={iid:int(ET.fromstring(raw).find('./T[@n="category"]').text)
             for typ,g,iid,raw in self.new if typ==TYPE_INTERACTION}
        self.assertEqual(cat[VIEW_ONLY_INTERACTION],CATEGORY_ID)
        self.assertEqual(sum(1 for x in cat.values() if x==CATEGORY_ID),1)
        self.assertTrue(all(x in {CATEGORY_ID,BASE_CATEGORY}
                            for x in cat.values()))

    def test_every_other_existing_action_unchanged(self):
        for old,new in zip(self.original,self.new):
            self.assertEqual(old[:3],new[:3])
            if old[0]==TYPE_INTERACTION and old[2]!=VIEW_ONLY_INTERACTION:
                self.assertEqual(old,new)
            if old[0] in (TYPE_CATEGORY,TYPE_SIMDATA):
                self.assertEqual(old,new)

    def test_both_locales_include_class1_label(self):
        locales=set()
        for typ,g,iid,raw in self.new:
            if typ==TYPE_STBL:
                strings=parse_stbl(raw)
                locales.add(iid>>56)
                self.assertIn(CATEGORY_KEY,strings)
                self.assertIn('M35',strings[0x3FCE8D06])
                self.assertIn('1',strings[CATEGORY_KEY])
        self.assertEqual(locales,{0,11})


if __name__=='__main__':
    unittest.main()
