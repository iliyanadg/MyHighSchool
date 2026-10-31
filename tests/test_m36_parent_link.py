"""M36 regression: parent linkage is exactly the delta from M35B."""
import struct
import unittest
import xml.etree.ElementTree as ET
from tooling.build_m36_parent_link import (
    package_bytes,BASE_CATEGORY,CATEGORY_ID,TYPE_CATEGORY,TYPE_SIMDATA,
    SIMDATA_GROUP)
from tooling.build_m35b_two_actions import package_bytes as m35b
from tooling.simdata_release_gate import resources,inspect_bytes


class ParentLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=resources(m35b())
        cls.new=resources(package_bytes())

    def test_only_new_parent_link_changed(self):
        self.assertEqual(len(self.base),29)
        self.assertEqual(len(self.new),29)
        for before,after in zip(self.base,self.new):
            self.assertEqual(before[:3],after[:3])
            if before[2]!=CATEGORY_ID:
                self.assertEqual(before,after)

    def test_xml_and_simdata_refer_to_same_parent(self):
        dic={(t,g,i):raw for t,g,i,raw in self.new}
        child=ET.fromstring(dic[(TYPE_CATEGORY,0,CATEGORY_ID)])
        self.assertEqual(child.find('./T[@n="_parent"]').text,str(BASE_CATEGORY))
        parent=ET.fromstring(dic[(TYPE_CATEGORY,0,BASE_CATEGORY)])
        self.assertIsNone(parent.find('./T[@n="_parent"]'))
        self.assertEqual(struct.unpack_from('<Q',
            dic[(TYPE_SIMDATA,SIMDATA_GROUP,CATEGORY_ID)],0x5c)[0],
            BASE_CATEGORY)
        self.assertEqual(struct.unpack_from('<Q',
            dic[(TYPE_SIMDATA,SIMDATA_GROUP,BASE_CATEGORY)],0x5c)[0],0)

    def test_two_categories_and_pairing_still_structurally_valid(self):
        audit=inspect_bytes(package_bytes())
        self.assertEqual(audit['status'],'STATIC_GATE_PASSED')
        self.assertEqual(audit['category_count'],2)
        self.assertEqual(audit['simdata_count'],2)


if __name__=='__main__':
    unittest.main()
