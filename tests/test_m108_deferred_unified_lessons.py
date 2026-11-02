"""M108 deferred roles: the real Bouncer assignment follows creation."""
import unittest

from tests.test_m108_unified_lessons import fixture,run
from tests.test_m108_post_bouncer_audit import (
    NativeSituation,NativeManager,barrier)


class DeferredUnifiedLessonTests(unittest.TestCase):
    def _prepare(self):
        EA,A1,A2,B,budget,counts,sims,undo=fixture(deferred=True)
        # The EA try_start returned all three native situation IDs and
        # reserved the invited Sim candidates from its local input set.
        ids=(run(B,sims,counts),run(A1,sims,counts),run(A2,sims,counts))
        self.assertEqual(len(set(ids)),3)
        self.assertTrue(budget.snapshot()['phase_plan_complete_offline'])
        audit=undo.deferred_native_audit
        self.assertEqual(audit.snapshot()['native_created_awaiting_bouncer'],3)
        self.assertEqual(audit.snapshot()['native_jobs_verified'],0)
        return EA,A1,A2,B,budget,counts,sims,undo,ids,audit

    def test_new_native_situation_ids_are_pending_not_actual_assignment(self):
        EA,A1,A2,B,budget,counts,sims,undo,ids,audit=self._prepare()
        try:
            m=NativeManager()
            for sid in ids:
                self.assertEqual(
                    audit.observe(sid,m,{})['status'],
                    'CREATED_AWAITING_BOUNCER')
            self.assertEqual(m.calls,0)
            self.assertFalse(audit.snapshot()['full_day_attendance_verified'])
            self.assertFalse(audit.snapshot()['all_registered_16_seated_verified'])
        finally:
            undo()

    def test_post_bouncer_exact_roles_confirm_students_and_staff(self):
        EA,A1,A2,B,budget,counts,sims,undo,ids,audit=self._prepare()
        try:
            actual={
                ids[0]:NativeSituation(304567,{
                    280777:(10,11,12,13,14,15),
                    277918:(200,201),278224:(202,)}),
                ids[1]:NativeSituation(304565,{277919:(2,3)}),
                ids[2]:NativeSituation(304703,{
                    277919:(4,5,6,7,8)}),
            }
            manager=NativeManager(actual)
            for sid in ids:
                self.assertEqual(
                    audit.observe(sid,manager,barrier(sid))['status'],
                    'NATIVE_JOBS_MATCH')
            self.assertEqual(audit.snapshot()['native_jobs_verified'],3)
            self.assertEqual(audit.snapshot()['native_created_awaiting_bouncer'],0)
            self.assertFalse(audit.snapshot()['full_day_attendance_verified'])
        finally:
            self.assertTrue(undo())

    def test_post_bouncer_wrong_job_rejected_even_if_native_created(self):
        EA,A1,A2,B,budget,counts,sims,undo,ids,audit=self._prepare()
        try:
            manager=NativeManager({
                ids[0]:NativeSituation(304567,{
                    280777:(200,11,12,13,14,15),
                    277918:(10,201),278224:(202,)})
            })
            before=manager.calls
            self.assertEqual(
                audit.observe(ids[0],manager,barrier(ids[0]))['status'],
                'WRONG_EA_SIM_OR_JOB')
            self.assertEqual(manager.calls,before+1)
            self.assertFalse(audit.snapshot()['full_day_attendance_verified'])
            self.assertEqual(audit.snapshot()['native_jobs_rejected'],1)
        finally:
            undo()

    def test_during_spinup_source_proof_missing_remains_pending(self):
        EA,A1,A2,B,budget,counts,sims,undo,ids,audit=self._prepare()
        try:
            manager=NativeManager({
                ids[0]:NativeSituation(304567,{
                    280777:(10,11,12,13,14,15),
                    277918:(200,201),278224:(202,)})
            })
            bad=barrier(ids[0],ea_bouncer_assignment_completed=False)
            self.assertEqual(audit.observe(ids[0],manager,bad)['status'],
                             'CREATED_AWAITING_BOUNCER')
            self.assertEqual(manager.calls,0)
        finally:
            undo()

    def test_no_duplicate_ea_create_if_receipt_still_pending(self):
        EA,A1,A2,B,budget,counts,sims,undo,ids,audit=self._prepare()
        try:
            before=EA.attempts
            self.assertIsNone(run(B,sims,counts))
            self.assertEqual(EA.attempts,before)
            self.assertEqual(len(undo.attempted_phases),3)
        finally:
            undo()


if __name__=='__main__':
    unittest.main()
