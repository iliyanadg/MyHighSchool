"""M113 home per-save MHS roster handoff (synthetic EA services)."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))
sys.path.insert(0,str(ROOT/'src'/'m109_activation'))
sys.path.insert(0,str(ROOT/'src'/'m113_controller'))

from mhs113_live_home_bridge import prepare_live_home_snapshot
from tests.test_m108_native_invitation import CLASSES,PLAYABLE,CORE


def fake_home(school=False,slot='11',base_slot='11',
              core=None,active=True,zone=111):
    local={'status':'LOCAL_REGISTRY_VERIFIED',
           'save_slot':base_slot,
           'classes':CLASSES,
           'playable':PLAYABLE,
           'assigned_roles':dict(CORE) if core is None else core}
    if not active:
        local={'status':'BLOCKED',
               'reason':'activate two MHS classes first'}
    services=types.ModuleType('services')
    services.current_zone=lambda:types.SimpleNamespace(id=zone)
    def venue():
        s=types.SimpleNamespace(guid64=277657 if school else 10)
        return types.SimpleNamespace(get_zone_director=lambda:
                                     types.SimpleNamespace(_schedule=s))
    services.venue_service=venue
    services.time_service=lambda:types.SimpleNamespace(sim_now=
        types.SimpleNamespace(absolute_ticks=lambda:15000))
    dt=types.ModuleType('date_and_time')
    dt.sim_ticks_per_day=lambda:1000
    bridge=types.ModuleType('mhs_m2_game_bridge')
    bridge.current_slot=lambda allow_travel=False:slot
    source=types.ModuleType('mhs105_live_preflight')
    source._base_data=lambda:local
    return {'services':services,'date_and_time':dt,
            'mhs_m2_game_bridge':bridge,
            'mhs105_live_preflight':source}


class M113LiveHomeTests(unittest.TestCase):
    def test_exact_manual_roles_and_two_classes_read_no_hooks(self):
        with patch.dict(sys.modules,fake_home()):
            r=prepare_live_home_snapshot()
        self.assertEqual(r['status'],'HOME_PLAN_READY_NOT_GAME_AUTHORIZED')
        self.assertEqual(r['selected_students'],16)
        self.assertEqual(r['selected_playable'],3)
        self.assertEqual(r['selected_core'],5)
        self.assertEqual(r['selected_base'],8)
        self.assertEqual(r['plan']['home_zone'],'111')
        self.assertEqual(r['plan']['sim_day'],15)
        self.assertFalse(r['hooks_installed'])
        self.assertFalse(r['game_modified'])
        self.assertFalse(r['exact_16_attendance_verified'])

    def test_not_at_school_and_no_wrong_save_reuse(self):
        for modules,reason in (
            (fake_home(school=True),'MUST_START_FROM_HOME_NOT_SCHOOL'),
            (fake_home(slot='12',base_slot='11'),
             'MHS_ROSTER_OR_CORE_ROLES_UNAVAILABLE'),
            (fake_home(zone=None),'CURRENT_HOME_ZONE_UNAVAILABLE')):
            with patch.dict(sys.modules,modules):
                r=prepare_live_home_snapshot()
            self.assertEqual(r['status'],'HOME_PREFLIGHT_BLOCKED')
            self.assertEqual(r['reason'],reason)
            self.assertFalse(r['hooks_installed'])

    def test_missing_manually_chosen_role_never_auto_filled(self):
        missing=dict(CORE)
        missing.pop(next(iter(missing)))
        with patch.dict(sys.modules,fake_home(core=missing)):
            r=prepare_live_home_snapshot()
        self.assertEqual(r['reason'],
                         'INVALID_EXACT_3_PLAYABLE_5_CORE_8_BASE')
        self.assertNotIn('plan',r)

    def test_inactive_registry_stays_blocked(self):
        with patch.dict(sys.modules,fake_home(active=False)):
            r=prepare_live_home_snapshot()
        self.assertEqual(r['reason'],'activate two MHS classes first')
        self.assertFalse(r['game_modified'])


if __name__=='__main__':
    unittest.main()
