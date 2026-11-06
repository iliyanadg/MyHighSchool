"""Regression: changing school days must not uninstall the live EA hooks.

This tests the shipped bootstrap.refresh() with a fake EA controller and
real session_decision(), without importing The Sims 4 into the test runner.
"""
import sys
import types
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'classroom_control'))
import mhs_classroom_bootstrap as bootstrap


class DailyLifecycleTests(TestCase):
    def run_refresh(self, old_day, new_day, reload=False, invalid=False):
        events = []
        runtime = types.SimpleNamespace(
            slot='1', school_day=('1', old_day), active=True,
            school_ready=True, m145_patch_result={'applied': True},
            m140_patch_result={'applied': True}, error='')
        def begin(key):
            events.append(('begin', key))
            if invalid:
                raise ValueError('ROSTER_CHANGED')
            runtime.school_day = key
            return True
        def stop():
            events.append(('stop', None))
            runtime.active = False
            return True
        runtime.begin_school_day = begin
        runtime.stop = stop

        class Store:
            def __init__(self, folder):
                pass
            def load(self, slot):
                return types.SimpleNamespace(active=True)

        controller = types.ModuleType('mhs145_classroom_controller')
        controller.FOLDER = 'unused'
        controller._RUNTIME = runtime
        controller.SettingsStore = Store
        controller.current_slot = lambda allow_travel=False: 1
        controller.zone_schedule = lambda: (20, 277657)
        controller.SCHOOL_SCHEDULES = frozenset((277657, 279958))
        controller.current_school_day = lambda slot: ('1', new_day)
        controller._install_school_adapters = lambda owner: (
            events.append(('adapters', None)) or True)
        controller._m141_start_trace = lambda owner, origin: (
            events.append(('trace', origin)) or True)
        with patch.dict(sys.modules, {
            'mhs145_classroom_controller': controller,
            'services': types.ModuleType('services'),
        }):
            result = bootstrap.refresh(reload=reload)
        return result, events, controller, runtime

    def test_next_school_day_refreshes_without_uninstalling_hooks(self):
        result, events, controller, runtime = self.run_refresh(5, 6)
        self.assertEqual(result, 'SCHOOL_SESSION_ACTIVE')
        self.assertEqual(events, [
            ('begin', ('1', 6)),
            ('adapters', None),
            ('trace', 'unified_zone_loaded')])
        self.assertIs(controller._RUNTIME, runtime)
        self.assertTrue(runtime.active)
        self.assertEqual(runtime.school_day, ('1', 6))

    def test_same_day_does_not_reset_native_guest_receipts(self):
        result, events, controller, runtime = self.run_refresh(5, 5)
        self.assertEqual(result, 'SCHOOL_SESSION_ACTIVE')
        self.assertEqual(events, [
            ('adapters', None), ('trace', 'unified_zone_loaded')])
        self.assertIs(controller._RUNTIME, runtime)

    def test_explicit_school_reload_still_requires_safe_home_activation(self):
        result, events, controller, runtime = self.run_refresh(
            5, 5, reload=True)
        self.assertEqual(result, 'ACTIVATION_REQUIRES_HOME_NEXT_SCHOOL_DAY')
        self.assertEqual(events, [('stop', None)])
        self.assertIsNone(controller._RUNTIME)
        self.assertFalse(runtime.active)

    def test_invalid_next_day_fails_closed_without_stopping_ea_hooks(self):
        result, events, controller, runtime = self.run_refresh(
            5, 6, invalid=True)
        self.assertEqual(result, 'NEW_SCHOOL_DAY_BLOCKED: ValueError')
        self.assertEqual(events, [('begin', ('1', 6))])
        self.assertIs(controller._RUNTIME, runtime)
        self.assertFalse(runtime.school_ready)
        self.assertTrue(runtime.active)
