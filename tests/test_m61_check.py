"""M61C regression: the pilot records the Sim and exposes a read-only check."""
import ast
import unittest
from pathlib import Path
SRC=Path(__file__).resolve().parents[1]/'src'/'m58_selection'/'mhs61_pilot_command.py'
class M61CheckTests(unittest.TestCase):
    def test_pilot_records_exact_name_class_and_id(self):
        s=SRC.read_text()
        self.assertIn('_LAST_TARGET=(str(slot)',s)
        self.assertIn("getattr(candidate,'first_name','')",s)
        self.assertIn('selected_class=klass',s)
        self.assertIn('int(candidate.sim_id)',s)
    def test_check_never_calls_invitation(self):
        tree=ast.parse(SRC.read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='arrival_status')
        names=[n.id for n in ast.walk(fn) if isinstance(n,ast.Name)]
        self.assertNotIn('create_one_existing_student',names)
        self.assertIn('services',names)
        self.assertIn('current_slot',names)
    def test_command_registered(self):
        self.assertIn("'mhs61.check'",SRC.read_text())
if __name__=='__main__':
    unittest.main()
