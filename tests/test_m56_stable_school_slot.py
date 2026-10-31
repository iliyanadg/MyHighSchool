"""M56 tests: reproducible save-identity bug on school scratch slot."""
import ast
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m2_registry'))
from mhs56_slot_identity import TravelSlotGuard,IdentityError


class StableSchoolSlotTests(unittest.TestCase):
    def test_home_to_school_and_strict_mutations(self):
        guard=TravelSlotGuard()
        with self.assertRaises(IdentityError):
            guard.resolve(0,9101,271,allow_travel=True)
        self.assertEqual(guard.resolve(7,9101,271),'7')
        self.assertEqual(guard.resolve(0,9101,271,allow_travel=True),'7')
        self.assertEqual(guard.last_source,'verified_zone_travel')
        with self.assertRaises(IdentityError):
            guard.resolve(0,9101,271,allow_travel=False)
        self.assertEqual(guard.resolve(0,9101,271,allow_travel=True),'7')

    def test_changed_save_or_household_fails_closed(self):
        guard=TravelSlotGuard()
        guard.resolve(7,9101,271)
        with self.assertRaises(IdentityError):
            guard.resolve(0,9102,271,allow_travel=True)
        with self.assertRaises(IdentityError):
            guard.resolve(0,9101,271,allow_travel=True)
        self.assertEqual(guard.resolve(10,9102,271),'10')
        with self.assertRaises(IdentityError):
            guard.resolve(0,9102,272,allow_travel=True)

    def test_opaque_stable_guid_may_be_hex_or_object(self):
        guard=TravelSlotGuard()
        guid='0x0019aabb'
        self.assertEqual(guard.resolve(19,guid,87),'19')
        self.assertEqual(guard.resolve(0,guid,87,allow_travel=True),'19')
        class GuidObject(object):
            def __str__(self):
                return '0x0019aabb'
        self.assertEqual(guard.resolve(0,GuidObject(),87,allow_travel=True),'19')

    def test_no_inferred_slot_when_guid_missing(self):
        guard=TravelSlotGuard()
        self.assertEqual(guard.resolve(5,None,22),'5')
        with self.assertRaises(IdentityError):
            guard.resolve(0,None,22,allow_travel=True)

    def test_safe_menu_and_runtime_uses_only_travel_reads(self):
        bridge=(ROOT/'src'/'m2_registry'/'mhs_m2_game_bridge.py').read_text()
        visibility=(ROOT/'src'/'m39_visibility'/'mhs39_visibility_ui.py').read_text()
        auto=(ROOT/'src'/'m55_attendance'/'mhs55_attendance_auto.py').read_text()
        staff=(ROOT/'src'/'m53_staff'/'mhs53_staff_ui.py').read_text()
        class_view=(ROOT/'src'/'m29_registry'/'mhs29_controls.py').read_text()
        self.assertIn('def current_slot(allow_travel=False):',bridge)
        self.assertIn('get_save_slot_proto_guid',bridge)
        self.assertIn('current_slot(allow_travel=True)',visibility)
        self.assertIn('current_slot(allow_travel=True)',auto)
        self.assertIn('current_slot(allow_travel=True)',class_view)
        self.assertIn("mode in ('view','teachers_view','all')",staff)
        self.assertIn('if current_slot()!=slot:',staff)
        for text in (bridge,visibility,auto,staff,class_view):
            ast.parse(text)


if __name__=='__main__':
    unittest.main()
