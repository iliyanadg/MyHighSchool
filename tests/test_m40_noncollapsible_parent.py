"""M40 root/child category collapse flags align with common TS4 nesting examples."""
import struct
import unittest
import xml.etree.ElementTree as ET
from tooling.build_m40_noncollapsible_parent import package_bytes
from tooling.build_m37_small_root import package_bytes as build_m37,NEW_ROOT,CATEGORY_ID
from tooling.simdata_release_gate import resources,inspect_bytes


class MenuCollapseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=resources(build_m37())
        cls.now=resources(package_bytes())

    def test_only_pair_bool_changed(self):
        ids={NEW_ROOT,CATEGORY_ID}
        self.assertEqual(len(self.old),29)
        self.assertEqual(len(self.now),29)
        for a,b in zip(self.old,self.now):
            self.assertEqual(a[:3],b[:3])
            if a[2] not in ids:
                self.assertEqual(a,b)
            elif a[0]==0x545AC67A:
                expected=bytearray(a[3])
                expected[0x40]=0
                self.assertEqual(bytes(expected),b[3])

    def test_xml_category_explicit_false(self):
        categories={}
        for typ,grp,iid,blob in self.now:
            if typ==0x03E9D964:
                categories[iid]=ET.fromstring(blob)
        self.assertEqual(set(categories),{NEW_ROOT,CATEGORY_ID})
        for root in categories.values():
            self.assertEqual(root.find('./T[@n="_collapsible"]').text,'False')
        self.assertEqual(categories[CATEGORY_ID].find('./T[@n="_parent"]').text,
                         str(NEW_ROOT))

    def test_simdata_category_paired_false(self):
        data={iid:blob for typ,grp,iid,blob in self.now if typ==0x545AC67A}
        self.assertEqual(set(data),{NEW_ROOT,CATEGORY_ID})
        for blob in data.values():
            self.assertEqual(blob[0x40],0)
        self.assertEqual(struct.unpack_from('<Q',data[CATEGORY_ID],0x5c)[0],
                         NEW_ROOT)

    def test_static_audit(self):
        info=inspect_bytes(package_bytes())
        self.assertEqual(info['status'],'STATIC_GATE_PASSED')
        self.assertEqual(info['category_count'],2)
        self.assertEqual(info['simdata_count'],2)


if __name__=='__main__':
    unittest.main()
