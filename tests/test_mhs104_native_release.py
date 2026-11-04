"""M104 Mac release excludes the old failed guest invitation architecture."""
import unittest
from tooling.build_mhs94_probe import script_sources as base_scripts
from tooling.build_mhs104_native_filter import script_sources
from pathlib import Path

class M104ReleaseTests(unittest.TestCase):
    def test_m94_originals_preserved_except_loader(self):
        old={p.name:p for p in base_scripts()}
        new={p.name:p for p in script_sources()}
        self.assertEqual(len(old),33)
        self.assertEqual(len(new),35)
        for name,p in old.items():
            if name=='mhs55_attendance_ui.py':
                self.assertEqual(new[name].parent.name,'m104_native')
            else:
                self.assertEqual(new[name],p)
        for name in ('mhs89_precreate_hook.py','mhs101_original_slot_runtime.py',
                     'mhs102_bouncer_observer.py'):
            self.assertNotIn(name,new)

    def test_no_new_invite_only_native_filter_one_call(self):
        new={p.name:p for p in script_sources()}
        src=new['mhs104_native_school_filter.py'].read_text()
        self.assertIn("Command('mhs104.arm'",src)
        self.assertIn("Command('mhs104.check'",src)
        self.assertIn("Command('mhs104.off'",src)
        self.assertIn('mode!=\'matching\'',src)
        self.assertIn('_ATTEMPTED=True',src)
        self.assertIn('return previous(service,*newargs,**newkwargs)',src)
        self.assertNotIn('create_situation(',src)
        self.assertNotIn('SituationGuestList',src)
        self.assertNotIn('mhs89_precreate_hook',src)
        self.assertIn('MHS_EA_FILTER_CONSTRAINTS_ENABLED=False',
            new['mhs57_filter_runtime.py'].read_text())

if __name__=='__main__':
    unittest.main()
