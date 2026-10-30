"""Regression: M32 must not reintroduce broken child-category references.

M33 keeps every mailbox action in the previously tested top-level
PieMenuCategory; the nested layout remains a separate unresolved task.
"""
import unittest
import xml.etree.ElementTree as ET
from tooling.build_m33_flat_recovery import (
    package_bytes, BASE_CATEGORY, CATEGORY_IDS, IDS, ROUTES, KEYS)
from tooling.build_m29_bundle import package_bytes as build_m29
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes


class FlatRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=resources(build_m29())
        cls.items=resources(package_bytes())

    def test_only_one_root_category_and_one_simdata(self):
        report=inspect_bytes(package_bytes())
        self.assertEqual(report['status'],'STATIC_GATE_PASSED')
        self.assertEqual(report['category_count'],1)
        self.assertEqual(report['simdata_count'],1)
        self.assertEqual(CATEGORY_IDS,(BASE_CATEGORY,)*3)
        self.assertEqual(len(self.items),23)

    def test_all_interactions_point_only_to_existing_category(self):
        category_ids={i for t,g,i,raw in self.items if t==0x03E9D964}
        self.assertEqual(category_ids,{BASE_CATEGORY})
        for t,g,i,raw in self.items:
            if t==0xE882D22F:
                root=ET.fromstring(raw)
                key=root.find('./T[@n="category"]')
                if key is not None:
                    self.assertIn(int(key.text),category_ids)

    def test_new_transfers_label_both_source_and_destination(self):
        names={}
        for t,g,i,raw in self.items:
            if t==0x220557DA:
                strings=parse_stbl(raw)
                self.assertIn('M33',strings[0x3FCE8D06])
                for (source,destination),key in zip(ROUTES,KEYS):
                    self.assertIn('{}'.format(source),strings[key])
                    self.assertIn('{}'.format(destination),strings[key])
                names.update(strings)
        self.assertEqual(len(IDS),6)

    def test_old_m29_interaction_tunings_unchanged(self):
        for original,now in zip(self.original,self.items):
            self.assertEqual(original[:3],now[:3])
            if original[0] in (0xE882D22F,0x03E9D964,0x545AC67A):
                self.assertEqual(original,now)


if __name__=='__main__':
    unittest.main()
