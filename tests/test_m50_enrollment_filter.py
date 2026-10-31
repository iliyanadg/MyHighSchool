"""M50: enrolled students are absent from Iscrivi and native UI caps picks."""
import ast
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tests.test_m48_one_step_enrollment import M48Tests,FakePicker
from tooling.build_m50_filtered_cap import package_bytes
from tooling.build_m49_picker_strategy import package_bytes as m49_package

from mhs_m2_roster import SchoolRoster
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs46_enrollment_transaction import (
    preview_enrollment,confirm_enrollment,EnrollmentTransactionError)


class M50Tests(unittest.TestCase):
    def setUp(self):
        self.fixture=M48Tests()

    def test_same_proven_M49_menu_binary(self):
        self.assertEqual(package_bytes(),m49_package())

    def test_iscrivi_hides_students_from_any_class(self):
        env,calls,actor=self.fixture._env()
        enrolled={'11':1,'12':1,'13':1,'14':2}
        roster=SimpleNamespace(assignments=enrolled,
            class_members=lambda k:[
                sid for sid,cls in enrolled.items() if cls==k])
        env['_ROSTERS']=SimpleNamespace(load=lambda slot:roster)
        env['_teens']=lambda:[
            SimpleNamespace(sim_id=sid) for sid in range(11,21)]
        self.assertTrue(env['open_picker'](1,actor))
        dialog=FakePicker.dialogs[0]
        # 11,12,13 already in class 1, 14 in class 2. None can appear.
        self.assertEqual([r.sim_id for r in dialog.rows],
                         [15,16,17,18,19,20])
        self.assertEqual(dialog.kwargs['max_selectable'],5)
        self.assertIn('Posti liberi: 5/8',dialog.kwargs['text'])

    def test_no_students_duplicate_in_same_or_other_class(self):
        env,calls,actor=self.fixture._env()
        roster=SimpleNamespace(assignments={'11':1,'12':2},
            class_members=lambda k:['11'] if k==1 else ['12'])
        env['_ROSTERS']=SimpleNamespace(load=lambda slot:roster)
        env['_teens']=lambda:[SimpleNamespace(sim_id=11),
                             SimpleNamespace(sim_id=12)]
        self.assertFalse(env['open_picker'](1,actor))
        self.assertEqual(len(FakePicker.dialogs),0)
        self.assertEqual(calls['commit'],[])

    def test_full_class_never_opens_more_enrollment(self):
        env,calls,actor=self.fixture._env()
        enrolled={str(s):1 for s in range(11,19)}
        roster=SimpleNamespace(assignments=enrolled,
            class_members=lambda k:list(enrolled) if k==1 else [])
        env['_ROSTERS']=SimpleNamespace(load=lambda slot:roster)
        self.assertFalse(env['open_picker'](1,actor))
        self.assertEqual(len(FakePicker.dialogs),0)
        self.assertEqual(calls['commit'],[])
        self.assertTrue(calls['notices'])

    def test_ui_uses_remaining_seats_1_to_8(self):
        from tests.test_m49_picker_strategy import _EAUnlimited
        source=(Path(__file__).resolve().parents[1]/
                'src/m48_enrollment/mhs48_single_picker.py').read_text()
        tree=ast.parse(source)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                and n.name=='_max_selectable')
        ns={'UiDialogObjectPicker':SimpleNamespace(
            _MaxSelectableUnlimited=_EAUnlimited)}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),
                     '<M50 picker cap>',mode='exec'),ns)
        for count in range(1,9):
            strategy=ns['_max_selectable'](count)
            self.assertIsInstance(strategy,_EAUnlimited)
            self.assertEqual(strategy.get_max_selectable(),count)
        with self.assertRaises(ValueError):
            ns['_max_selectable'](0)

    def test_preview_strictly_new_and_transfer_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            store=RosterStore(temp)
            settings=SettingsStore(temp)
            slot='11'
            settings.set_active(slot,True)
            store.save(slot,SchoolRoster(slot,{'11':1,'12':2}))
            check=lambda sid:True
            with self.assertRaises(EnrollmentTransactionError):
                preview_enrollment(
                    store,settings,slot,1,('11',),check,only_new=True)
            with self.assertRaises(EnrollmentTransactionError):
                preview_enrollment(
                    store,settings,slot,1,('12',),check,only_new=True)
            plan=preview_enrollment(
                store,settings,slot,1,('13',),check,only_new=True)
            self.assertTrue(plan['only_new'])
            result=confirm_enrollment(store,settings,slot,plan,check)
            self.assertEqual(result['class_size'],2)
            self.assertEqual(store.load(slot).assignments['13'],1)
            # The transfer function still supports moving enrolled Sims,
            # only the new student registration UI is strict.
            move=preview_enrollment(
                store,settings,slot,2,('11',),check)
            self.assertFalse(move['only_new'])
            moved=confirm_enrollment(store,settings,slot,move,check)
            self.assertEqual(moved['moved'],1)

    def test_new_student_becoming_registered_during_picker_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            store=RosterStore(temp)
            settings=SettingsStore(temp)
            settings.set_active('11',True)
            plan=preview_enrollment(
                store,settings,'11',1,('13',),lambda _:True,
                only_new=True)
            store.save('11',SchoolRoster('11',{'13':2}))
            with self.assertRaises(EnrollmentTransactionError):
                confirm_enrollment(store,settings,'11',plan,lambda _:True)
            self.assertEqual(store.load('11').assignments['13'],2)


if __name__=='__main__':
    unittest.main()
