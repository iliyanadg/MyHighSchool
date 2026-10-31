"""M35B controlled change: add second class 1 item to existing new category."""
import unittest
import xml.etree.ElementTree as ET
from tooling.build_m35b_two_actions import (
    package_bytes, CATEGORY_ID, REMOVE_CLASS1, VIEW_ONLY_INTERACTION)
from tooling.build_m35_category_smoke import package_bytes as build_m35
from tooling.simdata_release_gate import resources, inspect_bytes

T_INT=0xE882D22F
T_CAT=0x03E9D964
T_SIMDATA=0x545AC67A


class M35BDualMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=resources(build_m35())
        cls.now=resources(package_bytes())

    def test_two_actions_belong_to_one_new_category(self):
        refs={}
        for typ,g,i,raw in self.now:
            if typ!=T_INT:
                continue
            node=ET.fromstring(raw).find('./T[@n="category"]')
            if node is not None:
                refs[i]=int(node.text)
        self.assertEqual({i for i,v in refs.items() if v==CATEGORY_ID},
                         {VIEW_ONLY_INTERACTION,REMOVE_CLASS1})

    def test_no_new_categories_added_over_m35(self):
        self.assertEqual(len(self.now),len(self.old))
        self.assertEqual(inspect_bytes(package_bytes())['category_count'],2)
        self.assertEqual(inspect_bytes(package_bytes())['simdata_count'],2)

    def test_only_removal_interaction_changed(self):
        for before,after in zip(self.old,self.now):
            self.assertEqual(before[:3],after[:3])
            if before[2]!=REMOVE_CLASS1:
                self.assertEqual(before,after)
        for typ,g,i,raw in self.now:
            if typ in (T_CAT,T_SIMDATA):
                self.assertIn((typ,g,i,raw),self.old)


if __name__=='__main__':
    unittest.main()
