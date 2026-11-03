"""M112: replace ONLY explicitly validated vanilla school student guests.

No real EA install. This proves safe cloning, exact 13-ID routing through
the pre-existing M108 invitation/precreate seams, and fail-closed behavior.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'/'m108_native_roster'))
from tests.test_m108_native_invitation import (
    session, EAList, Guest, Job, CONTEXT, CORE, CORE_JOBS,
    BASE_JOB, BASE_SITUATION, CORE_SITUATION,
)
from tests.test_m108_native_precreate import (
    all_proof, manager, Situation, CoreSituation,
)
from mhs108_native_precreate import install

VERIFIED = dict(CONTEXT, original_ea_school_guest_takeover_verified=True)


def base_original(sid=999):
    old = EAList()
    old.add_guest_info(Guest(sid, Job(BASE_JOB)))
    return old


def core_original():
    old = EAList()
    old.add_guest_info(Guest(200, Job(277895)))
    for index, job in enumerate(CORE_JOBS):
        old.add_guest_info(Guest(901+index, Job(job), True))
    return old


class NativeVanillaGuestTakeoverTests(unittest.TestCase):
    def test_original_base_random_teen_replaced_by_exact_registered_one(self):
        s = session()
        original = base_original()
        before = tuple((g.sim_id, g.job_type.guid64)
                       for g in original.guest_info_gen())
        ticket, clone = s.preview(BASE_SITUATION, original, VERIFIED)
        self.assertEqual(ticket, 'base:5')
        self.assertEqual([(g.sim_id,g.job_type.guid64)
                          for g in clone.guest_info_gen()],[(5,BASE_JOB)])
        self.assertEqual(before,tuple((g.sim_id,g.job_type.guid64)
                          for g in original.guest_info_gen()))
        self.assertTrue(all(not g.accept_alternate_sim
                            for g in clone.guest_info_gen()))
        self.assertEqual(s.snapshot()['base_situations_created'],0)

    def test_original_five_core_random_teens_replaced_with_five_registered(self):
        s = session()
        original = core_original()
        ticket, clone = s.preview(CORE_SITUATION, original, VERIFIED)
        self.assertEqual(ticket,'core')
        seen = list(clone.guest_info_gen())
        self.assertEqual([g.sim_id for g in seen],[200,2,3,4,10,11])
        self.assertEqual([g.job_type.guid64 for g in seen[1:]],
                         list(CORE_JOBS))
        self.assertTrue(all(g.accept_alternate_sim is False
                            for g in seen[1:]))
        self.assertEqual(len(tuple(original.guest_info_gen())),6)

    def test_unknown_vanilla_students_cannot_be_replaced_without_separate_proof(self):
        for guid, original in (
                (BASE_SITUATION,base_original()),
                (CORE_SITUATION,core_original())):
            s=session()
            self.assertEqual(s.preview(guid,original,CONTEXT),(None,None))
            self.assertEqual(s.snapshot()['base_situations_created'],0)
            self.assertFalse(s.snapshot()['core_situation_created'])

    def test_unverified_schedule_origin_does_not_take_over_vanilla_guests(self):
        s=session()
        self.assertEqual(s.preview(
            BASE_SITUATION, base_original(),
            dict(VERIFIED,native_origin_verified=False)),(None,None))

    def test_extra_unknown_job_is_not_discarded_silently(self):
        s=session()
        original=core_original()
        original.add_guest_info(Guest(9999,Job(199000)))
        self.assertEqual(s.preview(CORE_SITUATION,original,VERIFIED),
                         (None,None))

    def test_duplicate_original_student_role_is_ambiguous(self):
        s=session()
        old=base_original()
        old.add_guest_info(Guest(998,Job(BASE_JOB)))
        self.assertEqual(s.preview(BASE_SITUATION,old,VERIFIED),(None,None))
        old2=core_original()
        old2.add_guest_info(Guest(777,Job(CORE_JOBS[0])))
        self.assertEqual(s.preview(CORE_SITUATION,old2,VERIFIED),
                         (None,None))

    def test_selected_enrolled_teen_as_original_teacher_is_rejected(self):
        s=session()
        old=core_original()
        guests=list(old.guest_info_gen())
        old._guests[0] = Guest(2,Job(277895))
        self.assertEqual(s.preview(CORE_SITUATION,old,VERIFIED),(None,None))

    def test_original_teacher_in_base_slot_is_never_silently_removed(self):
        s=session()
        original=base_original()
        original.add_guest_info(Guest(200,Job(277895)))
        self.assertEqual(s.preview(BASE_SITUATION,original,VERIFIED),
                         (None,None))

    def test_native_precreate_receives_exact_one_base_and_five_core_guests(self):
        s = session()
        Manager = manager()
        undo = install(Manager, s, lambda:VERIFIED, all_proof())
        self.assertTrue(callable(undo))
        try:
            m=Manager()
            base=base_original()
            result=m.create_situation(Situation(),guest_list=base)
            self.assertEqual(result,101)
            got=list(m.calls[-1][1].guest_info_gen())
            self.assertEqual([x.sim_id for x in got],[5])
            self.assertEqual([x.sim_id for x in base.guest_info_gen()],[999])
            # Next request is Core; no random 5 NPCs may survive.
            core=core_original()
            result=m.create_situation(CoreSituation(),guest_list=core)
            self.assertEqual(result,102)
            got=list(m.calls[-1][1].guest_info_gen())
            self.assertEqual([g.sim_id for g in got],[200,2,3,4,10,11])
            self.assertEqual(len(m.calls),2)
            self.assertFalse(s.snapshot()['attendance_verified'])
        finally:
            self.assertTrue(undo())

    def test_vanilla_original_not_modified_if_ea_creation_raises(self):
        s=session()
        old=base_original()
        class Manager(object):
            calls=0
            def create_situation(self,typ,guest_list=None):
                self.calls+=1
                raise RuntimeError('original EA failed')
        undo=install(Manager,s,lambda:VERIFIED,all_proof())
        try:
            obj=Manager()
            with self.assertRaises(RuntimeError):
                obj.create_situation(Situation(),guest_list=old)
            self.assertEqual(obj.calls,1)
            self.assertEqual([g.sim_id for g in old.guest_info_gen()],
                             [999])
            self.assertEqual(s.snapshot()['base_situations_created'],0)
        finally:
            self.assertTrue(undo())


if __name__=='__main__':
    unittest.main()
