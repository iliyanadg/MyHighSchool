"""M37 prevents 64-bit parent tuning reference from silently breaking pie menu."""
import struct
import unittest
import xml.etree.ElementTree as ET
from tooling.build_m37_small_root import (
    package_bytes,NEW_ROOT,CATEGORY_ID,BASE_CATEGORY,TYPE_CATEGORY,
    TYPE_SIMDATA,SIMDATA_GROUP,TYPE_INTERACTION)
from tooling.simdata_release_gate import resources,inspect_bytes


class RootIdRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=resources(package_bytes())

    def test_all_category_tuning_ids_are_positive_31_bit(self):
        ids=[iid for t,g,iid,raw in self.rows if t==TYPE_CATEGORY]
        self.assertEqual(set(ids),{NEW_ROOT,CATEGORY_ID})
        self.assertTrue(all(0<id<2**31 for id in ids))
        self.assertGreater(BASE_CATEGORY,2**31)

    def test_root_uses_same_instance_as_simdata(self):
        ids={iid for t,g,iid,raw in self.rows if t==TYPE_CATEGORY}
        paired={iid for t,g,iid,raw in self.rows if t==TYPE_SIMDATA}
        self.assertEqual(ids,paired)

    def test_child_parent_references_new_31_bit_root(self):
        for t,g,iid,raw in self.rows:
            if t==TYPE_CATEGORY and iid==CATEGORY_ID:
                self.assertEqual(ET.fromstring(raw).find('./T[@n="_parent"]').text,str(NEW_ROOT))
            if t==TYPE_SIMDATA and iid==CATEGORY_ID:
                self.assertEqual(struct.unpack_from('<Q',raw,0x5c)[0],NEW_ROOT)

    def test_every_root_menu_interaction_remapped(self):
        seen_root=0
        seen_child=0
        for t,g,iid,raw in self.rows:
            if t!=TYPE_INTERACTION:
                continue
            field=ET.fromstring(raw).find('./T[@n="category"]')
            if field is not None:
                self.assertNotEqual(field.text,str(BASE_CATEGORY))
                self.assertIn(int(field.text),{NEW_ROOT,CATEGORY_ID})
                seen_root+=field.text==str(NEW_ROOT)
                seen_child+=field.text==str(CATEGORY_ID)
        self.assertGreaterEqual(seen_root,10)
        self.assertEqual(seen_child,2)

    def test_structural_gate(self):
        result=inspect_bytes(package_bytes())
        self.assertEqual(result['status'],'STATIC_GATE_PASSED')
        self.assertEqual(result['category_count'],2)
        self.assertEqual(result['simdata_count'],2)


if __name__=='__main__':
    unittest.main()
