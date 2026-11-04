"""M108 single native EA try_start wrapper — OFFLINE unit integration.

Read against original EA tuning IDs. The fake native situation manager in
these tests does not prove the TS4 engine accepts the Class1 shadow metaclass.
"""
import sys
import unittest
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace as Namespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))

from mhs108_unified_lessons import (
    REQUIRED_LIVE_GATES, install_offline_only)
from mhs108_post_bouncer_audit import NativeJobAudit
from mhs108_class1_dual_route_budget import PHASES
from tests.test_m108_class1_dual_route_budget import (
    coordinator as class1_coordinator)
from tests.test_m108_class1_shadow_cap import original_class
from tests.test_m108_native_invitation import (
    prepare_fixed_manifest, CLASSES, CORE)

STUDENTS = CLASSES[0] + CLASSES[1]
PLAYERS = ('1', '9', '16')


class Ref(object):
    def __init__(self, guid):
        self.guid64 = guid


class Sim(object):
    def __init__(self, sid):
        self.sim_id = int(sid)
    def __hash__(self):
        return self.sim_id
    def __eq__(self, other):
        return isinstance(other, Sim) and other.sim_id == self.sim_id


class NativeTest(object):
    def __init__(self, ids):
        self.ids = frozenset(str(i) for i in ids)
    def run_tests(self, sim):
        return str(sim.sim_id) in self.ids


def proofs():
    # Synthetic test ONLY, no source of these flags in the installed mod.
    return {k: True for k in REQUIRED_LIVE_GATES}


def fixture(phase='lesson', native_staff_ok=True, bad_receipt=False,
            partial=False, deferred=False):
    class EA(object):
        attempts = 0
        receipts = {}
        native_taken = []
        next_situation = 700
        @classmethod
        def try_start(cls, sims, sim_info, duration, additional_ids, counts):
            EA.attempts += 1
            chosen = {}
            already = set()
            for job_entry in cls.job_assignments:
                job = job_entry.job
                cap = job_entry.sim_count.upper_bound
                for mod in job_entry.upper_bound_count_modifiers:
                    cap -= counts[(mod.situation, mod.job)]
                if cap < 1:
                    continue
                matching = sorted(
                    (sim for sim in sims if sim not in already
                     and job_entry.tests.run_tests(sim)), key=lambda s:s.sim_id)
                matching = matching[:min(1, cap) if partial else cap]
                if matching:
                    chosen[job.guid64] = tuple(s.sim_id for s in matching)
                    already.update(matching)
            if not chosen:
                return None
            EA.next_situation += 1
            situation_id = EA.next_situation
            EA.native_taken.append((cls.guid64, situation_id, chosen))
            shown_jobs = chosen
            if bad_receipt == 'extra':
                shown_jobs = {k:(v + (999,) if k in (277919,280777) else v)
                              for k,v in chosen.items()}
            elif bad_receipt == 'swapped' and 277918 in chosen:
                student_job = 280777 if 280777 in chosen else 277919
                shown_jobs = dict(chosen)
                students = list(shown_jobs[student_job])
                teachers = list(shown_jobs[277918])
                students[0], teachers[0] = teachers[0], students[0]
                shown_jobs[student_job] = tuple(students)
                shown_jobs[277918] = tuple(teachers)
            EA.receipts[situation_id] = {
                'native_ea_guest_list_inspected': True,
                'situation_id': situation_id,
                'ids_by_job': shown_jobs}
            sims.difference_update(already)
            for job_entry in cls.job_assignments:
                counts[(cls.situation, job_entry.job)] += len(
                    chosen.get(job_entry.job.guid64, ()))
            return situation_id

    references = {}
    def same(obj):
        return references.setdefault(obj.guid64, obj)

    stage = PHASES[phase]
    def branch(route):
        original = original_class(phase=phase, route=route)
        attrs = {}
        for name in ('guid64','situation','job_assignments','user_facing',
                     'default_job_order','default_met_minimum_jobs',
                     'default_need_minimum_jobs'):
            attrs[name] = getattr(original,name)
        result = type('NativeClass1' + route, (EA,), attrs)
        entry = result.job_assignments[0]
        entry.job = same(entry.job)
        result.situation = same(result.situation)
        for modifier in entry.upper_bound_count_modifiers:
            modifier.job = same(modifier.job)
            modifier.situation = same(modifier.situation)
        entry.tests = NativeTest(('2','3') if route == 'with_trait'
                                 else ('4','5','6','7','8'))
        result.default_job_order = [entry.job]
        result.default_met_minimum_jobs = {entry.job:entry}
        return result

    WithTrait, NoTrait = branch('with_trait'), branch('no_trait')
    info = {304570:(304567,[(280777,8,('10','11','12','13','14','15')),
                              (277918,2,('200','201')),
                              (278224,1,('202',))]),
            297773:(297774,[(277919,8,('10','11','12','13','14','15')),
                              (277918,2,('200','201'))])}
    cls_id = 304570 if phase=='lesson' else 297773
    situation_guid, specs = info[cls_id]
    entries = []
    for job_id, upper, test_ids in specs:
        entries.append(Namespace(job=same(Ref(job_id)),
            sim_count=Namespace(lower_bound=0, upper_bound=upper),
            tests=NativeTest(test_ids), upper_bound_count_modifiers=()))
    Others=type('EAClass2Others',(EA,),{
        'guid64':cls_id,'situation':same(Ref(situation_guid)),
        'job_assignments':tuple(entries)})

    m=prepare_fixed_manifest(CLASSES, PLAYERS, CORE, 11, 12, 777)
    budget=class1_coordinator(phase=phase, clock=('10:00' if phase=='lesson'
                                                   else '09:30'))
    native_counts=defaultdict(int)
    modifier=WithTrait.job_assignments[0].upper_bound_count_modifiers[0]
    native_counts[(modifier.situation,modifier.job)]=3
    on_lot=STUDENTS+('200','201','202','999')
    all_staff={277918:('200','201')}
    if phase=='lesson':
        all_staff[278224]=('202',)

    def context(cls):
        data_guid=cls.guid64
        if data_guid==WithTrait.guid64:
            eligible=('2','3')
            after=2
        elif data_guid==NoTrait.guid64:
            eligible=('4','5','6','7','8')
            after=5
        else:
            eligible=('10','11','12','13','14','15')
            after=None
        return {
            'mhs_unified_school_active':True,
            'mhs_class1_dual_route_active':True,
            'native_school_phase_origin_verified':True,
            'verified_ea_phase_origin':True,
            'verified_school_zone':True,
            'ea_job_counts_verified':True,
            'ea_route_test_results_verified':True,
            'native_ea_candidate_set_verified':True,
            'ea_job_counts_verified':True,
            'ea_route_test_results_verified':True,
            'verified_staff_jobs':native_staff_ok,
            'native_job_layout_verified':True,
            'verified_staff_by_job':all_staff,
            'expected_native_class1_job_count_after':after,
            'schedule_guid':277657,'save_slot':'11','sim_day':12,
            'zone_id':'777','time_window':('10:00' if phase=='lesson'
                                          else '09:30'),
            'observed_on_lot':on_lot,
            'observed_ea_school_members':STUDENTS,
            'verified_native_eligible_ids':eligible,
        }
    deferred_audit = NativeJobAudit(m) if deferred else None
    undo = install_offline_only(
        EA,m,context,lambda cls, ctx:budget,
        lambda cls,situation_id,ctx:EA.receipts[situation_id],
        proofs(), deferred_native_audit=deferred_audit)
    assert callable(undo)
    sims=set(Sim(sid) for sid in on_lot)
    return EA,WithTrait,NoTrait,Others,budget,native_counts,sims,undo


