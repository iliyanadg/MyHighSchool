"""M48 checkmark is the ONLY confirmation; X never writes student JSON."""
import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

from tooling.build_m48_single_checkmark import (
    package_bytes,SCRIPTS,ENROLL_IDS,CATEGORY_IDS,TYPE_INTERACTION)
from tooling.build_m45_visibility_complete import package_bytes as build_m45
from tooling.simdata_release_gate import resources,inspect_bytes


class FakeDialog(object):
    def __init__(self):
        self.callback=None
        self.shown=False
        self.rows=[]
    def add_row(self,row):
        self.rows.append(row)
    def add_listener(self,callback):
        self.callback=callback
    def show_dialog(self):
        self.shown=True
    def reply(self,accepted,selected=()):
        self.callback(SimpleNamespace(
            accepted=accepted,
            get_result_tags=lambda:tuple(selected)))


class FakeFactory(object):
    def __init__(self,out):
        self.out=out
    def default(self,*args,**kwargs):
        result=FakeDialog()
        result.kwargs=kwargs
        self.out.append(result)
        return result


class FakePicker(object):
    dialogs=[]
    @classmethod
    def TunableFactory(cls):
        return FakeFactory(cls.dialogs)


class M48Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=resources(build_m45())
        cls.after=resources(package_bytes())

    def test_only_three_interactions_changed(self):
        self.assertEqual(len(self.after),35)
        self.assertEqual([x[:3] for x in self.before],
                         [x[:3] for x in self.after])
        changed={a[2] for a,b in zip(self.before,self.after) if a[3]!=b[3]}
        self.assertEqual(changed,set(ENROLL_IDS))
        for i,iid in enumerate(ENROLL_IDS):
            row=next(r for r in self.after if r[0]==TYPE_INTERACTION and r[2]==iid)
            xml=ET.fromstring(row[3])
            self.assertEqual(xml.get('m'),'mhs48_single_picker')
            self.assertEqual(xml.get('c'),'MHS48EnrollClass{}'.format(i+1))
            self.assertEqual(xml.find('./T[@n="category"]').text,
                             str(CATEGORY_IDS[i]))
        check=inspect_bytes(package_bytes())
        self.assertEqual(check['status'],'STATIC_GATE_PASSED')
        self.assertEqual(check['category_count'],5)
        self.assertEqual(check['simdata_count'],5)

    def test_scripts_have_game_and_transaction_modules(self):
        names={p.name for p in SCRIPTS}
        self.assertEqual(len(names),17)
        self.assertIn('mhs48_single_picker.py',names)
        self.assertIn('mhs46_enrollment_transaction.py',names)
        self.assertNotIn('mhs47_enrollment_ui.py',names)

    def _env(self):
        text=(Path(__file__).resolve().parents[1]/
              'src/m48_enrollment/mhs48_single_picker.py').read_text()
        tree=ast.parse(text)
        fn=next(n for n in tree.body
                if isinstance(n,ast.FunctionDef) and n.name=='open_picker')
        filter_fn=next(n for n in tree.body
                if isinstance(n,ast.FunctionDef) and
                n.name=='_unassigned_candidates')
        FakePicker.dialogs=[]
        calls={'preview':[],'commit':[],'notices':[],'events':[]}
        def preview(*args,**kwargs):
            calls['preview'].append(args)
            return {'slot':'11','class':args[3],'selected':args[4],
                    'changed':1,'class_size':1}
        def commit(*args):
            calls['commit'].append(args)
            return {'changed':1,'class_size':1}
        def row(sim_id,selected,tag):
            return SimpleNamespace(sim_id=sim_id,tag=tag)
        class Settings(object):
            def require_management(self,slot,klass):
                return True
        env={
            'current_slot':lambda:'11',
            '_SETTINGS':Settings(),
            '_ROSTERS':SimpleNamespace(load=lambda slot:SimpleNamespace(
                assignments={},class_members=lambda klass:[])),
            '_teens':lambda:[SimpleNamespace(sim_id=11),
                             SimpleNamespace(sim_id=12)],
            'canonical_sim_id':lambda sid:str(int(sid)),
            'UiSimPicker':FakePicker,
            'SimPickerRow':row,
            '_max_selectable':lambda limit:limit,
            '_text':lambda txt:txt,
            '_record':lambda *args:calls['events'].append(args),
            '_notify':lambda *args:calls['notices'].append(args),
            'preview_enrollment':preview,
            'confirm_enrollment':commit,
            'teenager_checker':lambda sid:True,
        }
        exec(compile(ast.Module(body=[filter_fn,fn],type_ignores=[]),
                     '<M48 real picker>',mode='exec'),env)
        actor=SimpleNamespace(sim=object())
        return env,calls,actor

    def test_x_cancel_does_not_preview_or_write(self):
        env,calls,actor=self._env()
        self.assertTrue(env['open_picker'](1,actor))
        dialog=FakePicker.dialogs[0]
        self.assertTrue(dialog.shown)
        self.assertEqual(len(dialog.rows),2)
        self.assertEqual(dialog.kwargs['max_selectable'],8)
        dialog.reply(False,(11,12))
        dialog.reply(True,(11,12))
        self.assertEqual(calls['preview'],[])
        self.assertEqual(calls['commit'],[])

    def test_checkmark_saves_once_no_second_dialog(self):
        env,calls,actor=self._env()
        env['open_picker'](2,actor)
        dialog=FakePicker.dialogs[0]
        dialog.reply(True,(11,12))
        dialog.reply(True,(11,12))
        self.assertEqual(len(FakePicker.dialogs),1)
        self.assertEqual(len(calls['preview']),1)
        self.assertEqual(len(calls['commit']),1)
        self.assertEqual(calls['commit'][0][3]['selected'],('11','12'))

    def test_invalid_or_empty_selection_never_writes(self):
        env,calls,actor=self._env()
        env['open_picker'](1,actor)
        FakePicker.dialogs[0].reply(True,())
        self.assertEqual(calls['commit'],[])
        self.assertTrue(calls['notices'])
        env,calls,actor=self._env()
        env['open_picker'](1,actor)
        FakePicker.dialogs[0].reply(True,(11,11))
        self.assertEqual(calls['commit'],[])

    def test_failed_confirmation_does_not_announce_success(self):
        env,calls,actor=self._env()
        def reject(*args):
            raise ValueError('Classe piena')
        env['confirm_enrollment']=reject
        env['open_picker'](3,actor)
        FakePicker.dialogs[0].reply(True,(11,))
        self.assertEqual(len(calls['notices']),1)
        self.assertIn('Nessuna modifica',calls['notices'][0][1])


if __name__=='__main__':
    unittest.main()
