"""M38 static hierarchy regression, pending M37 parent compatibility in game."""
import struct
import unittest
import xml.etree.ElementTree as ET
from tooling.build_m38_three_class_menu import (
    package_bytes,NEW_ROOT,CATEGORY_IDS,SETTINGS_CATEGORY,
    TYPE_CATEGORY,TYPE_SIMDATA,TYPE_INTERACTION,
    ENROLL_IDS,REMOVE_CLASS_IDS,NEW_VIEW_IDS,TRANSFER_IDS,ROUTES,SETTINGS_IDS)
from tooling.simdata_release_gate import resources,inspect_bytes


class AllClassesMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=resources(package_bytes())

    def test_category_tree_and_simdata_are_paired(self):
        categories={}
        sims={}
        for t,g,i,raw in self.records:
            if t==TYPE_CATEGORY:
                categories[i]=ET.fromstring(raw)
            elif t==TYPE_SIMDATA:
                sims[i]=raw
        self.assertEqual(len(categories),5)
        self.assertEqual(set(categories),set(sims))
        self.assertEqual(set(categories),{NEW_ROOT,*CATEGORY_IDS,SETTINGS_CATEGORY})
        self.assertTrue(all(0<cid<2**31 for cid in categories))
        for cid in set(categories)-{NEW_ROOT}:
            self.assertEqual(categories[cid].find('./T[@n="_parent"]').text,
                             str(NEW_ROOT))
            self.assertEqual(struct.unpack_from('<Q',sims[cid],0x5c)[0],NEW_ROOT)
        self.assertIsNone(categories[NEW_ROOT].find('./T[@n="_parent"]'))

    def test_only_actions_for_class_in_each_child(self):
        actions={}
        for typ,g,iid,raw in self.records:
            if typ!=TYPE_INTERACTION:
                continue
            category=ET.fromstring(raw).find('./T[@n="category"]')
            if category is not None:
                actions[iid]=int(category.text)
        for klass in (1,2,3):
            expected=CATEGORY_IDS[klass-1]
            for iid in (ENROLL_IDS[klass-1],REMOVE_CLASS_IDS[klass-1],
                        NEW_VIEW_IDS[klass-1]):
                self.assertEqual(actions[iid],expected)
        for iid,(src,dest) in zip(TRANSFER_IDS,ROUTES):
            self.assertEqual(actions[iid],CATEGORY_IDS[src-1])

    def test_settings_inside_settings_and_activation_in_root(self):
        actions={}
        for typ,g,iid,raw in self.records:
            if typ==TYPE_INTERACTION:
                category=ET.fromstring(raw).find('./T[@n="category"]')
                if category is not None:
                    actions[iid]=int(category.text)
        self.assertEqual(actions[SETTINGS_IDS[0]],NEW_ROOT)
        self.assertEqual(actions[SETTINGS_IDS[1]],NEW_ROOT)
        self.assertEqual(actions[SETTINGS_IDS[2]],SETTINGS_CATEGORY)
        self.assertEqual(actions[SETTINGS_IDS[3]],SETTINGS_CATEGORY)

    def test_package_structural_gate(self):
        info=inspect_bytes(package_bytes())
        self.assertEqual(info['status'],'STATIC_GATE_PASSED')
        self.assertEqual(info['resource_count'],35)
        self.assertEqual(info['category_count'],5)
        self.assertEqual(info['simdata_count'],5)


if __name__=='__main__':
    unittest.main()