def run(cls, sims, counts):
    return cls.try_start(sims,None,'EA_ORIGINAL_DURATION',(),counts)


class UnifiedLessonsTests(unittest.TestCase):
    def test_unverified_live_gate_never_installs_hook(self):
        for gate in REQUIRED_LIVE_GATES:
            class EA(object):
                @classmethod
                def try_start(cls,*args):
                    return 8
            p=proofs()
            p[gate]=False
            self.assertIsNone(install_offline_only(
                EA,{},lambda cls:{},lambda cls,ctx:None,
                lambda cls,id,ctx:{},p))
            self.assertEqual(EA.try_start(),8)

    def test_two_classrooms_13_exact_npcs_and_original_staff(self):
        EA,A1,A2,B,budget,counts,sims,undo=fixture()
        try:
            before=set(sims)
            self.assertIsNotNone(run(B,sims,counts))
            self.assertIsNotNone(run(A1,sims,counts))
            self.assertIsNotNone(run(A2,sims,counts))
            self.assertEqual(EA.attempts,3)
            self.assertEqual([v[0] for v in EA.native_taken],
                             [304570,304563,304561])
            self.assertEqual(
                set(v for entry in EA.native_taken for ids in
                    entry[2].values() for v in ids),
                {2,3,4,5,6,7,8,10,11,12,13,14,15,200,201,202})
            self.assertEqual(len(sims),len(before)-16)
            self.assertNotIn(Sim(200),sims)
            self.assertIn(Sim(999),sims)
            self.assertTrue(budget.snapshot()['phase_plan_complete_offline'])
            self.assertEqual(A1.job_assignments[0].sim_count.upper_bound,6)
            self.assertEqual(A2.job_assignments[0].sim_count.upper_bound,6)
            self.assertEqual(len(undo.blocked_receipts),0)
        finally:
            self.assertTrue(undo())

    def test_both_classes_prepare_keep_staff_and_same_class_roster(self):
        EA,A1,A2,B,budget,counts,sims,undo=fixture(phase='prepare')
        try:
            self.assertIsNotNone(run(A1,sims,counts))
            self.assertIsNotNone(run(B,sims,counts))
            self.assertIsNotNone(run(A2,sims,counts))
            self.assertEqual(EA.attempts,3)
            self.assertEqual(
                set(s.sim_id for s in sims),{1,9,16,202,999})
            self.assertTrue(budget.snapshot()['phase_plan_complete_offline'])
        finally:
            undo()

    def test_wrong_staff_evidence_blocks_others_before_ea(self):
        EA,A1,A2,B,budget,counts,sims,undo=fixture(native_staff_ok=False)
        try:
            before=set(sims)
            self.assertIsNone(run(B,sims,counts))
            self.assertEqual(EA.attempts,0)
            self.assertEqual(sims,before)
        finally:
            undo()

    def test_bad_post_native_guest_job_receipt_does_not_claim_class(self):
        EA,A1,A2,B,budget,counts,sims,undo=fixture(bad_receipt='extra')
        try:
            before=set(sims)
            self.assertIsNotNone(run(B,sims,counts))
            self.assertEqual(sims,before)
            self.assertEqual(len(undo.blocked_receipts),1)
            self.assertEqual(undo.blocked_receipts[0][0],304570)
            self.assertIsNotNone(run(A1,sims,counts))
            self.assertTrue(budget.snapshot()['blocked'])
            self.assertFalse(budget.snapshot()['phase_plan_complete_offline'])
        finally:
            undo()

    def test_same_ids_in_wrong_ea_jobs_are_rejected(self):
        # A matching total of present Sims is NOT proof of right roles:
        # swapping one student and teacher must reject the native receipt.
        EA,A1,A2,B,budget,counts,sims,undo=fixture(bad_receipt='swapped')
        try:
            previous=set(sims)
            self.assertIsNotNone(run(B,sims,counts))
            self.assertEqual(sims,previous)
            self.assertEqual(len(undo.blocked_receipts),1)
            self.assertEqual(EA.attempts,1)
        finally:
            undo()

    def test_native_class2_cannot_be_recreated_same_save_day_window(self):
        EA,A1,A2,B,budget,counts,sims,undo=fixture()
        try:
            self.assertIsNotNone(run(B,sims,counts))
            prior_attempts=EA.attempts
            self.assertIsNone(run(B,sims,counts))
            self.assertEqual(EA.attempts,prior_attempts)
            self.assertEqual(len(undo.attempted_phases),1)
        finally:
            undo()

    def test_failed_native_phase_is_not_retried(self):
        EA,A1,A2,B,budget,counts,sims,undo=fixture(partial=True)
        try:
            self.assertIsNotNone(run(B,sims,counts))
            self.assertIsNone(run(B,sims,counts))
            self.assertEqual(EA.attempts,1)
            self.assertEqual(len(undo.blocked_receipts),1)
        finally:
            undo()

    def test_partial_native_assignment_does_not_modify_shared_set(self):
        EA,A1,A2,B,budget,counts,sims,undo=fixture(partial=True)
        try:
            old=set(sims)
            self.assertIsNotNone(run(A1,sims,counts))
            self.assertEqual(sims,old)
            self.assertEqual(len(undo.blocked_receipts),1)
            self.assertTrue(budget.snapshot()['blocked'])
            self.assertIsNone(run(A2,sims,counts))
            self.assertEqual(EA.attempts,1)
        finally:
            undo()

    def test_generic_legacy_controller_does_not_stack(self):
        from mhs108_ea_phase_adapter import (
            install_offline_only as install_old,
            REQUIRED_LIVE_GATES as OLD_PROOFS)
        EA,A1,A2,B,budget,counts,sims,undo=fixture()
        try:
            self.assertIsNone(install_old(
                EA,{},lambda cls:{},
                {k:True for k in OLD_PROOFS}))
            self.assertIsNone(install_offline_only(
                EA,{},lambda cls:{},lambda cls,c:None,
                lambda cls,id,c:{},proofs()))
        finally:
            undo()

    def test_unrelated_ea_situation_and_inactive_mod_are_unmodified(self):
        EA,A1,A2,B,budget,counts,sims,undo=fixture()
        class Other(EA):
            guid64=12345
            job_assignments=A1.job_assignments
            situation=A1.situation
        try:
            old=set(sims)
            self.assertIsNotNone(run(Other,sims,counts))
            self.assertNotEqual(sims,old)
        finally:
            self.assertTrue(undo())


if __name__=='__main__':
    unittest.main()
