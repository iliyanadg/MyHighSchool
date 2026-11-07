"""M161/M163: automatic re-arm after Save As and menu commits."""
import ast
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'classroom_control'))
import mhs_classroom_bootstrap as bootstrap


class HomeRegistryRearmTests(unittest.TestCase):
    def test_committed_edit_rechecks_at_home(self):
        controller=types.ModuleType('mhs145_classroom_controller')
        controller.zone_schedule=lambda:(100,None)
        controller.SCHOOL_SCHEDULES=frozenset((277657,279958))
        calls=[]
        with patch.dict(sys.modules,{'mhs145_classroom_controller':controller}), \
             patch.object(bootstrap,'refresh',side_effect=lambda:calls.append(1)):
            self.assertTrue(bootstrap.registry_changed_at_home())
            self.assertEqual(calls,[1])

    def test_school_menu_write_does_not_reinstall_midday(self):
        controller=types.ModuleType('mhs145_classroom_controller')
        controller.zone_schedule=lambda:(200,277657)
        controller.SCHOOL_SCHEDULES=frozenset((277657,279958))
        calls=[]
        with patch.dict(sys.modules,{'mhs145_classroom_controller':controller}), \
             patch.object(bootstrap,'refresh',side_effect=lambda:calls.append(1)):
            self.assertFalse(bootstrap.registry_changed_at_home())
            self.assertEqual(calls,[])

    def test_refresh_recursion_guard(self):
        controller=types.ModuleType('mhs145_classroom_controller')
        controller.zone_schedule=lambda:(100,None)
        controller.SCHOOL_SCHEDULES=frozenset((277657,279958))
        observed=[]
        def during_refresh():
            observed.append(bootstrap.registry_changed_at_home())
        with patch.dict(sys.modules,{'mhs145_classroom_controller':controller}), \
             patch.object(bootstrap,'refresh',side_effect=during_refresh):
            self.assertTrue(bootstrap.registry_changed_at_home())
        self.assertEqual(observed,[False])


class SameZoneSaveAsWatcherTests(unittest.TestCase):
    def watcher_function(self):
        path=ROOT/'src'/'m145_class2_playable'/'mhs145_classroom_controller.py'
        tree=ast.parse(path.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                  and n.name=='_m141_start_watcher')
        return compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec')

    def test_save_as_slot_changed_at_home_refreshes_without_extra_alarm(self):
        alarm=types.ModuleType('alarms')
        clock=types.ModuleType('clock')
        handlers=[]
        alarm.add_alarm=lambda owner,interval,callback,repeating: (
            handlers.append(callback) or 'alarm-handle')
        clock.interval_in_sim_minutes=lambda number:number
        changed=[]
        controller=types.ModuleType('mhs_classroom_bootstrap')
        controller.refresh=lambda reload=False:changed.append(reload)
        runtime=types.SimpleNamespace(
            active=True,m141_watcher_timer=None,
            in_school=lambda:False,m141_start_error=None,
            slot='15')
        env={
            'current_slot':lambda allow_travel=False:'16',
            '_m141_cancel_alarm':lambda h:None,
        }
        exec(self.watcher_function(),env)
        with patch.dict(sys.modules,{
            'alarms':alarm,'clock':clock,'mhs_classroom_bootstrap':controller}):
            env['_m141_start_watcher'](runtime)
            self.assertEqual(len(handlers),1)
            handlers[0]('alarm-handle')
        self.assertEqual(changed,[True])

    def test_unchanged_slot_does_not_refresh(self):
        alarm=types.ModuleType('alarms')
        clock=types.ModuleType('clock')
        handlers=[]
        alarm.add_alarm=lambda owner,interval,callback,repeating: (
            handlers.append(callback) or 'alarm-handle')
        clock.interval_in_sim_minutes=lambda number:number
        changed=[]
        controller=types.ModuleType('mhs_classroom_bootstrap')
        controller.refresh=lambda reload=False:changed.append(reload)
        runtime=types.SimpleNamespace(
            active=True,m141_watcher_timer=None,
            in_school=lambda:False,m141_start_error=None,
            slot='15')
        env={'current_slot':lambda allow_travel=False:'15',
             '_m141_cancel_alarm':lambda h:None}
        exec(self.watcher_function(),env)
        with patch.dict(sys.modules,{
            'alarms':alarm,'clock':clock,'mhs_classroom_bootstrap':controller}):
            env['_m141_start_watcher'](runtime)
            handlers[0]('alarm-handle')
        self.assertEqual(changed,[])


if __name__=='__main__':
    unittest.main()
