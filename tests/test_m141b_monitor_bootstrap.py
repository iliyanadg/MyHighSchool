"""M141b failsafe school journal bootstrap offline wiring tests."""
import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'src'/'m141_day_trace'/'mhs141_classroom_controller.py').read_text(encoding='utf-8')


class TestM141bBootstrap(unittest.TestCase):
    def test_python_syntax_and_hook_safeguards(self):
        tree=ast.parse(SOURCE)
        methods={n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        for name in ('_m141_start_watcher','_m141_start_trace','_m141_stop_trace',
                     'm141_monitor','m141_log','arm_m127'):
            self.assertIn(name,methods)
        self.assertIn("_m141_start_trace(self,'school_situation')",SOURCE)
        self.assertIn("_m141_start_watcher(trial)",SOURCE)
        self.assertIn("_m141_start_trace(_RUNTIME,'monitor_fallback')",SOURCE)
        self.assertIn("_m141_start_trace(_RUNTIME,'log_fallback')",SOURCE)
        self.assertIn("runtime.m141_timer=handle",SOURCE)
        self.assertIn("runtime.m141_trace_origin=origin",SOURCE)
        self.assertIn("runtime.m141_journal.flush()",SOURCE)
        self.assertIn("runtime.m141_start_error='START_'+type(exc).__name__",SOURCE)
        self.assertIn("runtime.in_school()",SOURCE)
        self.assertIn("len(j.samples) if j else 0",SOURCE)
        self.assertIn("M141b MONITOR: scuola=",SOURCE)
    def test_does_not_change_student_actions_in_monitor(self):
        tree=ast.parse(SOURCE)
        functions={node.name:node for node in ast.walk(tree)
                   if isinstance(node,ast.FunctionDef)}
        for name in ('_m141_start_watcher','_m141_start_trace','m141_monitor'):
            lines=SOURCE.splitlines()
            first=functions[name].lineno-1
            last=next((i for i in range(first+1,len(lines))
                       if lines[i].startswith('def ')
                       or lines[i].startswith('@sims4.commands.Command(')),len(lines))
            source='\n'.join(lines[first:last])
            for action in ('push_super_affordance(', 'cancel_interaction(',
                           'set_position(', 'teleport('):
                self.assertNotIn(action,source)
    def test_explicit_save_from_monitor(self):
        self.assertIn("'trace_started_'+origin",SOURCE)
        self.assertIn("runtime.m141_journal.flush()",SOURCE)
        self.assertIn("'mhs141.monitor'",SOURCE)

if __name__ == '__main__':
    unittest.main()
