"""Pure M39 visibility policy and minimal changed tuning surface tests."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RULES=ROOT/'src'/'m39_visibility'
if str(RULES) not in sys.path:
    sys.path.insert(0,str(RULES))
from mhs39_visibility_rules import allowed,VisibilityError
from tooling.build_m39_conditional_menu import package_bytes,specs
from tooling.build_m38_three_class_menu import package_bytes as m38
from tooling.simdata_release_gate import resources,inspect_bytes


class SchoolVisibilityPolicyTests(unittest.TestCase):
    def test_off_shows_only_enable(self):
        self.assertTrue(allowed(False,2,'enable'))
        for action in ('disable','activate_third','deactivate_third'):
            self.assertFalse(allowed(False,2,action))
        for klass in (1,2,3):
            self.assertFalse(allowed(False,2,'class',klass))

    def test_active_two_classes_has_later_class3_enable(self):
        self.assertTrue(allowed(True,2,'class',1))
        self.assertTrue(allowed(True,2,'class',2))
        self.assertFalse(allowed(True,2,'class',3))
        self.assertTrue(allowed(True,2,'activate_third'))
        self.assertFalse(allowed(True,2,'deactivate_third'))
        self.assertTrue(allowed(True,2,'disable'))
        self.assertFalse(allowed(True,2,'enable'))

    def test_active_three_classes_can_show_third_class(self):
        self.assertTrue(allowed(True,3,'class',3))
        self.assertTrue(allowed(True,3,'deactivate_third'))
        self.assertFalse(allowed(True,3,'activate_third'))

    def test_bad_settings_fail_closed(self):
        for value in (0,1,'yes',None):
            with self.assertRaises(VisibilityError):
                allowed(value,2,'enable')
        with self.assertRaises(VisibilityError):
            allowed(True,4,'class',3)


class ConditionalTuningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=resources(m38())
        cls.new=resources(package_bytes())

    def test_only_action_class_and_module_differ(self):
        self.assertEqual(len(self.old),35)
        self.assertEqual(len(self.new),35)
        for before,after in zip(self.old,self.new):
            self.assertEqual(before[:3],after[:3])
            typ=before[0]
            if typ!=0xE882D22F:
                self.assertEqual(before,after)
            else:
                a=ET.fromstring(before[3])
                b=ET.fromstring(after[3])
                self.assertEqual(b.get('m'),'mhs39_visibility_ui')
                self.assertEqual(b.get('c'),'MHS39_'+a.get('c'))
                b.set('c',a.get('c'))
                b.set('m',a.get('m'))
                self.assertEqual(ET.tostring(a),ET.tostring(b))

    def test_all_action_classes_mapped_and_unique(self):
        self.assertEqual(len(specs()),19)
        self.assertEqual(len(set(specs().values())),19)

    def test_all_tuning_categories_still_pair(self):
        info=inspect_bytes(package_bytes())
        self.assertEqual(info['status'],'STATIC_GATE_PASSED')
        self.assertEqual(info['category_count'],5)
        self.assertEqual(info['simdata_count'],5)


if __name__=='__main__':
    unittest.main()
