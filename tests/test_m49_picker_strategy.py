"""Regression: M48's real Mac ImmutableSlots.get_max_selectable exception."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

from tooling.build_m49_picker_strategy import package_bytes,SCRIPTS
from tooling.build_m48_single_checkmark import package_bytes as build_m48
from tests.test_m48_one_step_enrollment import M48Tests,FakePicker


class _EAUnlimited(object):
    def get_max_selectable(self,*args,**kwargs):
        return 999


class M49Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=(Path(__file__).resolve().parents[1]/
                  'src/m48_enrollment/mhs48_single_picker.py')

    def test_package_is_exactly_M48_binary_no_menu_regressions(self):
        self.assertEqual(package_bytes(),build_m48())
        self.assertEqual(len(SCRIPTS),17)

    def test_native_max_selectable_has_required_game_method(self):
        source=self.path.read_text()
        self.assertNotIn('make_immutable_slots_class',source)
        tree=ast.parse(source)
        fn=next(n for n in tree.body
                if isinstance(n,ast.FunctionDef) and n.name=='_max_selectable')
        ea=SimpleNamespace(_MaxSelectableUnlimited=_EAUnlimited)
        namespace={'UiDialogObjectPicker':ea}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),
                     '<M49 max selection>',mode='exec'),namespace)
        strategy=namespace['_max_selectable'](8)
        self.assertTrue(callable(strategy.get_max_selectable))
        self.assertEqual(strategy.get_max_selectable(),8)
        with self.assertRaises(ValueError):
            namespace['_max_selectable'](9)

    def test_exact_game_error_is_blocked_before_show(self):
        source=self.path.read_text()
        tree=ast.parse(source)
        fn=next(n for n in tree.body
                if isinstance(n,ast.FunctionDef) and n.name=='_max_selectable')
        namespace={'UiDialogObjectPicker':SimpleNamespace(
            _MaxSelectableUnlimited=lambda:SimpleNamespace())}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),
                     '<M49 invalid runtime>',mode='exec'),namespace)
        with self.assertRaisesRegex(TypeError,'selezione EA'):
            namespace['_max_selectable'](8)

    def test_over_eight_selected_never_writes(self):
        # Validate the full real picker callback, not only a mock of the
        # transaction service; UI might allow many choices with EA's
        # Unlimited strategy and our callback must reject all >8.
        fixture=M48Tests()
        env,calls,actor=fixture._env()
        env['_teens']=lambda:[
            SimpleNamespace(sim_id=100+i) for i in range(9)]
        self.assertTrue(env['open_picker'](1,actor))
        self.assertEqual(len(FakePicker.dialogs[0].rows),9)
        FakePicker.dialogs[0].reply(
            True,tuple(100+i for i in range(9)))
        self.assertEqual(calls['commit'],[])
        self.assertEqual(calls['preview'],[])
        self.assertTrue(calls['notices'])


if __name__=='__main__':
    unittest.main()
