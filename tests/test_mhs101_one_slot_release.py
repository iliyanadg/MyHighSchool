"""M101 static safety: original EA call only, no eager arming."""
import sys
import unittest
from pathlib import Path
from tooling.build_mhs101_one_slot import script_sources, UI, COUNT
from tooling.build_mhs99_trace import script_sources as old_scripts

class M101BuildTests(unittest.TestCase):
    def test_package_uses_m99_original_modules_except_ui_loader(self):
        base={p.name:p for p in old_scripts()}
        now={p.name:p for p in script_sources()}
        self.assertEqual(len(base),34)
        self.assertEqual(len(now),COUNT)
        self.assertEqual(COUNT,40)
        for name,p in base.items():
            self.assertEqual(now[name],UI if name=='mhs55_attendance_ui.py'
                             else p)
    def test_one_opt_in_command_and_no_automatic_invites(self):
        sources={p.name:p for p in script_sources()}
        runtime=sources['mhs101_original_slot_runtime.py'].read_text(encoding='utf-8')
        self.assertIn("Command('mhs101.arm'",runtime)
        self.assertIn("Command('mhs101.check'",runtime)
        self.assertIn("spawn_sims_during_zone_spin_up",sources[
            'mhs101_original_slot_gate.py'].read_text(encoding='utf-8'))
        self.assertIn('OneSlotPilot()',runtime)
        self.assertIn('services.sim_filter_service()',runtime)
        self.assertNotIn('create_one_existing_student(',runtime)
        self.assertNotIn('create_situation(',runtime)
        self.assertIn('context_checker=_context',runtime)
        self.assertIn('on_created=_created',runtime)
        self.assertIn('trace_situation(',runtime)
        self.assertIn('created_situation_id',runtime)
        self.assertIn('latest_verification',runtime)
        self.assertIn('if not install():',runtime)

    def test_m89_keeps_original_ea_request_flags(self):
        source=Path('src/m89_selection/mhs89_precreate_hook.py').read_text()
        self.assertIn("copied=dict(kwargs)",source)
        self.assertIn("copied['guest_list']=new_list",source)
        self.assertIn('context_checker',source)

if __name__=='__main__':
    unittest.main()
