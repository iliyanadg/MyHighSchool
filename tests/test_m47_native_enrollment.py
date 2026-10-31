"""M47: native in-game explicit confirmation and unchanged M45 category graph."""
import ast
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

from tooling.build_m47_native_enrollment import (
    package_bytes,transformed_resources,ENROLL_IDS,PACKAGE,SCRIPT,SCRIPTS,
    TYPE_INTERACTION,CATEGORY_IDS)
from tooling.build_m45_visibility_complete import package_bytes as build_m45
from tooling.simdata_release_gate import resources,inspect_bytes


class FakeDialog(object):
    def __init__(self):
        self.listener=None
        self.shown=False
    def add_listener(self,fn):
        self.listener=fn
    def show_dialog(self):
        self.shown=True
    def respond(self,accepted):
        self.listener(SimpleNamespace(accepted=accepted))


class FakeTunableFactory(object):
    def __init__(self,holder):
        self.holder=holder
    def default(self,*args,**kwargs):
        result=FakeDialog()
        self.holder.append(result)
        return result


class FakeDialogType(object):
    created=[]
    @classmethod
    def TunableFactory(cls):
        return FakeTunableFactory(cls.created)


class M47NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=resources(build_m45())
        cls.after=resources(package_bytes())

    def test_all_menu_category_simdata_localization_unchanged(self):
        self.assertEqual(len(self.before),35)
        self.assertEqual(len(self.after),35)
        modified=[]
        for old,new in zip(self.before,self.after):
            self.assertEqual(old[:3],new[:3])
            if old[3]!=new[3]:
                modified.append(old[2])
        self.assertEqual(set(modified),set(ENROLL_IDS))
        gate=inspect_bytes(package_bytes())
        self.assertEqual(gate['status'],'STATIC_GATE_PASSED')
        self.assertEqual(gate['category_count'],5)
        self.assertEqual(gate['simdata_count'],5)

    def test_enrollment_tunings_match_immediate_interaction_structure(self):
        # Every newly wired action has the same fields as a working
        # M27 immediate action; all original picker IDs, STBL and category kept.
        for index,iid in enumerate(ENROLL_IDS):
            entry=next(x for x in self.after if x[0]==TYPE_INTERACTION and x[2]==iid)
            old=next(x for x in self.before if x[0]==TYPE_INTERACTION and x[2]==iid)
            node=ET.fromstring(entry[3])
            oldnode=ET.fromstring(old[3])
            self.assertEqual(node.get('m'),'mhs39_visibility_ui')
            self.assertEqual(node.get('c'),'MHS47EnrollClass{}'.format(index+1))
            self.assertEqual(node.get('n'),oldnode.get('n'))
            self.assertEqual(node.get('s'),oldnode.get('s'))
            self.assertEqual(node.find('./T[@n="display_name"]').text,
                             oldnode.find('./T[@n="display_name"]').text)
            self.assertEqual(node.find('./T[@n="category"]').text,
                             str(CATEGORY_IDS[index]))
            self.assertEqual(node.find('./E[@n="target_type"]').text,'OBJECT')
            self.assertIsNone(node.find('./U[@n="sim_picker"]'))

    def test_native_ui_modules_bundle_inventory(self):
        self.assertEqual(len(SCRIPTS),17)
        self.assertEqual(len({p.name for p in SCRIPTS}),17)
        self.assertIn('mhs46_enrollment_transaction.py',{p.name for p in SCRIPTS})
        self.assertIn('mhs47_enrollment_ui.py',{p.name for p in SCRIPTS})

    def _dialog_function(self):
        source=(Path(__file__).resolve().parents[1]/
                'src/m47_enrollment/mhs47_enrollment_ui.py').read_text()
        tree=ast.parse(source)
        fn=next(n for n in tree.body
                if isinstance(n,ast.FunctionDef) and n.name=='_confirmation_dialog')
        env={
            'UiDialogOkCancel':FakeDialogType,
            '_localized':lambda x:lambda **kwargs:x,
            'confirm_enrollment':lambda *args:None,
            '_ROSTERS':object(),
            '_SETTINGS':object(),
            'current_slot':lambda:'11',
            'teenager_checker':lambda x:True,
            '_notice':lambda *args:None,
            '_event':lambda *args:None,
        }
        compiled=compile(ast.Module(body=[fn],type_ignores=[]),
                         filename='<M47 actual dialog function>',mode='exec')
        exec(compiled,env)
        return env

    def test_cancel_never_writes_and_duplicate_callback_cannot_double_write(self):
        FakeDialogType.created=[]
        env=self._dialog_function()
        writes=[]
        env['confirm_enrollment']=lambda *args:writes.append(args) or {
            'changed':1,'class_size':1}
        plan={'slot':'11','class':1,'selected':('111',),
              'selected_count':1,'changed':1,'moved':0,
              'already_in_class':0,'class_size':1,'remaining':7,'snapshot':'x'}
        env['_confirmation_dialog'](object(),1,plan)
        self.assertEqual(len(FakeDialogType.created),1)
        dialog=FakeDialogType.created[0]
        self.assertTrue(dialog.shown)
        dialog.respond(False)
        dialog.respond(True)
        self.assertEqual(writes,[])
        FakeDialogType.created=[]
        env['_confirmation_dialog'](object(),1,plan)
        confirmed=FakeDialogType.created[0]
        confirmed.respond(True)
        confirmed.respond(True)
        self.assertEqual(len(writes),1)

    def test_engine_failure_does_not_report_success(self):
        FakeDialogType.created=[]
        env=self._dialog_function()
        messages=[]
        def fail(*args):
            raise RuntimeError('Roster changed')
        env['confirm_enrollment']=fail
        env['_notice']=lambda actor,title,msg:messages.append((title,msg))
        plan={'slot':'11','class':1,'selected':('111',),
              'selected_count':1,'changed':1,'moved':0,
              'already_in_class':0,'class_size':1,'remaining':7,'snapshot':'x'}
        env['_confirmation_dialog'](object(),1,plan)
        FakeDialogType.created[-1].respond(True)
        self.assertEqual(len(messages),1)
        self.assertIn('non salvata',messages[0][0])


if __name__=='__main__':
    unittest.main()
