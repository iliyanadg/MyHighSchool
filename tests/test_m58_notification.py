"""M58 compact notification regression without importing EA runtime."""
import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class NotificationTests(unittest.TestCase):
    def test_compact_report_under_notification_limit(self):
        path=ROOT/'src'/'m55_attendance'/'mhs55_attendance_ui.py'
        tree=ast.parse(path.read_text())
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='compact_diagnostic')
        class Probe:
            @staticmethod
            def status():
                return {'installed':True,'counts':{277733:{'calls':6},298052:{'calls':1},298096:{'calls':1}},'error':'none'}
        ns={'mhs58_situation_probe':Probe()}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'compact_diagnostic','exec'),ns)
        result=ns['compact_diagnostic']()
        self.assertIn('Studenti:6',result)
        self.assertIn('Core:1',result)
        self.assertIn('Mensa:0',result)
        self.assertIn('NON presenze',result)
        self.assertLess(len(result),240)
    def test_snapshot_is_saved_on_diagnostic_click(self):
        source=(ROOT/'src'/'m55_attendance'/'mhs55_attendance_ui.py').read_text()
        self.assertIn('mhs58_situation_probe.save_report(folder, mhs57_filter_runtime.m59_snapshot())',source)

    def test_ui_passes_short_report_to_notification(self):
        source=(ROOT/'src'/'m55_attendance'/'mhs55_attendance_ui.py').read_text()
        self.assertIn("text=_text(compact_diagnostic()+' '+short_line(result85))",source)
        self.assertIn('result85=capture_status(folder)',source)


if __name__=='__main__':
    unittest.main()
