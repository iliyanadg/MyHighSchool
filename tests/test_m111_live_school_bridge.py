"""M111 live school/save bridge: synthetic service wiring, no real Sims."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m111_bouncer'))
sys.path.insert(0,str(ROOT/'src'/'m57_selection'))

from mhs111_live_school_bridge import inspect_current_school_ea_jobs
from tests.test_m111_school_job_readback import setup, manifest


def fake_game(active=True, count=2, schedule=277657, slot='11',
              zone_id=777, cohort=None):
    infos, manager, _ = setup()
    chosen = cohort if cohort is not None else manifest()

    class Settings(object):
        def __init__(self):
            self.active=active
            self.class_count=count

    class Store(object):
        def __init__(self, directory):
            self.directory=directory
        def load(self, selected_slot):
            assert selected_slot == slot
            return object()

    class SettingsStore(Store):
        def load(self, selected_slot):
            assert selected_slot == slot
            return Settings()

    class InfoManager(object):
        def get_all(self):
            return tuple(infos)

    class Household(object):
        def sim_info_gen(self):
            return tuple(infos[:2])

    class Director(object):
        _schedule=type('WeeklySchedule',(),{'guid64':schedule})()

    class VenueService(object):
        def get_zone_director(self):
            return Director()

    modules = {}
    services=types.ModuleType('services')
    services.active_household=lambda:Household()
    services.current_zone=lambda:type('Zone',(),{'id':zone_id})()
    services.venue_service=lambda:VenueService()
    services.get_zone_situation_manager=lambda:manager
    services.sim_info_manager=lambda:InfoManager()
    modules['services']=services

    sims=types.ModuleType('sims')
    sims.__path__=[]
    sim_types=types.ModuleType('sims.sim_info_types')
    sim_types.Age=type('Age',(),{'TEEN':'teen'})
    sim_types.Species=type('Species',(),{'HUMAN':'human'})
    sims.sim_info_types=sim_types
    modules['sims']=sims
    modules['sims.sim_info_types']=sim_types

    slotbridge=types.ModuleType('mhs_m2_game_bridge')
    slotbridge.current_slot=lambda allow_travel=False:slot
    modules['mhs_m2_game_bridge']=slotbridge

    roster_mod=types.ModuleType('mhs_m2_store')
    roster_mod.RosterStore=Store
    modules['mhs_m2_store']=roster_mod
    staff_mod=types.ModuleType('mhs53_staff_store')
    staff_mod.StaffStore=Store
    modules['mhs53_staff_store']=staff_mod
    setting_mod=types.ModuleType('mhs34_settings')
    setting_mod.SettingsStore=SettingsStore
    modules['mhs34_settings']=setting_mod
    manifest_mod=types.ModuleType('mhs57_school_manifest')
    manifest_mod.make_manifest=lambda roster, staff, n, teen_ids:chosen
    modules['mhs57_school_manifest']=manifest_mod
    return modules, manager


class M111LiveBridgeTests(unittest.TestCase):
    def test_reads_actual_synthetic_service_and_keeps_bouncer_unproven(self):
        modules, manager=fake_game()
        with patch.dict(sys.modules,modules):
            r=inspect_current_school_ea_jobs('lesson')
        self.assertEqual(r['status'],'SINGLE_PHASE_JOB_MEMBERSHIPS_MATCH_OBSERVED')
        self.assertEqual(r['zone_id'],'777')
        self.assertEqual(r['school_schedule_guid'],277657)
        self.assertTrue(r['roster_slot_verified'])
        self.assertTrue(r['ea_school_schedule_observed'])
        self.assertFalse(r['post_bouncer_barrier_verified'])
        self.assertFalse(r['exact_16_native_membership_verified'])
        self.assertFalse(r['two_classroom_seating_verified'])
        self.assertEqual(manager.calls,16)

    def test_not_active_does_not_read_ea_situations(self):
        modules, manager=fake_game(active=False)
        with patch.dict(sys.modules,modules):
            r=inspect_current_school_ea_jobs('lesson')
        self.assertEqual(r['status'],'MY_HIGH_SCHOOL_NOT_ACTIVE')
        self.assertEqual(manager.calls,0)

    def test_three_classes_blocked_before_ea_reads(self):
        modules, manager=fake_game(count=3)
        with patch.dict(sys.modules,modules):
            r=inspect_current_school_ea_jobs('lesson')
        self.assertEqual(r['status'],'EXACTLY_TWO_CLASSES_REQUIRED')
        self.assertEqual(manager.calls,0)

    def test_non_school_lot_blocks_data_association(self):
        modules, manager=fake_game(schedule=88888)
        with patch.dict(sys.modules,modules):
            r=inspect_current_school_ea_jobs('lesson')
        self.assertEqual(r['status'],'NOT_ORIGINAL_EA_HIGH_SCHOOL_SCHEDULE')
        self.assertEqual(manager.calls,0)

    def test_missing_complete_roster_blocks(self):
        m=manifest()
        m.class_ids=(('1','2'),tuple(str(n) for n in range(9,17)))
        modules, manager=fake_game(cohort=m)
        with patch.dict(sys.modules,modules):
            r=inspect_current_school_ea_jobs('lesson')
        self.assertEqual(r['status'],'REGISTER_IS_NOT_COMPLETE_TWO_BY_EIGHT')
        self.assertEqual(manager.calls,0)

    def test_bad_zone_and_phase_fail_closed(self):
        modules, manager=fake_game(zone_id=None)
        with patch.dict(sys.modules,modules):
            r=inspect_current_school_ea_jobs('lesson')
        self.assertEqual(r['status'],'EA_CURRENT_ZONE_UNAVAILABLE')
        self.assertEqual(manager.calls,0)
        self.assertEqual(inspect_current_school_ea_jobs('lunch')['status'],
                         'PHASE_NOT_SPECIFIED')

    def test_game_service_error_returns_unknown_not_false_success(self):
        modules, manager=fake_game()
        modules['services'].venue_service=lambda:None
        with patch.dict(sys.modules,modules):
            r=inspect_current_school_ea_jobs('lesson')
        self.assertEqual(r['status'],'EA_VENUE_SERVICE_UNAVAILABLE')
        self.assertFalse(r['exact_16_native_membership_verified'])

if __name__=='__main__':
    unittest.main()
