"""M85: separate physical presence from real EA-school situation membership."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m85_diagnostics'))
from mhs85_reconcile import summarize
from mhs85_live_snapshot import snapshot

class M85Tests(unittest.TestCase):
    def test_pupils_on_lot_are_not_automatically_in_ea_school(self):
        classes=(('11','12'),('21','22'))
        out=summarize(classes,['11','12','21','99'],
                      {'11':[277733],'12':[123],'21':[298052],'99':[277733]})
        self.assertEqual(out['registered_on_lot'],3)
        self.assertEqual(out['registered_in_ea_school_situations'],2)
        self.assertEqual(out['unregistered_in_ea_school_situations'],1)
        self.assertEqual(out['in_ea_school_situations_per_class'],(1,1))
        self.assertFalse(out['seated_in_correct_class_verified'])

    def test_live_scan_never_changes_sim_or_situations(self):
        def info(sid):
            return SimpleNamespace(sim_id=sid,age=1,species=1,
                                   get_sim_instance=lambda:('sim',sid))
        manager=SimpleNamespace(
            get_situations_sim_is_in=lambda sim:(
                SimpleNamespace(guid64=277733) if sim[1]=='11'
                else SimpleNamespace(guid64=111),))
        manifest=SimpleNamespace(class_ids=(('11','12'),('21',)))
        out=snapshot(manifest,(info('11'),info('12'),info('21')),
                     manager,1,1,lambda s:s.guid64)
        self.assertEqual(out['status'],'observed')
        self.assertEqual(out['registered_in_ea_school_situations'],1)
        self.assertEqual(out['registered_on_lot'],3)

    def test_missing_ea_api_fails_closed(self):
        out=snapshot(SimpleNamespace(class_ids=(('11',),)),
                     (),object(),1,1,lambda s:s.guid64)
        self.assertNotEqual(out['status'],'observed')

    def test_build_includes_m85_modules_without_new_ea_tunings(self):
        s=(ROOT/'tooling'/'build_m58_diagnostic.py').read_text()
        for name in ('mhs85_reconcile.py','mhs85_live_snapshot.py',
                     'mhs85_ui_bridge.py'):
            self.assertIn(name,s)
        self.assertIn("assert len(SCRIPTS)==32",s)
        self.assertIn("package_bytes()",s)

if __name__=='__main__':
    unittest.main()
