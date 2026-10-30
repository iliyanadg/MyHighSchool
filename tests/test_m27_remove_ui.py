"""Source-only unit tests for class-filtered native remove picker."""
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m27_remove_ui'))
sys.path.insert(0,str(ROOT/'src'/'m26_withdrawal'))
sys.path.insert(0,str(ROOT/'src'/'m2_registry'))


class Base(object):
    def _run_interaction_gen(self,timeline):
        yield 'base-event'


class Commands(object):
    class CommandType:
        Live=1
    @staticmethod
    def Command(name,command_type=None):
        return lambda f:f
    @staticmethod
    def CheatOutput(c=None):
        return lambda message:None


class FakeDialog(object):
    def __init__(self):
        self.accepted=False
        self.rows=[]
        self.listener=None
        self.tags=()
        self.shown=False
    def add_row(self,row):
        self.rows.append(row)
    def add_listener(self,callback):
        self.listener=callback
    def show_dialog(self,**kwargs):
        self.shown=True
    def get_result_tags(self):
        return self.tags
    def accept(self,tags):
        self.accepted=True
        self.tags=tags
        self.listener(self)


class FakeFactory(object):
    dialog=None
    def __call__(self):
        return self
    def default(self,*args,**kwargs):
        FakeFactory.dialog=FakeDialog()
        return FakeFactory.dialog


class Row(object):
    def __init__(self,sid,selected,tag):
        self.sid=sid
        self.tag=tag


def load_ui():
    interactions=types.ModuleType('interactions')
    interactions.__path__=[]
    base=types.ModuleType('interactions.base')
    base.__path__=[]
    immediate=types.ModuleType('interactions.base.immediate_interaction')
    immediate.ImmediateSuperInteraction=Base
    services=types.ModuleType('services')
    services.sim_info_manager=lambda:None
    services.client_manager=lambda:None
    sims4=types.ModuleType('sims4')
    sims4.__path__=[]
    commands=types.ModuleType('sims4.commands')
    commands.Command=Commands.Command
    commands.CommandType=Commands.CommandType
    commands.CheatOutput=Commands.CheatOutput
    sims4.commands=commands
    with patch.dict(sys.modules,{
        'interactions':interactions,'interactions.base':base,
        'interactions.base.immediate_interaction':immediate,
        'services':services,'sims4':sims4,'sims4.commands':commands,
    }):
        sys.modules.pop('mhs27_remove_ui',None)
        module=importlib.import_module('mhs27_remove_ui')
    return module


