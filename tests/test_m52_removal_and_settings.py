"""M52: class-3 still occupied -> block with a notification; removal works."""
import ast
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tooling.build_m51_bulk_transfer import package_bytes as m51_package
from tooling.build_m52_removal_and_settings import package_bytes as m52_package


class M52Tests(unittest.TestCase):
    def test_menu_binary_unchanged(self):
        self.assertEqual(m51_package(),m52_package())

    def _load_apply(self):
        source=(Path(__file__).resolve().parents[1]/
                'src/m34_settings/mhs34_settings_ui.py').read_text()
        tree=ast.parse(source)
        fn=next(n for n in tree.body
                if isinstance(n,ast.FunctionDef) and n.name=='_apply')
        calls=[]
        class Config(object):
            def set_class_count(self,slot,count,roster):
                if count==2 and roster.class_members(3):
                    raise ValueError('Classe 3 contiene {} studenti: spostali'.format(
                        len(roster.class_members(3))))
                return SimpleNamespace(active=True,class_count=count)
            def set_active(self,slot,active):
                return SimpleNamespace(active=active,class_count=3)
        env={
            '_CONFIG':Config(),'current_slot':lambda:'11',
            '_ROSTERS':SimpleNamespace(load=lambda slot:SimpleNamespace(
                class_members=lambda klass:['101','102','103','104'] if klass==3 else [])),
            'SettingsError':ValueError,
            '_event':lambda value:calls.append(('event',value)),
            '_settings_notice':lambda title,msg:calls.append(('notice',title,msg)),
        }
        exec(compile(ast.Module(body=[fn],type_ignores=[]),
                     '<M52 actual settings apply>',mode='exec'),env)
        return env,calls

    def test_occupied_class_three_is_not_disabled_silently(self):
        env,calls=self._load_apply()
        self.assertFalse(env['_apply']('two'))
        alerts=[c for c in calls if c[0]=='notice']
        self.assertEqual(len(alerts),1)
        self.assertIn('Classe 3',alerts[0][1])
        self.assertIn('4 studenti',alerts[0][2])

    def test_disable_school_success(self):
        env,calls=self._load_apply()
        self.assertTrue(env['_apply']('disable'))
        self.assertFalse(any(c[0]=='notice' for c in calls))

    def test_no_second_confirmation_dialog_for_removal(self):
        source=(Path(__file__).resolve().parents[1]/
                'src/m27_remove_ui/mhs27_remove_ui.py').read_text()
        root=ast.parse(source)
        fn=next(n for n in root.body if isinstance(n,ast.FunctionDef)
                and n.name=='open_remove_picker')
        impl=source[source.index('def open_remove_picker('):
                    source.index('\nclass MHS27RemoveClass1')]
        self.assertIn('_SERVICE.commit(preview,current_slot())',impl)
        self.assertIn('result_dialog.get_result_tags()',impl)
        self.assertNotIn('UiDialogOkCancel',impl)
        self.assertIn('len(chosen)<=len(choices)',impl)


if __name__=='__main__':
    unittest.main()
