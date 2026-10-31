"""M36: single variable parent-link test over verified standalone M35B."""
import struct
import unittest
import xml.etree.ElementTree as ET
from tooling.build_m36_nested_class1 import (
    package_bytes, CATEGORY_ID, BASE_CATEGORY,
    TYPE_CATEGORY, TYPE_SIMDATA, SIMDATA_GROUP)
from tooling.build_m35b_two_actions import package_bytes as m35b
from tooling.simdata_release_gate import resources,inspect_bytes


class M36Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=resources(m35b())
        cls.now=resources(package_bytes())

    def test_paired_category_has_root_parent(self):
        x=next(raw for t,g,i,raw in self.now
               if t==TYPE_CATEGORY and i==CATEGORY_ID)
        root=ET.fromstring(x)
        self.assertEqual(root.find('./T[@n="_parent"]').text,str(BASE_CATEGORY))
        b=next(raw for t,g,i,raw in self.now
               if t==TYPE_SIMDATA and g==SIMDATA_GROUP and i==CATEGORY_ID)
        self.assertEqual(struct.unpack_from('<Q',b,0x5c)[0],BASE_CATEGORY)

    def test_exactly_two_category_resources_changed(self):
        modified=[]
        for before,now in zip(self.old,self.now):
            self.assertEqual(before[:3],now[:3])
            if before[3]!=now[3]:
                modified.append((now[0],now[2]))
        self.assertEqual(set(modified),
                         {(TYPE_CATEGORY,CATEGORY_ID),
                          (TYPE_SIMDATA,CATEGORY_ID)})
        self.assertEqual(len(self.old),len(self.now))

    def test_no_regression_in_static_structure(self):
        audit=inspect_bytes(package_bytes())
        self.assertEqual(audit['status'],'STATIC_GATE_PASSED')
        self.assertEqual(audit['category_count'],2)
        self.assertEqual(audit['simdata_count'],2)


if __name__=='__main__':
    unittest.main()
