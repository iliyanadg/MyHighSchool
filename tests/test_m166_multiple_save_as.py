"""M166: multiple Save As copies sharing the same EA GUID do not share data.

The Sims 4 can return a scratch slot after restart. Its *save title* is extra
identity evidence, but a copy is accepted ONLY after full SimInfo validation.
"""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for folder in ('m2_registry', 'm53_staff', 'm97_core_reservations',
               'classroom_control'):
    sys.path.insert(0, str(ROOT / 'src' / folder))

from mhs56_slot_identity import (
    NamedSaveBindings, TravelSlotGuard, synthetic_slot_for_named_save)
from mhs_m2_store import RosterStore
from mhs_m2_roster import SchoolRoster
from mhs34_settings import SettingsStore, SchoolSettings
from mhs53_staff_store import StaffStore, StaffRoster
from mhs97_core_role_store import CoreRoleStore, CoreRoleRoster
import mhs_m2_game_bridge as bridge


class NamedBindingsTests(unittest.TestCase):
    def test_separate_titles_same_guid(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = NamedSaveBindings(str(Path(folder) / 'names.json'))
            self.assertTrue(cache.remember('10', '0xABC', 'Originale', 721))
            self.assertTrue(cache.remember('16', '0xABC', 'Copia', 721))
            self.assertEqual(cache.unique('0xABC', 'Originale'), '10')
            self.assertEqual(cache.unique('0xABC', 'Copia'), '16')
            self.assertFalse(cache.remember('17', '0xABC', 'Copia', 721))
            self.assertEqual(cache.unique('0xABC', 'Copia'), '16')
            self.assertIsNone(cache.unique('0xABC', 'Terza'))

    def test_named_storage_is_deterministic_and_distinct(self):
        a = synthetic_slot_for_named_save('2481979395', 'Originale')
        b = synthetic_slot_for_named_save('2481979395', 'Copia')
        c = synthetic_slot_for_named_save('2481979395', 'Copia 2')
        self.assertEqual(a, synthetic_slot_for_named_save('2481979395',
                                                            'Originale'))
        self.assertEqual(len(set((a, b, c))), 3)
        self.assertTrue(all(int(x) > 0 for x in (a, b, c)))


class MultipleSaveAsGameIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = self.temp.name
        self.guid = '2481979395'
        self.household_id = 721
        self.title = 'Originale'
        self.slot = 0xFFFFFFFF
        self.zone = object()
        self.info = {}
        for i in range(100, 117):
            self.info[i] = types.SimpleNamespace(
                sim_id=i, age='TEEN', species='HUMAN',
                is_selectable=i in (100, 101, 102))
        for i in range(501, 510):
            self.info[i] = types.SimpleNamespace(
                sim_id=i, age='ADULT', species='HUMAN',
                is_selectable=False)
        self.manager = types.SimpleNamespace(get=self.info.get)
        self.bindings = bridge._slot_cache()
        self.bindings = type(self.bindings)(
            str(Path(self.folder) / 'MHS_VerifiedSaveIdentity.json'))
        self.named = NamedSaveBindings(
            str(Path(self.folder) / 'MHS_VerifiedSaveNames.json'))
        self.staff = {'principal':'501','teacher1':'502','teacher2':'503',
                      'teacher3':None,'custodians':['504','505'],
                      'cafeteria':['506','507','508']}
        for slot in ('10','16'):
            self.write_roster(slot)
            self.assertTrue(self.bindings.remember(slot, self.guid,
                                                   self.household_id))
        self.services = types.ModuleType('services')
        self.services.get_persistence_service=lambda:types.SimpleNamespace(
            get_save_slot_proto_buff=lambda:types.SimpleNamespace(
                slot_id=self.slot,slot_name=self.title),
            get_save_slot_proto_guid=lambda:self.guid)
        self.services.active_household=lambda:types.SimpleNamespace(
            id=self.household_id,
            sim_info_gen=lambda:iter(self.info[i] for i in (100,101,102)))
        self.services.sim_info_manager=lambda:self.manager
        self.services.current_zone=lambda:self.zone
        kinds = types.ModuleType('sims.sim_info_types')
        kinds.Age = types.SimpleNamespace(
            TEEN='TEEN',YOUNGADULT='YOUNGADULT',ADULT='ADULT',ELDER='ELDER')
        kinds.Species=types.SimpleNamespace(HUMAN='HUMAN')
        sims=types.ModuleType('sims')
        sims.sim_info_types=kinds
        controller=types.ModuleType('mhs145_classroom_controller')
        controller.SCHOOL_SCHEDULES=frozenset((277657,279958))
        controller.zone_schedule=lambda:(100,None)
        controller._RUNTIME=None
        self.mods=patch.dict(sys.modules,{
            'services':self.services,'sims':sims,'sims.sim_info_types':kinds,
            'mhs145_classroom_controller':controller})
        self.mods.start()
        self.addCleanup(self.mods.stop)
        self.patch_slot = patch.object(bridge,'_slot_cache',
                                       lambda:self.bindings)
        self.patch_names=patch.object(bridge,'_named_slot_cache',
                                      lambda:self.named)
        self.patch_slot.start()
        self.patch_names.start()
        self.addCleanup(self.patch_slot.stop)
        self.addCleanup(self.patch_names.stop)
        self.cold_start()

    def write_roster(self, slot):
        assignments={str(i):1 if i<108 else 2 for i in range(100,116)}
        SettingsStore(self.folder).save(SchoolSettings(slot,True,2))
        RosterStore(self.folder).save(slot,SchoolRoster(slot,assignments))
        StaffStore(self.folder).save(slot,StaffRoster(slot,self.staff))
        core=CoreRoleStore(self.folder)
        core.save(slot,CoreRoleRoster(slot,{
            'cheer':'103','chess':'104','football':'105',
            'computer':'106','mean':'107'}),core.load(slot).fingerprint())

    def cold_start(self):
        bridge._SLOT_GUARD=TravelSlotGuard()
        bridge._CACHED_RECOVERY=False
        bridge._LAST_BOUND=None
        bridge._LAST_SAVE_TITLE=None
        bridge._LAST_ZONE_TOKEN=None

    def test_original_and_two_save_as_versions_independent_after_restart(self):
        self.title='Originale'
        original=bridge.current_slot()
        self.assertEqual(len(RosterStore(self.folder).load(original).assignments),
                         16)
        self.assertNotIn(original,('10','16'))
        # The copied school starts with exactly the same sixteen students.
        self.cold_start()
        self.title='Copia'
        copy=bridge.current_slot()
        self.assertNotEqual(copy, original)
        self.assertEqual(RosterStore(self.folder).load(copy).assignments,
                         RosterStore(self.folder).load(original).assignments)
        # User changes an enrollment only in Copy. A third Save As in the
        # SAME zone must take the current Copy, not the unrelated Original.
        amended=dict(RosterStore(self.folder).load(copy).assignments)
        amended.pop('115')
        amended['116']=2
        RosterStore(self.folder).save(copy, SchoolRoster(copy,amended))
        self.title='Copia 2'
        third=bridge.current_slot()
        self.assertNotEqual(third, original)
        self.assertNotEqual(third, copy)
        self.assertIn('116',RosterStore(self.folder).load(third).assignments)
        self.assertNotIn('116',RosterStore(self.folder).load(original).assignments)
        self.assertEqual(len(RosterStore(self.folder).load(copy).assignments),16)
        # Cold start each version independently, after the third fork.
        for title,expected in (('Originale',original),('Copia',copy),
                               ('Copia 2',third)):
            self.cold_start()
            self.title=title
            self.assertEqual(bridge.current_slot(),expected)
        self.assertEqual(RosterStore(self.folder).load(copy).assignments,
                         RosterStore(self.folder).load(third).assignments)
        self.assertNotEqual(RosterStore(self.folder).load(original).assignments,
                            RosterStore(self.folder).load(third).assignments)

    def test_without_save_name_legacy_ambiguity_is_still_blocked(self):
        self.title = None
        with self.assertRaisesRegex(bridge.BridgeError,'non verificato'):
            bridge.current_slot()


if __name__ == '__main__':
    unittest.main()
