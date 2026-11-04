"""M112 integrated OFFLINE Base count and native guest takeover regression.

No Sims runtime, no proof of NPC spawn or class seating. The original
current EA count of three is passed through the *real wrapper*, not a
guessed '6 minus 3' deduction; all gates remain synthetic fixtures.
"""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))

from tests.test_m108_native_invitation import (
    session, CONTEXT, BASE_SITUATION, CORE_SITUATION, CORE_JOBS
)
from tests.test_m108_native_base_count import (
    fake_ea_schedule, all_gates, verified_context
)
from tests.test_m108_native_precreate import (
    manager, all_proof, Situation, CoreSituation
)
from tests.test_m112_native_guest_takeover import (
    VERIFIED, base_original, core_original
)
from mhs108_native_base_count import (
    install_offline_only, propose_native_base_count
)
from mhs108_native_precreate import install as install_precreate


class RealCountAndRegisteredGuestPlanTests(unittest.TestCase):
    def test_direct_count_alone_does_not_bypass_verified_early_context(self):
        s=session()
        self.assertEqual(propose_native_base_count(
            (3,3),277657,BASE_SITUATION,s,
            dict(verified_context(adjustment=0),
                 native_count_return_observed_in_current_callback=True,
                 exact_original_base_count_observed=(3,3),
                 school_verified=False)),(3,3))
        self.assertEqual(propose_native_base_count(
            (3,3),277657,BASE_SITUATION,s,
            dict(verified_context(adjustment=0),
                 native_count_return_observed_in_current_callback=True,
                 exact_original_base_count_observed=(5,5))),(3,3))

    def test_current_original_ea_count_three_can_propose_eight_only_inside_wrapper(self):
        Day,Main,Venue,Other,base,staff=fake_ea_schedule((3,3))
        s=session()
        undo=install_offline_only(
            Day,s,lambda:verified_context(adjustment=0),all_gates())
        self.assertTrue(callable(undo))
        try:
            self.assertEqual(Main.get_long_term_situation_count(base,None),
                             (8,8))
            self.assertEqual(Main.calls,1)
            self.assertEqual(Main.get_long_term_situation_count(staff,None),
                             (3,3))
            self.assertEqual(Other.get_long_term_situation_count(base,None),
                             (3,3))
            self.assertEqual(Venue.get_long_term_situation_count(base,None),
                             (3,3))
        finally:
            self.assertTrue(undo())
        self.assertEqual(Main.get_long_term_situation_count(base,None),
                         (3,3))

    def test_original_three_base_slots_to_eight_exact_invites_and_five_core(self):
        Day,Main,Venue,Other,base,staff=fake_ea_schedule((3,3))
        s=session()
        count_undo=install_offline_only(
            Day,s,lambda:verified_context(adjustment=0),all_gates())
        Manager=manager()
        guest_undo=install_precreate(
            Manager,s,lambda:VERIFIED,all_proof())
        self.assertTrue(callable(count_undo))
        self.assertTrue(callable(guest_undo))
        try:
            count=Main.get_long_term_situation_count(base,None)
            self.assertEqual(count,(8,8))
            m=Manager()
            vanilla_lists=[]
            for index in range(count[0]):
                original=base_original(900+index)
                vanilla_lists.append(original)
                self.assertEqual(m.create_situation(
                    Situation(),guest_list=original),101+index)
                self.assertEqual(
                    [g.sim_id for g in m.calls[-1][1].guest_info_gen()],
                    [int(s.manifest['base_ids'][index])])
            original_core=core_original()
            self.assertEqual(m.create_situation(
                CoreSituation(),guest_list=original_core),109)
            self.assertEqual([g.sim_id for g in
                m.calls[-1][1].guest_info_gen()],
                [200,2,3,4,10,11])
            roster_guests=set(
                str(g.sim_id) for call in m.calls
                for g in call[1].guest_info_gen()
                if g.job_type.guid64 in set((277894,)+CORE_JOBS))
            self.assertEqual(roster_guests,
                set(s.manifest['all_16'])-set(s.manifest['playable']))
            self.assertEqual(len(roster_guests),13)
            self.assertEqual(len(m.calls),9)
            self.assertEqual(
                [g.sim_id for g in vanilla_lists[0].guest_info_gen()],
                [900])
            self.assertFalse(s.snapshot()['attendance_verified'])
            self.assertFalse(s.snapshot()['ea_job_assignment_verified'])
        finally:
            self.assertTrue(guest_undo())
            self.assertTrue(count_undo())

    def test_unverified_original_call_cannot_take_over_vanilla_students(self):
        Day,Main,_,_,base,_=fake_ea_schedule((3,3))
        s=session()
        undo=install_offline_only(
            Day,s,lambda:verified_context(
                native_weekly_school_origin_verified=False),
                all_gates())
        self.assertTrue(callable(undo))
        try:
            self.assertEqual(Main.get_long_term_situation_count(base,None),
                             (3,3))
        finally:
            self.assertTrue(undo())


if __name__=='__main__':
    unittest.main()
