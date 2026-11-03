"""M110 live command registration with fake Sims module, no actual EA."""
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m110_trace'))
from tooling.build_mhs110_trace import SOURCES, NAME, EXPECTED_MAGIC
from tests.test_m110_trace_core import native


def load_game_trace():
    sims=types.ModuleType('sims4')
    cmds=types.ModuleType('sims4.commands')
    class CommandType:
        Live='Live'
    cmds.CommandType=CommandType
    commands={}
    def decorator(name, command_type):
        def decorated(fn):
            commands[name]=fn
            return fn
        return decorated
    cmds.Command=decorator
    output=[]
    cmds.output=lambda msg, conn=None: output.append(msg)
    sims.commands=cmds
    spec=importlib.util.spec_from_file_location('m110_game_trace_test',str(ROOT/'src'/'m110_trace'/'mhs110_game_trace.py'))
    mod=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'sims4':sims,'sims4.commands':cmds}):
        spec.loader.exec_module(mod)
    return mod,commands,output


class GameTraceTests(unittest.TestCase):
    def test_import_registers_three_commands_without_changing_ea(self):
        mod,cmds,outputs=load_game_trace()
        self.assertEqual(set(cmds),{'mhs110.start','mhs110.stop','mhs110.status'})
        self.assertFalse(mod.TRACER.report()['temporary_runtime_wrappers_active'])
        self.assertEqual(outputs,[])

    def test_live_commands_trace_then_write_json_report(self):
        mod,cmds,outputs=load_game_trace()
        classes,counts=native()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(mod,'_classes',return_value=classes),\
                 patch.object(mod,'_save',side_effect=lambda: 'json'):
                cmds['mhs110.start']()
                self.assertTrue(mod.TRACER.report()['temporary_runtime_wrappers_active'])
                classes['weekly_day'].get_long_term_situation_count(None,None)
                cmds['mhs110.status']()
                cmds['mhs110.stop']()
        self.assertEqual(counts['count'],1)
        self.assertIn('ON',outputs[0])
        self.assertIn('1',outputs[1])
        self.assertIn('ripristinati',outputs[2])
        self.assertFalse(mod.TRACER.report()['temporary_runtime_wrappers_active'])

    def test_stop_without_active_trace_is_not_a_restore_error(self):
        mod, cmds, outputs = load_game_trace()
        with patch.object(mod, '_save') as save:
            cmds['mhs110.stop']()
            save.assert_not_called()
        self.assertIn('NON ATTIVA', outputs[-1])
        self.assertIn('NON sovrascritto', outputs[-1])
        self.assertNotIn('ripristino non confermato', outputs[-1])

    def test_second_stop_preserves_first_saved_report(self):
        mod, cmds, outputs = load_game_trace()
        classes, _ = native()
        with patch.object(mod, '_classes', return_value=classes),\
             patch.object(mod, '_save', return_value='trace.json') as save:
            cmds['mhs110.start']()
            classes['weekly_day'].get_long_term_situation_count(None, None)
            cmds['mhs110.stop']()
            cmds['mhs110.stop']()
            self.assertEqual(save.call_count, 1)
        self.assertIn('ripristinati', outputs[-2])
        self.assertIn('NON ATTIVA', outputs[-1])
        self.assertEqual(mod.TRACER.report()['event_total'], 2)

    def test_actual_rollback_conflict_keeps_warning(self):
        mod, cmds, outputs = load_game_trace()
        classes, _ = native()
        with patch.object(mod, '_classes', return_value=classes),\
             patch.object(mod, '_save', return_value='trace.json'):
            cmds['mhs110.start']()
            classes['weekly_data'].try_start = classmethod(
                lambda cls, *a, **kw: None)
            cmds['mhs110.stop']()
        self.assertIn('ripristino non confermato', outputs[-1])
        self.assertEqual(mod.TRACER.report()['status'], 'RESTORE_CONFLICT')

    def test_only_two_diagnostic_modules_and_no_python37_build_here(self):
        self.assertEqual(set(s.name for s in SOURCES),{
            'mhs110_call_trace_core.py','mhs110_game_trace.py'})
        self.assertEqual(EXPECTED_MAGIC,bytes((66,13,13,10)))
        self.assertTrue(NAME.endswith('.ts4script'))

if __name__=='__main__':
    unittest.main()
