"""M109 live command + tiny Mac build: offline regression without Sims."""
import ast
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm109_activation'))

from mhs109_readonly_ea_probe import METHOD_CONTRACT
from tests.test_m109_readonly_ea_probe import fixture
from tooling.build_mhs109_readonly import script_sources, SOURCES, NAME


def load_live_command_with_fake_sims():
    fake_sims = types.ModuleType('sims4')
    cmds = types.ModuleType('sims4.commands')
    class CommandType:
        Live = 'Live'
    cmds.CommandType = CommandType
    cmds.Command = lambda name, command_type: lambda fn: fn
    printed = []
    cmds.output = lambda line, connection=None: printed.append(line)
    fake_sims.commands = cmds
    path = ROOT / 'src' / 'm109_activation' / 'mhs109_game_probe.py'
    spec = importlib.util.spec_from_file_location(
        '_mhs109_live_probe_fixture', str(path))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'sims4':fake_sims, 'sims4.commands':cmds}):
        spec.loader.exec_module(module)
    return module, printed


class M109LiveReadOnlyDiagnosticsTests(unittest.TestCase):

    def test_two_script_archive_has_no_prior_m108_school_controller(self):
        paths=script_sources()
        self.assertEqual(len(paths),2)
        self.assertEqual(set(path.name for path in paths),{
            'mhs109_readonly_ea_probe.py',
            'mhs109_game_probe.py'})
        self.assertTrue(NAME.endswith('.ts4script'))
        content='\n'.join(p.read_text(encoding='utf-8') for p in SOURCES)
        # The probe intentionally lists M108 marker names for conflict
        # detection. A string occurrence is not an imported M108 controller.
        self.assertIn('_mhs108_unified_lessons', content)
        for source in paths:
            tree = ast.parse(source.read_text(encoding='utf-8'),
                             filename=str(source))
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported.append(node.module or '')
            self.assertFalse(any(
                name.startswith('mhs108_') or '.mhs108_' in name
                for name in imported
            ), 'M108 controller imported by read-only probe: {}'.format(
                source.name))
        self.assertNotIn('mhs108_native_precreate',content)
        self.assertNotIn('create_situation(',content)
        self.assertNotIn('clone_for_replace(',content)
        self.assertNotIn('install_offline_only(',content)

    def test_live_game_probe_imports_only_for_explicit_command(self):
        mod,printed=load_live_command_with_fake_sims()
        self.assertEqual(printed,[])
        self.assertEqual(len(mod.MODULES),6)
        self.assertIn('sims4',mod.__dict__)
        # Importing sims4.commands registers the command, but never runs it.
        # The command is not executed at module import time.
        self.assertTrue(callable(mod._m109_probe_command))

    def test_live_class_probes_do_not_write_or_patch_original_ea_methods(self):
        mod,_=load_live_command_with_fake_sims()
        classes=fixture()
        original={key:dict(cls.__dict__) for key,cls in classes.items()}
        fake_modules={}
        for key,(path,name) in mod.MODULES.items():
            fake_modules.setdefault(path,types.ModuleType(path))
            setattr(fake_modules[path],name,classes[key])
        real_import=__import__('importlib').import_module
        def import_source(path):
            if path in fake_modules:
                return fake_modules[path]
            return real_import(path)
        with patch('importlib.import_module',side_effect=import_source):
            result=mod.capture_native_shapes()
        self.assertEqual(result['method_count_available'],
                         len(METHOD_CONTRACT))
        self.assertEqual(result['status'],
                         'METHOD_SHAPES_AVAILABLE_UNVERIFIED')
        self.assertTrue(all(x=='EA_CLASS_LOADED'
                            for x in result['native_modules'].values()))
        self.assertFalse(result['activation_authorized_by_game'])
        self.assertFalse(result['game_modified'])
        self.assertEqual(result['hook_target_count_located_unverified'], 6)
        self.assertEqual(result['hook_target_count_expected'], 6)
        self.assertEqual(result['known_mhs_hook_marker_count'], 0)
        self.assertEqual(result['mhs108_school_hooks_installed'], None)
        self.assertFalse(result['runtime_hook_install_authorized'])
        self.assertEqual(
            {key:dict(cls.__dict__) for key,cls in classes.items()},original)

    def test_broken_ea_import_does_not_invent_method_availability(self):
        mod,_=load_live_command_with_fake_sims()
        with patch('importlib.import_module',
                   side_effect=ImportError('EA not loaded')):
            result=mod.capture_native_shapes()
        self.assertEqual(result['method_count_available'],0)
        self.assertEqual(result['hook_target_count_located_unverified'],0)
        self.assertEqual(result['mhs108_school_hooks_installed'], None)
        self.assertEqual(result['status'],'NATIVE_EA_METHODS_NOT_READY')
        self.assertTrue(all(v=='IMPORT_ImportError'
                            for v in result['native_modules'].values()))
        self.assertFalse(result['activation_authorized_by_game'])

    def test_command_prints_six_stage_status_without_claiming_validity(self):
        mod, printed = load_live_command_with_fake_sims()
        sample = {
            'method_count_available': 15,
            'method_count_expected': 15,
            'hook_target_count_located_unverified': 6,
            'hook_target_count_expected': 6,
            'known_mhs_hook_marker_count': 0,
        }
        with patch.object(mod, 'capture_native_shapes', return_value=sample):
            with patch.object(mod, 'save_native_report',
                              return_value='/tmp/test.json'):
                mod._m109_probe_command()
        self.assertEqual(len(printed), 1)
        self.assertIn('15/15', printed[0])
        self.assertIn('6/6', printed[0])
        self.assertIn('non validati', printed[0])
        self.assertNotIn('funzionante', printed[0])

    def test_known_old_hook_is_reported_not_hidden(self):
        mod, _ = load_live_command_with_fake_sims()
        classes = fixture()
        old = classes['weekly_data'].__dict__['try_start'].__func__
        old._mhs108_unified_lessons = True
        fake_modules = {}
        for key, (path, name) in mod.MODULES.items():
            fake_modules.setdefault(path, types.ModuleType(path))
            setattr(fake_modules[path], name, classes[key])
        with patch('importlib.import_module',
                   side_effect=lambda path: fake_modules[path]):
            report = mod.capture_native_shapes()
        self.assertEqual(report['known_mhs_hook_marker_count'], 1)
        self.assertEqual(report['hook_target_count_located_unverified'], 5)
        self.assertEqual(report['known_mhs_hook_scan'],
                         'KNOWN_MHS_MARKERS_DETECTED')
        self.assertIsNone(report['mhs108_school_hooks_installed'])
        self.assertFalse(report['activation_authorized_by_game'])

    def test_report_written_to_explicit_test_dir_only(self):
        mod,_=load_live_command_with_fake_sims()
        with tempfile.TemporaryDirectory() as folder:
            path=mod.save_native_report({
                'status':'NATIVE_EA_METHODS_NOT_READY',
                'activation_authorized_by_game':False,
            },folder=folder)
            self.assertEqual(os.path.basename(path),mod.REPORT_NAME)
            self.assertTrue(os.path.exists(path))
            self.assertFalse(os.path.exists(path+'.tmp'))

    def test_command_errors_do_not_modify_ea_or_claim_success(self):
        mod,printed=load_live_command_with_fake_sims()
        with patch.object(mod,'capture_native_shapes',
                          side_effect=RuntimeError('test diagnostic error')):
            mod._m109_probe_command()
        self.assertEqual(len(printed),1)
        self.assertIn('Nessuna modifica',printed[0])
        self.assertNotIn('funzionante',printed[0])


if __name__ == '__main__':
    unittest.main()
