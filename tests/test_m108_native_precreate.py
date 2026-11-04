"""M108 pre-create wiring tests; NO game integration is authorized."""
import unittest

from tests.test_m108_native_invitation import (
    session, EAList, Guest, Job, CONTEXT, BASE_SITUATION,
    CORE_SITUATION, BASE_JOB)
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))
from mhs108_native_precreate import install, REQUIRED_LIVE_GATES


class Situation(object):
    guid64 = BASE_SITUATION


class CoreSituation(object):
    guid64 = CORE_SITUATION


class OutsideSituation(object):
    guid64 = 666666


def all_proof():
    """Synthetic flags only: *never* turn this into a live enable check."""
    return {k: True for k in REQUIRED_LIVE_GATES}


def manager():
    class Manager(object):
        def __init__(self):
            self.calls = []
            self.next_id = 100

        def create_situation(self, typ, guest_list=None, user_facing=False,
                             spawn_sims_during_zone_spin_up=False):
            self.calls.append((typ, guest_list, user_facing,
                               spawn_sims_during_zone_spin_up))
            self.next_id += 1
            return self.next_id

    return Manager


class NativePrecreateAdapterTests(unittest.TestCase):
    def test_not_installed_without_all_safety_gates(self):
        for missing in REQUIRED_LIVE_GATES:
            Manager = manager()
            proof = all_proof()
            proof[missing] = False
            self.assertIsNone(install(Manager, session(),
                                      lambda: CONTEXT, proof))
            original = EAList()
            m = Manager()
            m.create_situation(Situation(), guest_list=original)
            self.assertIs(m.calls[0][1], original)

    def test_pure_ea_base_then_core_same_calls_no_random(self):
        Manager = manager()
        s = session()
        uninstall = install(Manager, s, lambda: CONTEXT, all_proof())
        self.assertTrue(callable(uninstall))
        m = Manager()
        original_lists = []
        for n, sid in enumerate(s.manifest['base_ids']):
            original = EAList()
            original_lists.append(original)
            created = m.create_situation(
                Situation(), guest_list=original,
                user_facing=False, spawn_sims_during_zone_spin_up=True)
            self.assertEqual(created, 101 + n)
            call = m.calls[-1]
            self.assertEqual(call[1].invite_only, True)
            self.assertEqual([g.sim_id for g in call[1].guest_info_gen()],
                             [int(sid)])
            self.assertFalse(call[2])
            self.assertTrue(call[3])
            self.assertEqual(list(original.guest_info_gen()), [])
        # A ninth EA Base request does not create an extra/random NPC.
        self.assertIsNone(m.create_situation(Situation(), guest_list=EAList()))
        self.assertEqual(len(m.calls), 8)

        core = EAList()
        core.add_guest_info(Guest(2020, Job(277895)))
        created = m.create_situation(CoreSituation(), guest_list=core)
        self.assertEqual(created, 109)
        self.assertEqual(len(m.calls), 9)
        guests = list(m.calls[-1][1].guest_info_gen())
        self.assertEqual([x.sim_id for x in guests], [2020, 2, 3, 4, 10, 11])
        self.assertEqual([x.sim_id for x in core.guest_info_gen()], [2020])
        snap = s.snapshot()
        self.assertTrue(snap['all_nine_situations_created'])
        self.assertEqual(len(snap['student_ids_requested']), 13)
        self.assertFalse(snap['attendance_verified'])
        self.assertFalse(snap['actual_ea_core_reservations_verified'])
        self.assertTrue(uninstall())
        self.assertFalse(uninstall())

    def test_unrelated_events_always_remain_original(self):
        Manager = manager()
        uninstall = install(Manager, session(), lambda: CONTEXT, all_proof())
        m = Manager()
        original = EAList()
        m.create_situation(OutsideSituation(), guest_list=original)
        self.assertIs(m.calls[-1][1], original)
        self.assertTrue(uninstall())

    def test_unverified_context_preserves_vanilla_without_suppression(self):
        Manager = manager()
        s = session()
        uninstall = install(Manager, s,
                            lambda: dict(CONTEXT, native_origin_verified=False),
                            all_proof())
        m = Manager()
        old = EAList()
        m.create_situation(Situation(), guest_list=old)
        self.assertEqual(len(m.calls), 1)
        self.assertIs(m.calls[0][1], old)
        self.assertEqual(s.snapshot()['base_situations_created'], 0)
        uninstall()

    def test_core_unrecognized_ea_student_fails_closed(self):
        Manager = manager()
        s = session()
        uninstall = install(Manager, s, lambda: CONTEXT, all_proof())
        m = Manager()
        old = EAList()
        old.add_guest_info(Guest(999, Job(BASE_JOB)))
        self.assertIsNone(
            m.create_situation(CoreSituation(), guest_list=old))
        self.assertEqual(len(m.calls), 0)
        self.assertEqual([g.sim_id for g in old.guest_info_gen()], [999])
        uninstall()

    def test_native_exception_must_not_retry_and_does_not_advance(self):
        class Reject(object):
            def __init__(self):
                self.calls = 0

            def create_situation(self, typ, guest_list=None, **kwargs):
                self.calls += 1
                raise RuntimeError('native EA creation failed after call')

        s = session()
        uninstall = install(Reject, s, lambda: CONTEXT, all_proof())
        instance = Reject()
        with self.assertRaises(RuntimeError):
            instance.create_situation(Situation(), guest_list=EAList())
        self.assertEqual(instance.calls, 1)
        self.assertEqual(s.snapshot()['base_situations_created'], 0)
        self.assertTrue(uninstall())

    def test_positional_guest_list_is_preserved(self):
        Manager = manager()
        s = session()
        uninstall = install(Manager, s, lambda: CONTEXT, all_proof())
        m = Manager()
        old = EAList()
        m.create_situation(Situation(), old, False, True)
        self.assertEqual(len(m.calls), 1)
        self.assertEqual([g.sim_id for g in m.calls[0][1].guest_info_gen()],
                         [5])
        self.assertTrue(m.calls[0][3])
        self.assertEqual(list(old.guest_info_gen()), [])
        uninstall()

    def test_second_adapter_rejected_without_stacking(self):
        Manager = manager()
        s = session()
        undo = install(Manager, s, lambda: CONTEXT, all_proof())
        self.assertIsNone(install(Manager, session(), lambda: CONTEXT,
                                  all_proof()))
        self.assertTrue(undo())


if __name__ == '__main__':
    unittest.main()
