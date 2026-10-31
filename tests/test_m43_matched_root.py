"""M43: root menu ID matches existing name and all references rewritten."""
import struct
import unittest
import xml.etree.ElementTree as ET

from tooling.build_m43_matched_root import (
    package_bytes,NEW_ROOT,MATCHED_ROOT,ROOT_NAME,
    CATEGORY_TYPE,SIMDATA_TYPE,TYPE_INTERACTION)
from tooling.build_m42_safe_menu import package_bytes as build_m42
from tooling.build_m30_nested_menu import category_id
from tooling.simdata_release_gate import resources,inspect_bytes

class M43Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=resources(build_m42())
        cls.rows=resources(package_bytes())

    def test_root_is_matched_to_own_name(self):
        self.assertEqual(MATCHED_ROOT,category_id(ROOT_NAME))
        self.assertNotEqual(MATCHED_ROOT,NEW_ROOT)
        self.assertTrue(0<MATCHED_ROOT<2**31)
        roots=[(i,ET.fromstring(data)) for t,g,i,data in self.rows
               if t==CATEGORY_TYPE and i==MATCHED_ROOT]
        self.assertEqual(len(roots),1)
        iid,xml=roots[0]
        self.assertEqual(xml.attrib['n'],ROOT_NAME)
        self.assertEqual(int(xml.attrib['s']),iid)
        self.assertIsNone(xml.find('./T[@n="_parent"]'))

    def test_children_reference_matched_root_in_both_data_types(self):
        child_xml={}
        child_simdata={}
        for t,g,i,data in self.rows:
            if t==CATEGORY_TYPE and i!=MATCHED_ROOT:
                node=ET.fromstring(data)
                child_xml[i]=node.find('./T[@n="_parent"]').text
                self.assertEqual(category_id(node.get('n')),i)
            if t==SIMDATA_TYPE:
                if i==MATCHED_ROOT:
                    self.assertEqual(struct.unpack_from('<Q',data,0x5c)[0],0)
                    self.assertIn(ROOT_NAME.encode('ascii'),data)
                else:
                    child_simdata[i]=struct.unpack_from('<Q',data,0x5c)[0]
        self.assertEqual(len(child_xml),4)
        self.assertEqual(set(child_xml),set(child_simdata))
        self.assertEqual(set(child_xml.values()),{str(MATCHED_ROOT)})
        self.assertEqual(set(child_simdata.values()),{MATCHED_ROOT})

    def test_all_actions_keep_target_category(self):
        before={}
        after={}
        for rows,mapping in ((self.old,before),(self.rows,after)):
            for t,g,i,data in rows:
                if t==TYPE_INTERACTION:
                    node=ET.fromstring(data)
                    category=node.find('./T[@n="category"]')
                    mapping[i]=category.text if category is not None else None
        self.assertEqual(set(before),set(after))
        changed=0
        for i,value in before.items():
            if value==str(NEW_ROOT):
                self.assertEqual(after[i],str(MATCHED_ROOT))
                changed+=1
            else:
                self.assertEqual(after[i],value)
        self.assertGreaterEqual(changed,2)

    def test_new_package_is_structurally_valid(self):
        report=inspect_bytes(package_bytes())
        self.assertEqual(report['status'],'STATIC_GATE_PASSED')
        self.assertEqual(report['category_count'],5)
        self.assertEqual(report['simdata_count'],5)
        self.assertEqual(report['resource_count'],35)


if __name__=='__main__':
    unittest.main()
