"""M99 retained-game build topology and opt-in safety, no game imports."""
import unittest
from tooling.build_mhs94_probe import script_sources as old_sources
from tooling.build_mhs99_trace import script_sources, PILOT, TRACE
from pathlib import Path

class M99BuildTests(unittest.TestCase):
    def test_original_m94_menu_and_scripts_preserved(self):
        old={p.name:p for p in old_sources()}
        new={p.name:p for p in script_sources()}
        self.assertEqual(len(old),33)
        self.assertEqual(len(new),34)
        for name,path in old.items():
            if name=='mhs61_pilot_command.py':
                self.assertEqual(new[name],PILOT)
            else:
                self.assertEqual(new[name],path)
        self.assertEqual(new['mhs99_situation_trace.py'],TRACE)
        self.assertEqual(PILOT.parent.name,'m99_trace')

    def test_new_pilot_still_needs_explicit_cheat_command(self):
        source=PILOT.read_text(encoding='utf-8')
        self.assertIn("Command('mhs61.pilot'",source)
        self.assertIn("Command('mhs61.trace'",source)
        self.assertIn("create_one_existing_student(",source)
        self.assertIn("if key in _ATTEMPTED:",source)
        self.assertIn("trace_situation(mgr,info,_LAST_SITUATION_ID)",source)
        self.assertNotIn("from mhs96_exact_school_count import",source)
        self.assertNotIn("mhs97_core_filter_policy",source)

    def test_original_pilot_not_modified(self):
        original=next(p for p in old_sources() if p.name=='mhs61_pilot_command.py')
        code=original.read_text(encoding='utf-8')
        self.assertNotIn('mhs99_situation_trace',code)
        self.assertIn("Command('mhs61.check'",code)

if __name__=='__main__':
    unittest.main()
