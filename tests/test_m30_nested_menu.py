"""M30 nested class-menu checks: resources, references and binary data.

No test in this file can establish live Sims 4 pie-menu compatibility.
"""
import struct
import unittest
import xml.etree.ElementTree as ET

from tooling.build_m30_nested_menu import (
    BASE_CATEGORY, CATEGORY_IDS, CATEGORY_NAMES, NEW_KEYS,
    ENROLL_IDS, REMOVE_CLASS_IDS, NEW_VIEW_IDS,
    TYPE_CATEGORY, TYPE_SIMDATA, TYPE_INTERACTION, TYPE_STBL,
    SIMDATA_GROUP, MAIN_MENU_KEY, OLD_INSTANCE_NAME,
    package_bytes, create_child_simdata, M30BuildError)
from tooling.build_m29_bundle import package_bytes as build_m29
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes


class NestedClassMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=resources(build_m29())
        cls.new=resources(package_bytes())
        cls.lookup={(t,g,i):blob for t,g,i,blob in cls.new}

    def test_package_has_4_category_simdata_pairs(self):
        audit=inspect_bytes(package_bytes())
        self.assertEqual(audit['status'],'STATIC_GATE_PASSED')
        self.assertEqual(audit['category_count'],4)
        self.assertEqual(audit['simdata_count'],4)
        self.assertEqual(len(self.new),23)
        self.assertEqual(len(set(CATEGORY_IDS)),3)
        self.assertTrue(all(0<i<=0x7fffffff for i in CATEGORY_IDS))

    def test_children_link_to_main_parent(self):
        for class_index,iid in enumerate(CATEGORY_IDS):
            xml=self.lookup[(TYPE_CATEGORY,0,iid)]
            root=ET.fromstring(xml)
            self.assertEqual(root.get('s'),str(iid))
            self.assertEqual(root.get('n'),CATEGORY_NAMES[class_index])
            self.assertEqual(root.find('./T[@n="_parent"]').text,str(BASE_CATEGORY))
            self.assertEqual(root.find('./T[@n="_display_name"]').text,
                             '0x{:08X}'.format(NEW_KEYS[class_index]))
            raw=self.lookup[(TYPE_SIMDATA,SIMDATA_GROUP,iid)]
            self.assertEqual(struct.unpack_from('<I',raw,0x44)[0],NEW_KEYS[class_index])
            self.assertEqual(struct.unpack_from('<Q',raw,0x5c)[0],BASE_CATEGORY)
            self.assertTrue(raw.endswith(CATEGORY_NAMES[class_index].encode('ascii')+b'\x00'))

    def test_clones_change_only_named_binary_fields(self):
        old=self.lookup[(TYPE_SIMDATA,SIMDATA_GROUP,BASE_CATEGORY)]
        for iid in CATEGORY_IDS:
            current=self.lookup[(TYPE_SIMDATA,SIMDATA_GROUP,iid)]
            compare=bytearray(current)
            struct.pack_into('<I',compare,0x44,MAIN_MENU_KEY)
            struct.pack_into('<Q',compare,0x5c,0)
            offset=compare.find(CATEGORY_NAMES[CATEGORY_IDS.index(iid)].encode('ascii'))
            compare[offset:offset+20]=OLD_INSTANCE_NAME
            self.assertEqual(bytes(compare),old)
        with self.assertRaises(M30BuildError):
            create_child_simdata(b'DATA',0)

    def test_every_action_in_its_class_not_flat(self):
        for class_index,iid in enumerate(CATEGORY_IDS):
            for interaction in (ENROLL_IDS[class_index],
                                REMOVE_CLASS_IDS[class_index],
                                NEW_VIEW_IDS[class_index]):
                xml=self.lookup[(TYPE_INTERACTION,0,interaction)]
                root=ET.fromstring(xml)
                self.assertEqual(root.find('./T[@n="category"]').text,str(iid))
        # The top-level category should NOT have any of the nine actions.
        for action in ENROLL_IDS+REMOVE_CLASS_IDS+NEW_VIEW_IDS:
            root=ET.fromstring(self.lookup[(TYPE_INTERACTION,0,action)])
            self.assertNotEqual(root.find('./T[@n="category"]').text,str(BASE_CATEGORY))

    def test_english_italian_labels_and_old_texts(self):
        for t,g,i,raw in self.new:
            if t==TYPE_STBL:
                texts=parse_stbl(raw)
                self.assertEqual(len(texts),21)
                self.assertIn('M30',texts[MAIN_MENU_KEY])
                for key in NEW_KEYS:
                    self.assertIn(key,texts)

    def test_old_interaction_identity_and_source_unchanged(self):
        old={(t,g,i):raw for t,g,i,raw in self.old}
        for typ,group,iid,blob in self.new:
            if (typ,group,iid) not in old:
                continue
            if typ in (TYPE_SIMDATA,TYPE_CATEGORY):
                self.assertEqual(old[(typ,group,iid)],blob)
            if typ==TYPE_INTERACTION and iid not in (
                    ENROLL_IDS+REMOVE_CLASS_IDS+NEW_VIEW_IDS):
                self.assertEqual(old[(typ,group,iid)],blob)


if __name__=='__main__':
    unittest.main()
