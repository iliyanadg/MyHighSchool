"""M153: verified school-to-home scratch slot must not deactivate MHS.

Execute the shipping arm_m127 function extracted from the real controller.
Only an already verified live MHS session can reuse the scratch identity.
Save mutations, new arm, different save and roster rearm must fail closed.
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m2_registry'))
sys.path.insert(0,str(ROOT/'src'/'m147_integrated'))
from mhs56_slot_identity import TravelSlotGuard,IdentityError
from mhs147_class_timing_policy import roster_rearm_required


GROUPS=(tuple(str(100+i) for i in range(8)),
        tuple(str(108+i) for i in range(8)))
PINNED={278965:'500',278966:'501',278967:'502',278968:'503',303765:'504'}


class Runtime:
    def __init__(self):
        self.active=True
        self.slot='15'
        self.lesson_classes=GROUPS
        self.targets=tuple(str(100+i) for i in range(11))
        self.pinned=dict(PINNED)
        self.home_zone=100
        self.stopped=0
        self.error=''
    def in_school(self):
        return False
    def stop(self):
        self.stopped+=1
        return False


class FakeRoster:
    def __init__(self,groups):
        self.groups=groups
    def class_members(self,klass):
        return self.groups[klass-1]


class FakeStore:
    groups=GROUPS
    def __init__(self,folder):
        pass
    def load(self,slot):
        return FakeRoster(self.groups)


class Tests(unittest.TestCase):
    @staticmethod
    def controller_func():
        path=ROOT/'src'/'m145_class2_playable'/'mhs145_classroom_controller.py'
        tree=ast.parse(path.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                  and n.name=='arm_m127')
        return compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec')

    def env(self,active=True,real_slot=None,stable='0xbeef',household=721,
            zone=100,new_targets=None):
        guard=TravelSlotGuard()
        guard.resolve(15,'0xbeef',721)
        runtime=Runtime() if active else None
        watcher=[]
        def verified_slot(allow_travel=False):
            return guard.resolve(real_slot,stable,household,
                                 allow_travel=allow_travel)
        def registered(allow_travel=False):
            slot=verified_slot(allow_travel=allow_travel)
            return slot,(new_targets if new_targets is not None
                         else tuple(str(100+i) for i in range(11))),dict(PINNED)
        env={
            '_RUNTIME':runtime,
            'zone_schedule':lambda:(zone,None),
            'SCHOOL_SCHEDULES':frozenset((277657,279958)),
            'registered_eight':registered,
            'RosterStore':FakeStore,
            'FOLDER':'unused',
            'roster_rearm_required':roster_rearm_required,
            'current_slot':verified_slot,
            '_m141_start_watcher':watcher.append}
        exec(self.controller_func(),env)
        return env,guard,watcher,runtime

    def test_first_activation_does_not_accept_temporary_slot(self):
        env,guard,watcher,rt=self.env(active=False)
        msg=env['arm_m127']()
        self.assertIn('ID salvataggio temporaneo',msg)
        self.assertEqual(guard.last_source,'blocked_write_scratch')
        self.assertEqual(watcher,[])

    def test_return_home_reuses_verified_session_and_watcher(self):
        env,guard,watcher,rt=self.env()
        msg=env['arm_m127']()
        self.assertIn('M153 GIA ATTIVA',msg)
        self.assertEqual(guard.last_source,'verified_zone_travel')
        self.assertEqual(watcher,[rt])
        self.assertEqual(rt.stopped,0)
        self.assertEqual(rt.lesson_classes,GROUPS)
        self.assertEqual(rt.pinned,PINNED)

    def test_changed_roster_cannot_rearm_during_scratch(self):
        env,guard,watcher,rt=self.env(
            new_targets=tuple(str(300+i) for i in range(11)))
        msg=env['arm_m127']()
        self.assertIn('RICARICA RINVIATA',msg)
        self.assertEqual(guard.last_source,'blocked_write_scratch')
        self.assertEqual(watcher,[])
        self.assertEqual(rt.stopped,0)

    def test_different_save_slot_refused(self):
        env,guard,watcher,rt=self.env(real_slot=16)
        msg=env['arm_m127']()
        self.assertIn('cambiare salvataggio',msg)
        self.assertEqual(rt.stopped,0)
        self.assertFalse(watcher)

    def test_different_guid_refused_and_guard_reset(self):
        env,guard,watcher,rt=self.env(stable='0xdead')
        msg=env['arm_m127']()
        self.assertIn('Identita salvataggio cambiata',msg)
        self.assertEqual(rt.stopped,0)
        self.assertIsNone(guard.slot)

    def test_different_household_refused(self):
        env,guard,watcher,rt=self.env(household=722)
        msg=env['arm_m127']()
        self.assertIn('Nucleo attivo diverso',msg)
        self.assertEqual(rt.stopped,0)

    def test_real_slot_rearm_still_uses_original_stop_guard(self):
        env,guard,watcher,rt=self.env(
            real_slot=15,new_targets=tuple(str(300+i) for i in range(11)))
        msg=env['arm_m127']()
        self.assertIn('M147 RICARICA BLOCCATA',msg)
        self.assertEqual(rt.stopped,1)
        self.assertEqual(watcher,[])


if __name__=='__main__':
    unittest.main()