class UiTests(unittest.TestCase):
    def setUp(self):
        from mhs_m2_store import RosterStore
        from mhs_m2_roster import SchoolRoster
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=RosterStore(str(Path(self.tmp.name)/'M25_TEST'))
        self.store.save('11',SchoolRoster('11',{'101':1,'102':1,'201':2,'202':2}))
        self.mod=load_ui()
        from mhs26_remove import RemovalService
        self.mod._SERVICE=RemovalService(self.store)
        self.mod.current_slot=lambda:'11'
        self.all={str(i):types.SimpleNamespace(sim_id=i)
                  for i in (101,102,201,202,999)}
        self.mod._lookup_sim_info=lambda sid:self.all.get(sid)
        self.mod._dialog_factory=lambda klass,infos,actor:self._new_dialog(infos)
        self.dialog=None

    def _new_dialog(self,infos):
        self.dialog=FakeDialog()
        for info in infos:
            self.dialog.add_row(Row(info.sim_id,False,info.sim_id))
        return self.dialog

    def click(self,klass):
        obj=self.mod.MHS27RemoveClass1() if klass==1 else self.mod.MHS27RemoveClass2()
        obj.sim=object()
        self.assertEqual(list(obj._run_interaction_gen(None)),['base-event'])
        return self.dialog

    def test_native_picker_does_not_pass_tuple_icon_override(self):
        # Regression for actual macOS game error:
        # AttributeError: 'tuple' object has no attribute 'icon_resource'
        localization=types.ModuleType('sims4.localization')
        localization.LocalizationHelperTuning=types.SimpleNamespace(
            get_raw_text=lambda text:text)
        collections=types.ModuleType('sims4.collections')
        collections.make_immutable_slots_class=lambda fields:lambda values:values
        ui=types.ModuleType('ui')
        ui.__path__=[]
        picker=types.ModuleType('ui.ui_dialog_picker')

        class GuardDialog(FakeDialog):
            def show_dialog(self,**kwargs):
                if isinstance(kwargs.get('icon_override'),tuple):
                    raise AttributeError("'tuple' object has no attribute 'icon_resource'")
                return super().show_dialog(**kwargs)

        class NativeFactory(object):
            dialog=None
            def default(self,*args,**kwargs):
                self.dialog=GuardDialog()
                return self.dialog

        factory=NativeFactory()
        picker.UiSimPicker=types.SimpleNamespace(
            TunableFactory=lambda:types.SimpleNamespace(default=factory.default))
        picker.SimPickerRow=Row
        self.mod._dialog_factory=load_ui()._dialog_factory
        with patch.dict(sys.modules,{
            'sims4.localization':localization,
            'sims4.collections':collections,
            'ui':ui,
            'ui.ui_dialog_picker':picker,
        }):
            self.click(1)
        self.assertIsNotNone(factory.dialog)
        self.assertTrue(factory.dialog.shown)
        self.assertEqual(self.mod._EVENTS[-1][0],'OPEN')

    def test_class1_picker_has_only_class1_members(self):
        self.click(1)
        self.assertEqual({x.tag for x in self.dialog.rows},{101,102})

    def test_class2_picker_has_only_class2_members(self):
        self.click(2)
        self.assertEqual({x.tag for x in self.dialog.rows},{201,202})

    def test_confirm_stages_but_never_writes(self):
        d=self.click(1)
        original=Path(self.store.path(11)).read_bytes()
        d.accept((101,))
        self.assertEqual(self.mod._PENDING['removed'],1)
        self.assertEqual(original,Path(self.store.path(11)).read_bytes())

    def test_commit_only_after_console_confirmation(self):
        self.click(2).accept((201,202))
        self.mod.mhs27_removecommit('no')
        self.assertEqual(self.store.load('11').class_members(2),['201','202'])
        self.mod.mhs27_removecommit('conferma')
        self.assertEqual(self.store.load('11').class_members(1),['101','102'])
        self.assertEqual(self.store.load('11').class_members(2),[])

    def test_wrong_class_result_rejected(self):
        self.click(1).accept((201,))
        self.assertIsNone(self.mod._PENDING)
        self.assertEqual(self.store.load('11').class_members(1),['101','102'])

    def test_cancel_does_not_write(self):
        d=self.click(2)
        d.accepted=False
        d.listener(d)
        self.assertIsNone(self.mod._PENDING)
        self.assertEqual(self.store.load('11').class_members(2),['201','202'])

    def test_roster_changed_while_picker_open_blocks(self):
        d=self.click(1)
        from mhs_m2_roster import SchoolRoster
        self.store.save('11',SchoolRoster('11',{'101':1,'102':1,'103':1,'201':2}))
        d.accept((101,))
        self.assertIsNone(self.mod._PENDING)

    def test_slot_changed_before_confirmation_blocks(self):
        d=self.click(1)
        self.mod.current_slot=lambda:'12'
        d.accept((101,))
        self.assertIsNone(self.mod._PENDING)

    def test_list_preserved_after_not_confirming(self):
        self.click(1).accept((101,))
        self.mod.mhs27_removecancel()
        self.assertEqual(self.store.load('11').class_members(1),['101','102'])

    def test_not_allowed_without_enrollment(self):
        from mhs_m2_roster import SchoolRoster
        self.store.save('11',SchoolRoster('11',{'201':2}))
        self.click(1)
        self.assertIsNone(self.dialog)
        self.assertIsNone(self.mod._PENDING)


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tooling.build_m27_removal import package_bytes
        from tooling.simdata_release_gate import resources
        cls.pack=package_bytes()
        cls.entries=resources(cls.pack)

    def test_inventory_11_and_original_confirmations(self):
        self.assertEqual(len(self.entries),11)
        from tooling.build_m25_enrollment import build_package
        from tooling.simdata_release_gate import resources
        originals=resources(build_package())
        for old,new in zip(originals,self.entries):
            if old[0]==0xE882D22F:
                self.assertEqual(old,new)

    def test_two_remove_interactions_in_own_category(self):
        from tooling.build_m27_removal import IDS, BASE_CATEGORY
        import xml.etree.ElementTree as ET
        for id in IDS:
            root=next(ET.fromstring(raw) for ty,g,i,raw in self.entries if i==id)
            self.assertEqual(root.find('./T[@n="category"]').text,str(BASE_CATEGORY))
            self.assertEqual(root.attrib['m'],'mhs27_remove_ui')

    def test_injector_includes_new_entries(self):
        from tooling.build_m27_removal import IDS
        import xml.etree.ElementTree as ET
        injector=next(ET.fromstring(raw) for ty,g,i,raw in self.entries if ty==0x7DF2169C)
        registered={int(x.text) for x in injector.findall('.//L[@n="_super_affordances"]/T')}
        self.assertTrue(set(IDS).issubset(registered))

    def test_two_languages_have_new_menu_items(self):
        from tooling.m1_links_and_strings import parse_stbl
        from tooling.build_m27_removal import STBL_KEY
        for ty,g,i,blob in self.entries:
            if ty==0x220557DA:
                keys=parse_stbl(blob)
                self.assertEqual(len(keys),11)
                self.assertTrue(all(key in keys for key in STBL_KEY))


if __name__=='__main__':
    unittest.main()
