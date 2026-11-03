"""M111 opt-in command registration and safety tests, no real Sims."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m111_bouncer'))

def load():
    state={'zone':111,'day':12,'slot':'11','school':False,
           'reads':0,'commands':{},'output':[]}
    sims4=types.ModuleType('sims4')
    cmds=types.ModuleType('sims4.commands')
    class CommandType: Live='Live'
    cmds.CommandType=CommandType
    def register(name,command_type):
        def decorated(fn):
            state['commands'][name]=fn
            return fn
        return decorated
    cmds.Command=register
    cmds.output=lambda msg,connection=None:state['output'].append(msg)
    sims4.commands=cmds

    services=types.ModuleType('services')
    services.current_zone=lambda:types.SimpleNamespace(id=state['zone'])
    services.time_service=lambda:types.SimpleNamespace(sim_now=
        types.SimpleNamespace(absolute_ticks=lambda:state['day']*1000))
    def venue():
        schedule=types.SimpleNamespace(guid64=277657 if state['school']
                                       else 123)
        return types.SimpleNamespace(get_zone_director=lambda:
            types.SimpleNamespace(_schedule=schedule))
    services.venue_service=venue

    dt=types.ModuleType('date_and_time')
    dt.sim_ticks_per_day=lambda:1000
    identity=types.ModuleType('mhs_m2_game_bridge')
    identity.current_slot=lambda allow_travel=False:state['slot']
    bridge=types.ModuleType('mhs111_live_school_bridge')
    bridge.SCHOOL_SCHEDULES=frozenset((277657,279958))
    def snapshot(phase):
        state['reads']+=1
        return {'kind':'MOCK','status':'SINGLE_PHASE_JOB_MEMBERSHIPS_DIFFER',
                'post_bouncer_barrier_verified':False,
                'exact_16_native_membership_verified':False,
                'full_school_day_verified':False,
                'two_classroom_seating_verified':False}
    bridge.inspect_current_school_ea_jobs=snapshot

    fake={'sims4':sims4,'sims4.commands':cmds,'services':services,
          'date_and_time':dt,'mhs_m2_game_bridge':identity,
          'mhs111_live_school_bridge':bridge}
    spec=importlib.util.spec_from_file_location(
        'm111_game_test_unique',str(ROOT/'src'/'m111_bouncer'/
                                  'mhs111_game_probe.py'))
    mod=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,fake):
        spec.loader.exec_module(mod)
    return mod,state


class M111GameCommandTests(unittest.TestCase):
    def test_import_registers_three_commands_without_game_modification(self):
        mod,state=load()
        self.assertEqual(set(state['commands']),
                         {'mhs111.arm','mhs111.check','mhs111.status'})
        self.assertIsNone(mod._ARMED)
        self.assertIsNone(mod._LAST)

    def test_home_arm_and_school_check_one_read_only_snapshot(self):
        mod,state=load()
        self.assertIn('PRONTA',mod.arm())
        state['school']=True
        state['zone']=777
        with patch.object(mod,'_write') as write:
            self.assertIn('REPORT',mod.check())
            write.assert_called_once()
        self.assertEqual(state['reads'],1)
        self.assertTrue(mod._LAST['capture_same_save_day'])
        self.assertTrue(mod._LAST['phase_selected_by_user_not_game_verified'])
        self.assertFalse(mod._LAST['exact_16_native_membership_verified'])
        self.assertFalse(mod._LAST['post_bouncer_barrier_verified'])
        self.assertTrue(mod._LAST['no_ea_hooks_installed_by_m111'])

    def test_wrong_day_prevents_situation_readback(self):
        mod,state=load()
        mod.arm()
        state['zone']=777
        state['school']=True
        state['day']=13
        with patch.object(mod,'_write'):
            mod.check()
        self.assertEqual(state['reads'],0)
        self.assertEqual(mod._LAST['status'],'WRONG_SAVE_OR_GAME_DAY')

    def test_wrong_save_blocks_readback(self):
        mod,state=load()
        mod.arm()
        state['zone']=777
        state['school']=True
        state['slot']='12'
        with patch.object(mod,'_write'):
            mod.check()
        self.assertEqual(state['reads'],0)
        self.assertEqual(mod._LAST['status'],'WRONG_SAVE_OR_GAME_DAY')

    def test_school_start_blocked_and_no_report(self):
        mod,state=load()
        state['school']=True
        self.assertIn('BLOCCATA',mod.arm())
        self.assertIsNone(mod._ARMED)
        self.assertIn('NON PREPARATA',mod.check())

    def test_still_at_home_does_not_read_jobs(self):
        mod,state=load()
        mod.arm()
        with patch.object(mod,'_write'):
            mod.check()
        self.assertEqual(mod._LAST['status'],'NOT_TRAVELLED_TO_SCHOOL')
        self.assertEqual(state['reads'],0)

    def test_json_is_atomic_and_has_no_student_writes(self):
        mod,state=load()
        with tempfile.TemporaryDirectory() as root:
            with patch.object(mod,'DIR',root):
                data=mod._unknown('READ_ONLY')
                mod._write(data)
                report=json.loads((Path(root)/mod.FILE).read_text())
                self.assertEqual(report['status'],'READ_ONLY')
                self.assertFalse(report['game_modified'])
                self.assertFalse(report['post_bouncer_barrier_verified'])
                self.assertFalse((Path(root)/(mod.FILE+'.tmp')).exists())


if __name__=='__main__':
    unittest.main()
