"""M106 Mac PILOT source graph, not a final gameplay release."""
import ast
import unittest
from pathlib import Path
from tooling.build_mhs106_pilot import (
    script_sources,EXPECTED_SCRIPTS,UI,MODULES)
from tooling.build_mhs98_roles import package_bytes
from tooling.simdata_release_gate import inspect_bytes

ROOT=Path(__file__).resolve().parents[1]


class M106MacPilotTests(unittest.TestCase):
    def test_native_menu_and_python37_source_graph(self):
        scripts=script_sources()
        self.assertEqual(len(scripts),EXPECTED_SCRIPTS)
        self.assertEqual(len({s.name for s in scripts}),EXPECTED_SCRIPTS)
        self.assertEqual(next(s for s in scripts
                              if s.name=='mhs55_attendance_ui.py'),UI)
        names={s.name for s in scripts}
        for name in MODULES:
            self.assertIn(name,names)
        for name in ('mhs105_game_controller.py',
                     'mhs57_filter_runtime.py','mhs98_core_role_ui.py',
                     'mhs105_live_preflight.py','mhs93_verified_jobs.py'):
            self.assertIn(name,names)
        for script in scripts:
            ast.parse(script.read_text(encoding='utf-8'))

    def test_m106_loader_registers_native_commands(self):
        loader=UI.read_text()
        self.assertIn('import mhs106_game_controller',loader)
        control=(ROOT/'src'/'m106_roster_first'/
                 'mhs106_game_controller.py').read_text()
        for command in ('mhs106.arm','mhs106.check','mhs106.off'):
            self.assertIn(command,control)
        self.assertIn('m57._filtered=_filtered',control)
        self.assertIn('return _OLD_FILTER(original,service,newargs,newkwargs,mode)',
                      control)

    def test_m106_pilot_instructions_have_real_line_breaks(self):
        # Guard against escaped-backslash lines like the old M109 README.
        tree=ast.parse((ROOT/'tooling'/'build_mhs106_pilot.py')
                       .read_text(encoding='utf-8'))
        assignments=[node.value for node in ast.walk(tree)
                     if isinstance(node,ast.Assign)
                     and any(isinstance(target,ast.Name) and target.id=='notes'
                             for target in node.targets)]
        self.assertEqual(len(assignments),1)
        self.assertIsInstance(assignments[0],ast.Str)
        instructions=assignments[0].s
        self.assertGreaterEqual(instructions.count('\n'),15)
        self.assertNotIn('\\n',instructions)

    def test_no_direct_spawn_or_schedule_count_in_m106(self):
        folder=ROOT/'src'/'m106_roster_first'
        src='\n'.join((folder/name).read_text() for name in MODULES)
        for unsafe in ('create_situation(', 'spawn_sim(', 'add_trait(',
                       'remove_trait(', 'approved_base_count(',
                       'SituationGuestList('):
            self.assertNotIn(unsafe,src)

    def test_original_m98_package_resources_preserved(self):
        resources=inspect_bytes(package_bytes())
        self.assertEqual(resources['resource_count'],76)
        self.assertEqual(resources['status'],'STATIC_GATE_PASSED')


if __name__=='__main__':
    unittest.main()
