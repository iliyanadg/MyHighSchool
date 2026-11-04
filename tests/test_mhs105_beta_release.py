"""M105 Mac bundle source integrity and conservative runtime boot tests."""
import ast
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from tooling.build_mhs98_roles import package_bytes as m98_package
from tooling.build_mhs105_beta import script_sources,EXPECTED_SCRIPTS,M105_MODULES
from tooling.simdata_release_gate import inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'m105_day_controller'


class M105MacBuildSourceTests(unittest.TestCase):
    def test_single_76_resource_package_preserves_native_role_menu(self):
        report=inspect_bytes(m98_package())
        self.assertEqual(report['status'],'STATIC_GATE_PASSED')
        self.assertEqual(report['resource_count'],76)
        self.assertEqual(report['category_count'],11)

    def test_exact_unique_48_python37_module_sources(self):
        scripts=script_sources()
        names=[p.name for p in scripts]
        self.assertEqual(len(names),EXPECTED_SCRIPTS)
        self.assertEqual(len(set(names)),EXPECTED_SCRIPTS)
        for key in ('mhs98_core_role_ui.py','mhs97_core_role_store.py',
                    'mhs105_game_controller.py','mhs105_schedule_runtime.py',
                    'mhs105_live_preflight.py','mhs104_native_policy.py',
                    'mhs101_original_slot_gate.py','mhs93_verified_jobs.py',
                    'mhs57_filter_runtime.py','mhs55_attendance_ui.py'):
            self.assertIn(key,names)
        self.assertEqual(set(M105_MODULES)|{'mhs55_attendance_ui.py'},
                         {p.name for p in scripts if p.parent==SRC})
        self.assertEqual(next(p for p in scripts
                              if p.name=='mhs55_attendance_ui.py').parent,SRC)

    def test_loader_registers_m105_without_arming(self):
        loader=(SRC/'mhs55_attendance_ui.py').read_text()
        self.assertIn('import mhs105_game_controller',loader)
        self.assertNotIn('import mhs104_native_school_filter',loader)
        self.assertNotIn('mhs105.arm()',loader)

    def test_no_old_unsafe_school_hooks_in_bundle(self):
        names={p.name for p in script_sources()}
        forbidden={'mhs89_precreate_hook.py','mhs101_original_slot_runtime.py',
                   'mhs102_bouncer_observer.py','mhs104_native_school_filter.py'}
        self.assertFalse(names&forbidden)
        text='\n'.join((SRC/name).read_text() for name in M105_MODULES)
        self.assertNotIn('create_situation(',text)
        self.assertNotIn('SituationGuestList(',text)
        self.assertNotIn('approved_base_count(',text)

    def test_schedule_runtime_uses_audit_only_not_m96(self):
        src=(SRC/'mhs105_schedule_runtime.py').read_text()
        self.assertIn('NativeScheduleAudit',src)
        self.assertNotIn('mhs96_exact_school_count',src)
        self.assertNotIn('setattr(WeeklyScheduleDay',src)
        self.assertNotIn('return (8,8)',src)

    def test_python37_syntax_source(self):
        for source in script_sources():
            ast.parse(source.read_text(encoding='utf-8'))


if __name__=='__main__':
    unittest.main()
