"""M24 step: no writes to real game, only mock-based tests and DBPF audit."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm24_probe'))


class StubImmediate(object):
    def _run_interaction_gen(self, timeline):
        return 'ORIGINAL_NOTIFICATION'


class StubPicked(object):
    PickedSim = object()


class StubCommands(object):
    class CommandType:
        Live = 1
    @staticmethod
    def Command(name, command_type=None):
        return lambda fn: fn
    @staticmethod
    def CheatOutput(connection=None):
        return lambda msg: None


def import_probe():
    import importlib
    interactions = types.ModuleType('interactions')
    interactions.ParticipantType = StubPicked
    interactions.__path__ = []
    base = types.ModuleType('interactions.base')
    base.__path__ = []
    immediate = types.ModuleType('interactions.base.immediate_interaction')
    immediate.ImmediateSuperInteraction = StubImmediate
    sims4 = types.ModuleType('sims4')
    sims4.__path__ = []
    commands = types.ModuleType('sims4.commands')
    commands.Command = StubCommands.Command
    commands.CommandType = StubCommands.CommandType
    commands.CheatOutput = StubCommands.CheatOutput
    sims4.commands = commands
    with patch.dict(sys.modules, {'interactions': interactions, 'interactions.base': base,
                                  'interactions.base.immediate_interaction': immediate,
                                  'sims4': sims4, 'sims4.commands': commands}):
        sys.modules.pop('mhs24_diagnostic', None)
        module = importlib.import_module('mhs24_diagnostic')
    return module


class Sim(object):
    def __init__(self, sid):
        self.sim_info = types.SimpleNamespace(sim_id=sid)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.mod = import_probe()
        self.mod._SESSION.clear()

    def test_one_picked_id(self):
        x = self.mod.MHS24ProbeConfirmClass1()
        x.get_participants = lambda which: (Sim(1),)
        self.assertEqual(x._run_interaction_gen(None), 'ORIGINAL_NOTIFICATION')
        self.assertEqual(self.mod._SESSION[-1]['ids'], ('1',))

    def test_three_picked_ids_in_single_callback(self):
        x = self.mod.MHS24ProbeConfirmClass2()
        x.get_participants = lambda which: (Sim(1), Sim(2), Sim(3))
        x._run_interaction_gen(None)
        self.assertEqual(self.mod._SESSION[0]['class'], 2)
        self.assertEqual(len(self.mod._SESSION[0]['ids']), 3)

    def test_three_separate_callbacks_are_recorded_separately(self):
        for i in (1,2,3):
            x = self.mod.MHS24ProbeConfirmClass1()
            x.get_participants = lambda which, sid=i: (Sim(sid),)
            x._run_interaction_gen(None)
        self.assertEqual(len(self.mod._SESSION), 3)

    def test_missing_pickedsim_does_not_stop_notification(self):
        x = self.mod.MHS24ProbeConfirmClass1()
        x.get_participants = lambda which: None
        self.assertEqual(x._run_interaction_gen(None), 'ORIGINAL_NOTIFICATION')
        self.assertIn('PickedSim NONE', self.mod._SESSION[-1]['error'])

    def test_exception_does_not_stop_original_confirmation(self):
        x = self.mod.MHS24ProbeConfirmClass1()
        def bad(which): raise RuntimeError('unknown')
        x.get_participants = bad
        self.assertEqual(x._run_interaction_gen(None), 'ORIGINAL_NOTIFICATION')
        self.assertIn('RuntimeError', self.mod._SESSION[-1]['error'])

    def test_ring_limit(self):
        for i in range(100):
            x = self.mod.MHS24ProbeConfirmClass1()
            x.get_participants = lambda which, sid=i+1: (Sim(sid),)
            x._run_interaction_gen(None)
        self.assertEqual(len(self.mod._SESSION), 32)

    def test_no_disk_writes_or_enrollment_calls(self):
        source = (ROOT/'src'/'m24_probe'/'mhs24_diagnostic.py').read_text()
        self.assertNotIn('RosterStore', source)
        self.assertNotIn('enroll_selection', source)
        self.assertNotIn('open(', source)
        self.assertNotIn('os.', source)


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tooling.build_m24_probe import build_package, verify_only_two_tuning_changes
        from tooling.simdata_release_gate import resources
        cls.package = build_package()
        cls.resources = resources(cls.package)
        cls.verify = verify_only_two_tuning_changes()

    def test_nine_resources_and_original_category(self):
        self.assertTrue(self.verify)
        self.assertEqual(len(self.resources), 9)

    def test_two_confirmations_target_script_module(self):
        import xml.etree.ElementTree as ET
        from tooling.build_m24_probe import REPLACEMENTS, TYPE_INTERACTION
        selected = [(iid, ET.fromstring(content)) for typ, group, iid, content in self.resources
                    if typ == TYPE_INTERACTION and iid in REPLACEMENTS]
        self.assertEqual(len(selected), 2)
        for iid, root in selected:
            self.assertEqual(root.get('c'), REPLACEMENTS[iid])
            self.assertEqual(root.get('m'), 'mhs24_diagnostic')

    def test_binary_script_compile_requires_python37(self):
        import sys
        from tooling.build_m24_probe import compile_script, DiagnosticBuildError
        if sys.version_info[:2] != (3,7):
            with self.assertRaises(DiagnosticBuildError):
                compile_script(ROOT / '_not_generated.ts4script')


if __name__ == '__main__': unittest.main()
