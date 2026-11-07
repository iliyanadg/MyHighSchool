"""M160: durable identity comes from actual EA slot, not a save filename."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm2_registry'))
from mhs56_slot_identity import TravelSlotGuard, VerifiedSlotBindings
import mhs_m2_game_bridge as bridge


class BindingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / 'MHS_VerifiedSaveIdentity.json')

    def test_write_and_restart_unique_slot(self):
        a = VerifiedSlotBindings(self.path)
        self.assertTrue(a.remember('15', '0xabc', 721))
        # A second instance simulates a completely new game process.
        b = VerifiedSlotBindings(self.path)
        self.assertEqual(b.unique('0xabc', 721), '15')
        self.assertIsNone(b.unique('0xabc', 722))
        self.assertIsNone(b.unique('0xdef', 721))

    def test_same_guid_multiple_real_slots_fails_closed(self):
        a = VerifiedSlotBindings(self.path)
        self.assertTrue(a.remember(15, '0xabc', 721))
        self.assertTrue(a.remember(16, '0xabc', 721))
        self.assertIsNone(VerifiedSlotBindings(self.path).unique('0xabc', 721))

    def test_stale_or_corrupted_file_not_used(self):
        Path(self.path).write_text('{"version":1,"bindings":[{"slot":"15"}]}')
        self.assertIsNone(VerifiedSlotBindings(self.path).unique('0xabc', 721))

    def test_source_is_never_created_from_scratch_slot(self):
        a = VerifiedSlotBindings(self.path)
        self.assertFalse(a.remember(0xffffffff, '0xabc', 721))
        self.assertIsNone(a.unique('0xabc', 721))

    def test_new_household_same_save_can_be_bound_when_verified(self):
        a = VerifiedSlotBindings(self.path)
        a.remember(15, '0xabc', 721)
        a.remember(15, '0xabc', 722)
        self.assertEqual(a.unique('0xabc', 721), '15')
        self.assertEqual(a.unique('0xabc', 722), '15')


class BridgeColdStartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.binding = VerifiedSlotBindings(str(
            Path(self.tmp.name) / 'MHS_VerifiedSaveIdentity.json'))
        self.slot = 15
        self.guid = '0xabc'
        self.household = 721
        self.persistence = types.SimpleNamespace(
            get_save_slot_proto_buff=lambda: types.SimpleNamespace(
                slot_id=self.slot),
            get_save_slot_proto_guid=lambda: self.guid)
        self.services = types.ModuleType('services')
        self.services.get_persistence_service=lambda: self.persistence
        self.services.active_household=lambda: types.SimpleNamespace(
            id=self.household)
        self.controller = types.ModuleType('mhs145_classroom_controller')
        self.controller._RUNTIME=None
        self.controller.zone_schedule=lambda: (100, None)
        self.controller.SCHOOL_SCHEDULES=frozenset((277657,279958))
        self.patches=[
            patch.object(bridge,'_slot_cache',lambda: self.binding),
            patch.object(bridge,'_saved_roster_matches_live_game',
                         lambda slot: str(slot)=='15'),
            patch.dict(sys.modules,{'services':self.services,
                                    'mhs145_classroom_controller':self.controller})]
        for obj in self.patches:
            obj.start()
            self.addCleanup(obj.stop)
        bridge._SLOT_GUARD=TravelSlotGuard()
        bridge._CACHED_RECOVERY=False
        bridge._LAST_BOUND=None

    def test_cold_restart_from_previous_live_real_slot(self):
        self.assertEqual(bridge.current_slot(), '15')
        self.assertEqual(self.binding.unique(self.guid,self.household),'15')
        # Shut down completely: in-memory guard and controller disappear.
        bridge._SLOT_GUARD=TravelSlotGuard()
        bridge._CACHED_RECOVERY=False
        bridge._LAST_BOUND=None
        self.slot=0xffffffff
        self.assertEqual(bridge.current_slot(allow_travel=False),'15')
        self.assertTrue(bridge._CACHED_RECOVERY)

    def test_unknown_guid_not_assigned_other_save(self):
        bridge.current_slot()
        bridge._SLOT_GUARD=TravelSlotGuard()
        bridge._CACHED_RECOVERY=False
        self.slot=0xffffffff
        self.guid='0xother'
        with self.assertRaisesRegex(bridge.BridgeError,'non verificato'):
            bridge.current_slot(allow_travel=False)

    def test_ambiguous_ancestor_not_guessed(self):
        bridge.current_slot()
        self.binding.remember(16,self.guid,self.household)
        bridge._SLOT_GUARD=TravelSlotGuard()
        bridge._CACHED_RECOVERY=False
        self.slot=0xffffffff
        with self.assertRaisesRegex(bridge.BridgeError,'non verificato'):
            bridge.current_slot(allow_travel=False)

    def test_cold_restart_home_switches_household_safely(self):
        bridge.current_slot()
        bridge._SLOT_GUARD=TravelSlotGuard()
        bridge._CACHED_RECOVERY=False
        self.slot=0xffffffff
        bridge.current_slot()
        self.household=722
        self.assertEqual(bridge.current_slot(),'15')
        self.assertEqual(self.binding.unique(self.guid,722),'15')


if __name__ == '__main__':
    unittest.main()
