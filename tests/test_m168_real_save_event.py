"""M168: observed EA save_game_gen events, not guessed title transitions.

Offline tests use the *actual* four MHS JSON stores and a fake native EA
PersistenceService. The game's runtime APIs still require an in-game test.
"""
import sys
import types
import unittest
from unittest.mock import patch

from tests.test_m166_multiple_save_as import MultipleSaveAsGameIdentityTests
from mhs_m2_store import RosterStore
from mhs_m2_roster import SchoolRoster
from mhs34_settings import SettingsStore
from mhs53_staff_store import StaffStore
from mhs97_core_role_store import CoreRoleStore
import mhs_m2_game_bridge as bridge
import mhs168_save_event as save_events


class RealSaveEventsTests(unittest.TestCase):
    write_roster = MultipleSaveAsGameIdentityTests.write_roster
    cold_start = MultipleSaveAsGameIdentityTests.cold_start

    def setUp(self):
        MultipleSaveAsGameIdentityTests.setUp(self)
        controller = sys.modules['mhs145_classroom_controller']
        controller.FOLDER = self.folder
        controller.SettingsStore = SettingsStore
        self.preferred = None
        self.services.get_persistence_service = lambda: types.SimpleNamespace(
            get_save_slot_proto_buff=lambda: types.SimpleNamespace(
                slot_id=self.slot, slot_name=self.title,
                preferred_manual_slot_id=self.preferred),
            get_save_slot_proto_guid=lambda: self.guid)
        self.slot = 10
        self.title = 'Originale'
        bridge._COMMITTED_SAVE_ANCHOR = None
        save_events._LAST_STATUS = 'NOT_SEEN'
        self.assertEqual(bridge.current_slot(allow_travel=True), '10')

    def _save(self, slot, title):
        before = save_events._snapshot_source()
        self.assertIsNotNone(before)
        data = types.SimpleNamespace(slot_id=slot, slot_name=title)
        outcome = save_events._after_save(data, before)
        self.assertIn(
            outcome.split('_HOME_REFRESH_PENDING')[0],
            ('COPIED_10_TO_17','COPIED_17_TO_18',
             'SAVED_SAME_SLOT_10','SAVED_SAME_SLOT_17',
             'SAVED_SAME_SLOT_18'))
        self.slot=0xffffffff
        self.preferred=slot
        self.title=title
        return str(slot)

    def test_save_then_two_save_as_then_cold_restart_all_three(self):
        self._save(10, 'Originale')
        self.assertEqual(RosterStore(self.folder).load('10').class_members(1),
                         RosterStore(self.folder).load('10').class_members(1))

        first=self._save(17,'Copia 1')
        self.assertEqual(bridge.current_slot(allow_travel=True), first)
        self.assertTrue(SettingsStore(self.folder).load(first).active)
        self.assertEqual(len(RosterStore(self.folder).load(first).assignments),16)
        self.assertEqual(StaffStore(self.folder).load(first).roles,
                         StaffStore(self.folder).load('10').roles)
        self.assertEqual(CoreRoleStore(self.folder).load(first).roles,
                         CoreRoleStore(self.folder).load('10').roles)

        roster=RosterStore(self.folder).load(first)
        revised=dict(roster.assignments)
        revised.pop('115')
        revised['116']=2
        RosterStore(self.folder).save(first,SchoolRoster(first,revised))
        second=self._save(18,'Copia 2')
        self.assertTrue(SettingsStore(self.folder).load(second).active)
        self.assertIn('116',RosterStore(self.folder).load(second).assignments)
        self.assertNotIn('116',RosterStore(self.folder).load('10').assignments)
        # Repeated ordinary Save to the same slot doesn't change the
        # external student, staff, or Core role registries.
        before=RosterStore(self.folder).load(second).to_json()
        self._save(18,'Copia 2')
        self.assertEqual(RosterStore(self.folder).load(second).to_json(),before)

        for title,slot in (('Originale',10),('Copia 1',17),('Copia 2',18)):
            self.cold_start()
            bridge._COMMITTED_SAVE_ANCHOR=None
            self.slot=0xffffffff
            self.preferred=slot
            self.title=title
            self.assertEqual(bridge.current_slot(allow_travel=True),str(slot))
            self.assertTrue(SettingsStore(self.folder).load(str(slot)).active)

    def test_preferred_manual_id_distinguishes_identical_guid_household(self):
        self.cold_start()
        bridge._COMMITTED_SAVE_ANCHOR=None
        self.title = None
        self.slot = 0xffffffff
        self.preferred = 16
        self.assertEqual(bridge.current_slot(allow_travel=True),'16')

    def test_different_zone_aborts_copy(self):
        before=save_events._snapshot_source()
        self.zone=object()
        self.assertEqual(
            save_events._after_save(
                types.SimpleNamespace(slot_id=17,slot_name='Other'),before),
            'ZONE_CHANGED_NO_COPY')
        self.assertFalse(SettingsStore(self.folder).load('17').active)

    def test_scratch_autosave_does_not_create_any_data(self):
        before=save_events._snapshot_source()
        outcome=save_events._after_save(
            types.SimpleNamespace(slot_id=0xffffffff,slot_name='Autosave'),
            before)
        self.assertEqual(outcome,'SKIPPED_SCRATCH_OR_AUTOSAVE')
        self.assertFalse(SettingsStore(self.folder).load('17').active)

    def test_save_generator_chain_preserved_and_installed_once(self):
        events=[]
        class DummyPersistence:
            def save_game_gen(self,timeline,data,*args,**kwargs):
                events.append(('EA',timeline,args,kwargs))
                yield 'saving'
                return 'EA_SAVED'
        cls=DummyPersistence
        with patch.object(save_events,'_snapshot_source',
                          return_value=('10',id(self.zone))), \
             patch.object(save_events,'_after_save',
                          side_effect=lambda d,s:events.append(('MHS',d.slot_id))):
            self.assertTrue(save_events.install(cls))
            installed=cls.save_game_gen
            self.assertTrue(save_events.install(cls))
            self.assertIs(cls.save_game_gen,installed)
            obj=cls()
            gen=obj.save_game_gen('t',types.SimpleNamespace(slot_id=17),
                                  1,reason='manual')
            self.assertEqual(next(gen),'saving')
            with self.assertRaises(StopIteration) as done:
                next(gen)
            self.assertEqual(done.exception.value,'EA_SAVED')
        self.assertEqual(events[0],('EA','t',(1,),{'reason':'manual'}))
        self.assertEqual(events[1],('MHS',17))

    def test_failed_native_generator_does_not_copy_or_swallow_error(self):
        events=[]
        class DummyPersistence:
            def save_game_gen(self,timeline,data):
                yield 'saving'
                raise RuntimeError('EA_SAVE_FAILED')
        with patch.object(save_events,'_snapshot_source',
                          return_value=('10',id(self.zone))), \
             patch.object(save_events,'_after_save',
                          side_effect=lambda *args: events.append(args)):
            save_events.install(DummyPersistence)
            gen=DummyPersistence().save_game_gen(
                't',types.SimpleNamespace(slot_id=17))
            self.assertEqual(next(gen),'saving')
            with self.assertRaisesRegex(RuntimeError,'EA_SAVE_FAILED'):
                next(gen)
        self.assertEqual(events,[])


if __name__ == '__main__':
    unittest.main()
