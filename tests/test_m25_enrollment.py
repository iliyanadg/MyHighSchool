"""M25 is a staged commit test, not a production save solution."""
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m25_enrollment'))
sys.path.insert(0,str(ROOT/'src'/'m2_registry'))


class Base(object):
    def _run_interaction_gen(self,timeline):
        yield 'original-notification-activated'
        return 'ok'


class FakeCommands(object):
    class CommandType:
        Live=1

    @staticmethod
    def Command(name,command_type=None):
        return lambda fn: fn

    @staticmethod
    def CheatOutput(_connection=None):
        return lambda s: None


def load_module(store):
    interactions=types.ModuleType('interactions')
    interactions.__path__=[]
    interactions.ParticipantType=types.SimpleNamespace(PickedSim='PickedSim')
    parent=types.ModuleType('interactions.base')
    parent.__path__=[]
    immediate=types.ModuleType('interactions.base.immediate_interaction')
    immediate.ImmediateSuperInteraction=Base
    sims4=types.ModuleType('sims4')
    sims4.__path__=[]
    commands=types.ModuleType('sims4.commands')
    commands.Command=FakeCommands.Command
    commands.CommandType=FakeCommands.CommandType
    commands.CheatOutput=FakeCommands.CheatOutput
    sims4.commands=commands
    mocks={'interactions':interactions,'interactions.base':parent,
           'interactions.base.immediate_interaction':immediate,
           'sims4':sims4,'sims4.commands':commands}
    with patch.dict(sys.modules,mocks):
        sys.modules.pop('mhs25_confirmation',None)
        module=importlib.import_module('mhs25_confirmation')
        module._STORE=store
        return module


class Sim(object):
    def __init__(self,sid):
        self.sim_info=types.SimpleNamespace(sim_id=sid)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        from mhs_m2_store import RosterStore
        self.store=RosterStore(str(Path(self.temp.name)/'M25'))
        self.mod=load_module(self.store)
        self.oldslot=self.mod.current_slot
        self.oldteen=self.mod.teenager_checker
        self.mod.current_slot=lambda:'11'
        self.mod.teenager_checker=lambda sid:int(sid)<100
        self.addCleanup(lambda:setattr(self.mod,'current_slot',self.oldslot))
        self.addCleanup(lambda:setattr(self.mod,'teenager_checker',self.oldteen))

    def do_picker(self, klass, ids):
        cls=self.mod.MHS25StageConfirmClass1 if klass==1 else self.mod.MHS25StageConfirmClass2
        interaction=cls()
        interaction.get_participants=lambda which:tuple(Sim(n) for n in ids)
        return list(interaction._run_interaction_gen(None))

    def test_stage_preserves_original_generator(self):
        self.assertEqual(self.do_picker(1,[1]),['original-notification-activated'])
        self.assertEqual(self.mod._PENDING['picked'],('1',))
        self.assertFalse(Path(self.store.path(11)).exists())

    def test_confirmation_does_not_write_until_explicit_commit(self):
        self.do_picker(1,[1,2,3])
        self.mod.mhs25_preview()
        self.assertFalse(Path(self.store.path(11)).exists())
        self.mod.mhs25_commit('no')
        self.assertFalse(Path(self.store.path(11)).exists())
        self.mod.mhs25_commit('conferma')
        self.assertEqual(self.store.load(11).class_members(1),['1','2','3'])

    def test_eight_selected_in_single_event(self):
        self.do_picker(2,list(range(1,9)))
        self.mod.mhs25_commit('conferma')
        self.assertEqual(len(self.store.load(11).class_members(2)),8)

    def test_wrong_slot_clears_pending_without_write(self):
        self.do_picker(1,[1])
        self.mod.current_slot=lambda:'12'
        self.mod.mhs25_commit('conferma')
        self.assertIsNone(self.mod._PENDING)
        self.assertFalse(Path(self.store.path(11)).exists())

    def test_invalid_teen_blocks_all(self):
        self.do_picker(1,[1,200])
        self.mod.mhs25_commit('conferma')
        self.assertFalse(Path(self.store.path(11)).exists())

    def test_unidentified_slot_blocks_staging(self):
        self.mod.current_slot=lambda:(_ for _ in ()).throw(Exception('no slot'))
        self.do_picker(1,[1])
        self.assertIsNone(self.mod._PENDING)
        self.assertFalse(Path(self.store.path(11)).exists())

    def test_new_selection_replaces_old_pending(self):
        self.do_picker(1,[1,2])
        self.do_picker(2,[3])
        self.mod.mhs25_commit('conferma')
        self.assertEqual(self.store.load(11).class_members(1),[])
        self.assertEqual(self.store.load(11).class_members(2),['3'])

    def test_class_transfer_no_duplicate(self):
        self.do_picker(1,[3])
        self.mod.mhs25_commit('conferma')
        self.do_picker(2,[3])
        self.mod.mhs25_commit('conferma')
        self.assertEqual(self.store.load(11).class_members(1),[])
        self.assertEqual(self.store.load(11).class_members(2),['3'])

    def test_discard_does_not_write(self):
        self.do_picker(1,[4])
        self.mod.mhs25_discard()
        self.mod.mhs25_commit('conferma')
        self.assertFalse(Path(self.store.path(11)).exists())


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tooling.build_m25_enrollment import build_package
        from tooling.simdata_release_gate import resources
        cls.entries=resources(build_package())

    def test_binary_resources(self):
        self.assertEqual(len(self.entries),9)

    def test_modified_menu_text_is_truthful(self):
        from tooling.m1_links_and_strings import parse_stbl
        rows=[parse_stbl(payload) for typ,g,i,payload in self.entries
              if typ==0x220557DA]
        self.assertEqual(len(rows),2)
        for row in rows:
            self.assertNotIn('Nessuna iscrizione verra salvata.',row[0x7FE4CEBC])
            self.assertIn('mhs25.preview',row[0x7FE4CEBC])

    def test_confirmations_bind_to_script(self):
        import xml.etree.ElementTree as ET
        from tooling.build_m25_enrollment import CONFIRMATIONS
        for typ,g,i,payload in self.entries:
            if i in CONFIRMATIONS:
                elem=ET.fromstring(payload)
                self.assertEqual(elem.get('m'),'mhs25_confirmation')
                self.assertEqual(elem.get('c'),CONFIRMATIONS[i])

    def test_pickers_not_modified_and_injector_highbit(self):
        from tooling.build_m1_offline import build_m1_bytes
        from tooling.simdata_release_gate import resources
        originals=resources(build_m1_bytes())
        for before,after in zip(originals,self.entries):
            if before[0] in (0x03E9D964,0x545AC67A,0x7DF2169C):
                self.assertEqual(before,after)


if __name__=='__main__':
    unittest.main()
