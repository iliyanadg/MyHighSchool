"""A Save As fork can import MHS settings without replacing either EA save."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for directory in ('m2_registry','m53_staff','m97_core_reservations','classroom_control'):
    sys.path.insert(0,str(ROOT/'src'/directory))
from mhs_m2_store import RosterStore
from mhs_m2_roster import SchoolRoster
from mhs34_settings import SettingsStore, SchoolSettings
from mhs53_staff_store import StaffStore, StaffRoster
from mhs97_core_role_store import CoreRoleStore, CoreRoleRoster
from mhs_save_as_copy import (
    prepare_copy,import_copy,import_unique_copy,eligible_source_slots,
    SaveAsCopyError)


class SaveAsCloneTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=self.temp.name
        self.source='41'
        self.target='42'
        self.teen_ids=[str(i) for i in range(100,116)]
        self.played=self.teen_ids[:3]
        self.names={
            'principal':'501','teacher1':'502','teacher2':'503',
            'teacher3':None,'custodians':['504','505'],
            'cafeteria':['506','507','508']}
        self.staff_ids=list(range(501,509))
        self.sim_infos={}
        for sid in self.teen_ids:
            self.sim_infos[int(sid)]=SimpleNamespace(
                age='TEEN',species='HUMAN',is_selectable=sid in self.played)
        for sid in self.staff_ids:
            self.sim_infos[int(sid)]=SimpleNamespace(
                age='ADULT',species='HUMAN',is_selectable=False)
        self.manager=SimpleNamespace(get=self.sim_infos.get)
        self.write_source(self.source)

    def write_source(self,slot):
        assignments={str(sid):(1 if j<8 else 2)
                     for j,sid in enumerate(range(100,116))}
        SettingsStore(self.folder).save(SchoolSettings(slot,True,2))
        RosterStore(self.folder).save(slot,SchoolRoster(slot,assignments))
        StaffStore(self.folder).save(slot,StaffRoster(slot,self.names))
        core={'cheer':'103','chess':'104','football':'105',
              'computer':'106','mean':'107'}
        store=CoreRoleStore(self.folder)
        store.save(slot,CoreRoleRoster(slot,core),store.load(slot).fingerprint())

    def opts(self):
        return (self.manager,'TEEN','HUMAN',('YOUNGADULT','ADULT','ELDER'),
                self.played)

    def state(self):
        return {p.name:p.read_bytes() for p in Path(self.folder).glob('*.json')}

    def test_full_import_preserves_all_four_registries_and_source_bytes(self):
        before=self.state()
        response=import_unique_copy(self.folder,self.target,*self.opts())
        self.assertEqual(response['students'],16)
        self.assertEqual(response['staff'],8)
        self.assertEqual(response['roles'],5)
        self.assertEqual(response['source'],self.source)
        self.assertEqual(response['target'],self.target)
        self.assertEqual(RosterStore(self.folder).load(self.target).assignments,
                         RosterStore(self.folder).load(self.source).assignments)
        self.assertEqual(StaffStore(self.folder).load(self.target).roles,
                         StaffStore(self.folder).load(self.source).roles)
        self.assertEqual(CoreRoleStore(self.folder).load(self.target).roles,
                         CoreRoleStore(self.folder).load(self.source).roles)
        self.assertTrue(SettingsStore(self.folder).load(self.target).active)
        for name,blob in before.items():
            self.assertEqual((Path(self.folder)/name).read_bytes(),blob)
        self.assertFalse((Path(self.folder)/
                         ('Ultima_modifica_slot_'+self.target+'.json')).exists())
        for name in self.state():
            if name.endswith('_slot_'+self.target+'.json'):
                self.assertEqual(self.target,__import__('json').loads(
                    (Path(self.folder)/name).read_text())['slot'])

    def test_never_overwrite_even_partial_target(self):
        custom=SettingsStore(self.folder).path(self.target)
        Path(custom).write_bytes(b'pre-existing data must not be lost')
        before=self.state()
        with self.assertRaisesRegex(SaveAsCopyError,'TARGET_SETTINGS_INVALID'):
            import_copy(self.folder,self.source,self.target,*self.opts())
        self.assertEqual(before,self.state())

    def test_source_age_and_identity_require_actual_current_sim_ids(self):
        for field,value in (('age','ADULT'),('species','DOG')):
            info=self.sim_infos[108]
            old=getattr(info,field)
            setattr(info,field,value)
            with self.assertRaises(SaveAsCopyError):
                prepare_copy(self.folder,self.source,self.target,*self.opts())
            setattr(info,field,old)
        self.sim_infos.pop(503)
        with self.assertRaisesRegex(SaveAsCopyError,'SAVED_SIM_MISSING'):
            prepare_copy(self.folder,self.source,self.target,*self.opts())
        self.assertFalse(any('_slot_42' in name for name in self.state()))

    def test_unrelated_household_is_not_a_matching_source(self):
        with self.assertRaisesRegex(SaveAsCopyError,'HOUSEHOLD_DOES_NOT_MATCH'):
            prepare_copy(self.folder,self.source,self.target,self.manager,'TEEN',
                         'HUMAN',('ADULT',),['999999'])
        self.assertEqual(eligible_source_slots(self.folder,self.target,
                self.manager,'TEEN','HUMAN',('ADULT',),['999999']),())

    def test_identical_multiple_sources_are_safe_to_import(self):
        self.write_source('46')
        found=eligible_source_slots(self.folder,self.target,*self.opts())
        self.assertEqual(tuple(row[0] for row in found),('41','46'))
        report=import_unique_copy(self.folder,self.target,*self.opts())
        self.assertEqual(report['source'],'41')
        self.assertEqual(report['students'],16)

    def test_different_multiple_candidates_not_guessed(self):
        self.write_source('46')
        alternative=StaffStore(self.folder).load('46')
        different=dict(self.names)
        different['principal']='509'
        self.sim_infos[509]=SimpleNamespace(
            age='ADULT',species='HUMAN',is_selectable=False)
        StaffStore(self.folder).save('46',StaffRoster('46',different))
        with self.assertRaisesRegex(SaveAsCopyError,'MULTIPLE_SOURCE_SAVES'):
            import_unique_copy(self.folder,self.target,*self.opts())
        report=import_copy(self.folder,'41',self.target,*self.opts())
        self.assertEqual(report['source'],'41')

    def test_incomplete_source_and_bad_core_roles_not_copied(self):
        source=CoreRoleStore(self.folder).path(self.source)
        os.unlink(source)
        with self.assertRaisesRegex(SaveAsCopyError,'SOURCE_CORE_MISSING'):
            import_copy(self.folder,self.source,self.target,*self.opts())
        self.assertFalse(any('_slot_42' in name for name in self.state()))

    def test_second_copy_is_idempotent_and_source_does_not_change(self):
        first=import_copy(self.folder,self.source,self.target,*self.opts())
        self.assertEqual(first['copied_files'],4)
        original=self.state()
        second=import_copy(self.folder,self.source,self.target,*self.opts())
        self.assertEqual(second['copied_files'],0)
        self.assertEqual(second['unchanged_files'],4)
        self.assertEqual(original,self.state())

    def test_partial_matching_target_imports_only_missing_files(self):
        settings=SchoolSettings(self.target,True,2)
        SettingsStore(self.folder).save(settings)
        before=Path(SettingsStore(self.folder).path(self.target)).read_bytes()
        result=import_copy(self.folder,self.source,self.target,*self.opts())
        self.assertEqual((result['copied_files'],result['unchanged_files']),(3,1))
        self.assertEqual(Path(SettingsStore(self.folder).path(self.target)).read_bytes(),
                         before)
        self.assertEqual(len(RosterStore(self.folder).load(self.target).assignments),16)

    def test_different_existing_students_are_never_overwritten(self):
        SettingsStore(self.folder).save(SchoolSettings(self.target,True,2))
        other=SchoolRoster(self.target,{'100':1})
        RosterStore(self.folder).save(self.target,other)
        before=self.state()
        with self.assertRaisesRegex(SaveAsCopyError,'TARGET_STUDENTS_DIFFERS'):
            import_copy(self.folder,self.source,self.target,*self.opts())
        self.assertEqual(self.state(),before)

    def test_write_failure_rolls_back_only_new_destination_files(self):
        real_open=os.open
        def inject(path,flags,*args):
            if path.endswith('Personale_slot_42.json'):
                raise OSError('inject disk failure')
            return real_open(path,flags,*args)
        before=self.state()
        with patch('mhs_save_as_copy.os.open',side_effect=inject):
            with self.assertRaisesRegex(SaveAsCopyError,'COPY_ABORTED_OSError'):
                import_copy(self.folder,self.source,self.target,*self.opts())
        self.assertEqual(before,self.state())
        self.assertFalse(any('_slot_42' in name for name in self.state()))


    def test_m156_auto_import_at_home_on_new_save(self):
        from mhs_classroom_bootstrap import _recover_save_as_at_home
        from types import ModuleType
        from unittest.mock import patch
        import sys
        controller=SimpleNamespace(FOLDER=self.folder, SettingsStore=SettingsStore)
        game_services=ModuleType('services')
        active=SimpleNamespace(sim_info_gen=lambda: (
            SimpleNamespace(sim_id=int(s),age='TEEN',species='HUMAN')
            for s in self.played))
        game_services.active_household=lambda: active
        game_services.sim_info_manager=lambda: self.manager
        sims=ModuleType('sims')
        kinds=ModuleType('sims.sim_info_types')
        kinds.Age=SimpleNamespace(TEEN='TEEN',YOUNGADULT='YOUNGADULT',
                                  ADULT='ADULT',ELDER='ELDER')
        kinds.Species=SimpleNamespace(HUMAN='HUMAN')
        sims.sim_info_types=kinds
        with patch.dict(sys.modules,{'services':game_services,'sims':sims,
                                     'sims.sim_info_types':kinds}):
            result=_recover_save_as_at_home(controller,self.target,False)
            self.assertEqual(result,'IMPORTED_FROM_41')
            self.assertTrue(SettingsStore(self.folder).load(self.target).active)
            self.assertEqual(len(RosterStore(self.folder).load(self.target).assignments),16)
            again=_recover_save_as_at_home(controller,self.target,False)
            self.assertEqual(again,'TARGET_ALREADY_CONFIGURED')

    def test_m159_same_session_save_as_prefers_previous_active_slot(self):
        from mhs_classroom_bootstrap import _recover_save_as_at_home
        from types import ModuleType
        from unittest.mock import patch
        import sys
        self.write_source('46')
        different=dict(self.names)
        different['principal']='509'
        self.sim_infos[509]=SimpleNamespace(
            age='ADULT',species='HUMAN',is_selectable=False)
        StaffStore(self.folder).save('46',StaffRoster('46',different))
        game_services=ModuleType('services')
        game_services.active_household=lambda: SimpleNamespace(
            sim_info_gen=lambda: (SimpleNamespace(
                sim_id=int(s),age='TEEN',species='HUMAN') for s in self.played))
        game_services.sim_info_manager=lambda:self.manager
        kinds=ModuleType('sims.sim_info_types')
        kinds.Age=SimpleNamespace(TEEN='TEEN',YOUNGADULT='YOUNGADULT',
                                  ADULT='ADULT',ELDER='ELDER')
        kinds.Species=SimpleNamespace(HUMAN='HUMAN')
        sims=ModuleType('sims')
        sims.sim_info_types=kinds
        controller=SimpleNamespace(FOLDER=self.folder,SettingsStore=SettingsStore)
        with patch.dict(sys.modules,{'services':game_services,'sims':sims,
                                     'sims.sim_info_types':kinds}):
            result=_recover_save_as_at_home(
                controller,self.target,False,previous_slot='41')
        self.assertEqual(result,'IMPORTED_FROM_41')
        self.assertEqual(
            StaffStore(self.folder).load(self.target).roles,
            StaffStore(self.folder).load('41').roles)

    def test_m156_auto_import_refuses_school_or_ambiguous_sources(self):
        from mhs_classroom_bootstrap import _recover_save_as_at_home
        controller=SimpleNamespace(FOLDER=self.folder,SettingsStore=SettingsStore)
        self.assertEqual(_recover_save_as_at_home(controller,self.target,True),'NOT_HOME')
        self.write_source('46')
        # Give one prior save different staff; divergent sources are
        # ambiguous even if their roster of 16 teens still matches.
        other=dict(self.names)
        other['principal']='509'
        self.sim_infos[509]=SimpleNamespace(
            age='ADULT',species='HUMAN',is_selectable=False)
        StaffStore(self.folder).save('46',StaffRoster('46',other))
        # Ambiguity must never be solved by choosing the most recent file.
        from types import ModuleType
        from unittest.mock import patch
        import sys
        game_services=ModuleType('services')
        game_services.active_household=lambda: SimpleNamespace(
            sim_info_gen=lambda: (SimpleNamespace(
                sim_id=int(s),age='TEEN',species='HUMAN') for s in self.played))
        game_services.sim_info_manager=lambda:self.manager
        kinds=ModuleType('sims.sim_info_types')
        kinds.Age=SimpleNamespace(TEEN='TEEN',YOUNGADULT='YOUNGADULT',
                                  ADULT='ADULT',ELDER='ELDER')
        kinds.Species=SimpleNamespace(HUMAN='HUMAN')
        sims=ModuleType('sims')
        sims.sim_info_types=kinds
        with patch.dict(sys.modules,{'services':game_services,'sims':sims,
                                     'sims.sim_info_types':kinds}):
            result=_recover_save_as_at_home(controller,self.target,False)
        self.assertIn('MULTIPLE_SOURCE_SAVES',result)
        self.assertFalse(any('_slot_42' in name for name in self.state()))


    def test_m165_cold_start_with_old_legacy_registry_bootstraps_without_cheat(self):
        import sys
        import mhs_m2_game_bridge as bridge
        from mhs56_slot_identity import (
            TravelSlotGuard, VerifiedSlotBindings, synthetic_slot_for_guid)
        from types import ModuleType
        from unittest.mock import patch
        guid='0x12345'
        new_slot=synthetic_slot_for_guid(guid)
        before={name:Path(self.folder,name).read_bytes()
                for name in self.state()}
        self.assertFalse(Path(self.folder,
            'MHS_VerifiedSaveIdentity.json').exists())
        self.assertFalse(Path(RosterStore(self.folder).path(new_slot)).exists())
        game_services=ModuleType('services')
        game_services.get_persistence_service=lambda:SimpleNamespace(
            get_save_slot_proto_buff=lambda:SimpleNamespace(slot_id=0xffffffff),
            get_save_slot_proto_guid=lambda:guid)
        game_services.active_household=lambda:SimpleNamespace(
            id=721,sim_info_gen=lambda:(
                SimpleNamespace(sim_id=int(s),age='TEEN',species='HUMAN')
                for s in self.played))
        game_services.sim_info_manager=lambda:self.manager
        kinds=ModuleType('sims.sim_info_types')
        kinds.Age=SimpleNamespace(TEEN='TEEN',YOUNGADULT='YOUNGADULT',
                                  ADULT='ADULT',ELDER='ELDER')
        kinds.Species=SimpleNamespace(HUMAN='HUMAN')
        sims=ModuleType('sims')
        sims.sim_info_types=kinds
        controller=ModuleType('mhs145_classroom_controller')
        controller.zone_schedule=lambda:(100,None)
        controller.SCHOOL_SCHEDULES=frozenset((277657,279958))
        controller._RUNTIME=None
        cache=VerifiedSlotBindings(str(Path(self.folder)/
            'MHS_VerifiedSaveIdentity.json'))
        with patch.object(bridge,'_slot_cache',lambda:cache), \
             patch.dict(sys.modules,{'services':game_services,'sims':sims,
                 'sims.sim_info_types':kinds,
                 'mhs145_classroom_controller':controller}):
            bridge._SLOT_GUARD=TravelSlotGuard()
            bridge._CACHED_RECOVERY=False
            self.assertEqual(bridge.current_slot(),new_slot)
            self.assertEqual(cache.unique(guid,721),new_slot)
            self.assertEqual(len(RosterStore(self.folder).load(new_slot).assignments),16)
            self.assertTrue(SettingsStore(self.folder).load(new_slot).active)
            self.assertEqual(StaffStore(self.folder).load(new_slot).roles,
                             StaffStore(self.folder).load(self.source).roles)
            # A second Python session still resolves without another import.
            bridge._SLOT_GUARD=TravelSlotGuard()
            bridge._CACHED_RECOVERY=False
            self.assertEqual(bridge.current_slot(),new_slot)
        for name,blob in before.items():
            self.assertEqual(Path(self.folder,name).read_bytes(),blob)

    def test_m165_two_different_legacy_schools_fail_closed(self):
        import sys
        import mhs_m2_game_bridge as bridge
        from mhs56_slot_identity import TravelSlotGuard, VerifiedSlotBindings
        from types import ModuleType
        from unittest.mock import patch
        self.write_source('46')
        other=dict(self.names)
        other['principal']='509'
        self.sim_infos[509]=SimpleNamespace(
            age='ADULT',species='HUMAN',is_selectable=False)
        StaffStore(self.folder).save('46',StaffRoster('46',other))
        before=self.state()
        game_services=ModuleType('services')
        game_services.get_persistence_service=lambda:SimpleNamespace(
            get_save_slot_proto_buff=lambda:SimpleNamespace(slot_id=0xffffffff),
            get_save_slot_proto_guid=lambda:'0x9876')
        game_services.active_household=lambda:SimpleNamespace(
            id=721,sim_info_gen=lambda:(
                SimpleNamespace(sim_id=int(s),age='TEEN',species='HUMAN')
                for s in self.played))
        game_services.sim_info_manager=lambda:self.manager
        kinds=ModuleType('sims.sim_info_types')
        kinds.Age=SimpleNamespace(TEEN='TEEN',YOUNGADULT='YOUNGADULT',
                                  ADULT='ADULT',ELDER='ELDER')
        kinds.Species=SimpleNamespace(HUMAN='HUMAN')
        sims=ModuleType('sims')
        sims.sim_info_types=kinds
        controller=ModuleType('mhs145_classroom_controller')
        controller.zone_schedule=lambda:(100,None)
        controller.SCHOOL_SCHEDULES=frozenset((277657,279958))
        controller._RUNTIME=None
        cache=VerifiedSlotBindings(str(Path(self.folder)/
            'MHS_VerifiedSaveIdentity.json'))
        with patch.object(bridge,'_slot_cache',lambda:cache), \
             patch.dict(sys.modules,{'services':game_services,'sims':sims,
                 'sims.sim_info_types':kinds,
                 'mhs145_classroom_controller':controller}):
            bridge._SLOT_GUARD=TravelSlotGuard()
            bridge._CACHED_RECOVERY=False
            with self.assertRaises(bridge.BridgeError):
                bridge.current_slot()
            self.assertIn('MULTIPLE_SOURCE_SAVES',bridge._MIGRATION_DIAGNOSTIC)
            self.assertIsNone(cache.unique('0x9876',721))
        self.assertEqual(before,self.state())



if __name__=='__main__':
    unittest.main()
