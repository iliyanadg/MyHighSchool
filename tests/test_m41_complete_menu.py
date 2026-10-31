"""All five classes/settings category pairs match EA TDesc fields and parent graph."""
import struct
import unittest
import xml.etree.ElementTree as ET

from tooling.build_m41_complete_menu import (
    package_bytes,SCHEMA_HASH,CATEGORY_TREE,CATEGORY_TYPE,SIMDATA_TYPE,
    SIMDATA_GROUP,NEW_ROOT,CATEGORY_IDS,SETTINGS_CATEGORY)
from tooling.build_m39_conditional_menu import package_bytes as m39
from tooling.simdata_release_gate import resources,inspect_bytes


class M41EAReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=resources(m39())
        cls.new=resources(package_bytes())

    def test_category_tree_exactly_five_paired(self):
        tuning={r[2]:ET.fromstring(r[3]) for r in self.new
                if r[0]==CATEGORY_TYPE}
        binary={r[2]:r[3] for r in self.new if r[0]==SIMDATA_TYPE}
        self.assertEqual(set(tuning),CATEGORY_TREE)
        self.assertEqual(set(binary),CATEGORY_TREE)
        self.assertEqual(len(tuning),5)

    def test_all_collapsible_false_as_in_current_ea_data(self):
        for typ,group,iid,blob in self.new:
            if typ==CATEGORY_TYPE:
                root=ET.fromstring(blob)
                self.assertEqual(root.find('./T[@n="_collapsible"]').text,
                                 'False')
            if typ==SIMDATA_TYPE:
                self.assertEqual(blob[0x40],0)
                self.assertIn(struct.pack('<I',SCHEMA_HASH),blob)
                self.assertIn(b'always_show_disabled_interactions',blob)

    def test_parent_link_both_xml_simdata_for_each_class(self):
        x={r[2]:ET.fromstring(r[3]) for r in self.new
           if r[0]==CATEGORY_TYPE}
        b={r[2]:r[3] for r in self.new if r[0]==SIMDATA_TYPE}
        self.assertIsNone(x[NEW_ROOT].find('./T[@n="_parent"]'))
        self.assertEqual(struct.unpack_from('<Q',b[NEW_ROOT],0x5c)[0],0)
        for ident in set(x)-{NEW_ROOT}:
            self.assertEqual(x[ident].find('./T[@n="_parent"]').text,
                             str(NEW_ROOT))
            self.assertEqual(struct.unpack_from('<Q',b[ident],0x5c)[0],
                             NEW_ROOT)

    def test_only_boolean_field_differs_from_existing_m39(self):
        self.assertEqual(len(self.old),len(self.new))
        for a,b in zip(self.old,self.new):
            self.assertEqual(a[:3],b[:3])
            if a[0] not in (CATEGORY_TYPE,SIMDATA_TYPE):
                self.assertEqual(a,b)
            elif a[0]==SIMDATA_TYPE:
                test=bytearray(a[3])
                self.assertEqual(test[0x40],1)
                test[0x40]=0
                self.assertEqual(bytes(test),b[3])

    def test_static_package_gate(self):
        report=inspect_bytes(package_bytes())
        self.assertEqual(report['status'],'STATIC_GATE_PASSED')
        self.assertEqual(report['resource_count'],35)
        self.assertEqual(report['category_count'],5)
        self.assertEqual(report['simdata_count'],5)


if __name__=='__main__':
    unittest.main()
