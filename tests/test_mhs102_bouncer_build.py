"""M102 Mac overlay retains M101d and replaces only the diagnostic reader."""
import unittest
from tooling.build_mhs101_one_slot import script_sources as m101_scripts
from tooling.build_mhs102_bouncer import script_sources as m102_scripts

class M102BuildTests(unittest.TestCase):
    def test_only_runtime_overlaid_one_new_read_only_module(self):
        base={p.name:p for p in m101_scripts()}
        newer={p.name:p for p in m102_scripts()}
        self.assertEqual(len(base),40)
        self.assertEqual(len(newer),41)
        for name,path in base.items():
            if name=='mhs101_original_slot_runtime.py':
                self.assertEqual(newer[name].parent.name,'m102_bouncer')
            else:
                self.assertEqual(newer[name],path)
        self.assertEqual(newer['mhs102_bouncer_observer.py'].parent.name,
                         'm102_bouncer')
    def test_m102_check_observes_without_spawning(self):
        code=next(p for p in m102_scripts()
                  if p.name=='mhs101_original_slot_runtime.py').read_text()
        self.assertIn('checked[\'bouncer_probe\']=bouncer_probe(mgr,situation_id)',code)
        self.assertIn('callback=None',code)
        self.assertIn('context_checker=_context',code)
        self.assertNotIn('create_one_existing_student(',code)
        self.assertNotIn('manager.create_situation(',code)
        obs=next(p for p in m102_scripts()
                 if p.name=='mhs102_bouncer_observer.py').read_text()
        self.assertNotIn('.create_situation(',obs)
        self.assertNotIn('.add_sim(',obs)
        self.assertNotIn('.spawn_sim(',obs)

if __name__=='__main__':
    unittest.main()
