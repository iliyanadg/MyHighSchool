"""M114: combine exact native EA Base/Core guest tickets, Bouncer scope and
random replacement blocking, with M109 descriptor-level rollback. OFFLINE.
"""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))
sys.path.insert(0,str(ROOT/'src'/'m109_activation'))
sys.path.insert(0,str(ROOT/'src'/'m113_controller'))
sys.path.insert(0,str(ROOT/'src'/'m114_bouncer'))

from tests.test_m108_native_invitation import (
    session, EAList, CONTEXT, CORE_JOBS, BASE_SITUATION, CORE_SITUATION,
)
from tests.test_m108_school_filter_scope import (
    Request, ORIGINAL, BLANK, Job, SchoolBase, SchoolCore, OtherSituation,
    Info, BASE_CONTEXT, proofs as filter_proofs, BASE_JOB,
)
from tests.test_m108_no_show_guard import guard_proofs
from mhs114_school_bouncer_pair import (
    build_school_bouncer_pair, compose_m113_late_graph,
)
from mhs113_early_school_entry import LATE_STAGES


def native_request_owner():
    def constructor(self,*args,**kwargs):
        return Request.__init__(self,*args,**kwargs)
    def additional_terms(self):
        return Request.get_additional_filter_terms(self)
    def clone(self,only_if_explicit=False):
        return {'requested_sim_id':0,
                'original_sim_id':self._requested_sim_id,
                'only_if_explicit':only_if_explicit}
    owner=type('BouncerRequest',(Request,),{
        '__init__':constructor,
        'get_additional_filter_terms':additional_terms,
        'clone_for_replace':clone,
    })
    owner.__module__='situations.bouncer.bouncer_request'
    return owner


def native_pair(owner=None,invites=True):
    owner=owner or native_request_owner()
    prepared=session()
    if invites:
        assert prepared.preview(BASE_SITUATION,EAList(),CONTEXT)[0]=='base:5'
        assert prepared.preview(CORE_SITUATION,EAList(),CONTEXT)[0]=='core'
    sim_infos={n:Info(n,selectable=n in (1,9,16))
               for n in range(1,17)}
    context=dict(BASE_CONTEXT)
    pair,reason=build_school_bouncer_pair(
        prepared,owner,BLANK,'TEEN','HUMAN',
        sim_infos.get,lambda:context)
    return pair,reason,owner,prepared,context


class NativeSchoolBouncerPairTests(unittest.TestCase):
    def test_real_class_identity_and_methods_required(self):
        pair,reason,owner,prepared,context=native_pair()
        self.assertIsNotNone(pair)
        self.assertFalse(pair.snapshot()['game_bouncer_modified'])
        self.assertFalse(pair.snapshot()['native_student_role_assignment_verified'])
        fake=native_request_owner()
        fake.__module__='third_party.mod'
        self.assertIsNone(native_pair(fake)[0])
        incomplete=type('BouncerRequest',(Request,),{
            '__init__':lambda self,*a,**kw:Request.__init__(self,*a,**kw),
            'get_additional_filter_terms':
                lambda self:Request.get_additional_filter_terms(self),
        })
        incomplete.__module__='situations.bouncer.bouncer_request'
        self.assertIsNone(native_pair(incomplete)[0])

    def test_missing_invitations_and_eligibility_proof_do_not_patch(self):
        pair,_,owner,prepared,_=native_pair(invites=False)
        self.assertIsNotNone(pair)
        proof=filter_proofs()
        proof['exact_student_invitation_prepared_before_ea']=False
        self.assertIsNone(pair.stage_graph(proof,guard_proofs()))
        original=owner.__dict__['__init__']
        self.assertIs(owner.__dict__['__init__'],original)
        accepted=owner(SchoolBase(),Job(BASE_JOB),5)
        self.assertIs(accepted._sim_filter,ORIGINAL)

    def test_all_stages_rollback_and_exact_invited_students_only(self):
        pair,_,owner,prepared,context=native_pair()
        originals={m:owner.__dict__[m] for m in (
            '__init__','get_additional_filter_terms','clone_for_replace')}
        graph=pair.stage_graph(filter_proofs(),guard_proofs())
        self.assertEqual(set(graph),{'school_filter_scope','no_show_guard'})
        self.assertTrue(graph['school_filter_scope']['install'](None,None))
        self.assertTrue(graph['no_show_guard']['install'](None,None))
        try:
            base=owner(SchoolBase(),Job(BASE_JOB),5)
            uninvited=owner(SchoolBase(),Job(BASE_JOB),6)
            core=owner(SchoolCore(),Job(CORE_JOBS[0]),2)
            wrong_core=owner(SchoolCore(),Job(CORE_JOBS[0]),3)
            teacher=owner(SchoolCore(),Job(277895),8)
            outsider=owner(OtherSituation(),Job(BASE_JOB),5)
            self.assertIs(base._sim_filter,BLANK)
            self.assertIs(core._sim_filter,BLANK)
            for obj in (uninvited,wrong_core,teacher,outsider):
                self.assertIs(obj._sim_filter,ORIGINAL)
                self.assertEqual(obj.get_additional_filter_terms(),
                                 ('keep-EA-terms',))
                self.assertEqual(obj.clone_for_replace()['requested_sim_id'],0)
            self.assertEqual(base.get_additional_filter_terms(),())
            self.assertIsNone(base.clone_for_replace(only_if_explicit=True))
            self.assertIsNone(core.clone_for_replace())
            self.assertEqual(pair.guard.snapshot()[
                'suppressed_random_student_clones'],2)
            self.assertEqual(pair.scope.snapshot()['tracked_requests'],2)
        finally:
            self.assertTrue(graph['no_show_guard']['restore']())
            self.assertTrue(graph['school_filter_scope']['restore']())
        for method in originals:
            self.assertIs(owner.__dict__[method],originals[method])
        self.assertEqual(pair.scope.snapshot()['tracked_requests'],0)

    def test_cancelled_guest_ends_request_scope(self):
        pair,_,owner,prepared,context=native_pair()
        graph=pair.stage_graph(filter_proofs(),guard_proofs())
        self.assertTrue(graph['school_filter_scope']['install'](None,None))
        self.assertTrue(graph['no_show_guard']['install'](None,None))
        try:
            req=owner(SchoolBase(),Job(BASE_JOB),5)
            self.assertIs(req._sim_filter,BLANK)
            self.assertTrue(prepared.cancel('base:5'))
            self.assertEqual(req.get_additional_filter_terms(),
                             ('keep-EA-terms',))
            self.assertIs(req._sim_filter,ORIGINAL)
            self.assertEqual(req.clone_for_replace()['requested_sim_id'],0)
        finally:
            self.assertTrue(graph['no_show_guard']['restore']())
            self.assertTrue(graph['school_filter_scope']['restore']())

    def test_invitation_creation_receipt_remains_valid_after_pending(self):
        pair,_,owner,prepared,context=native_pair()
        graph=pair.stage_graph(filter_proofs(),guard_proofs())
        self.assertTrue(graph['school_filter_scope']['install'](None,None))
        self.assertTrue(graph['no_show_guard']['install'](None,None))
        try:
            self.assertTrue(prepared.acknowledge_created('base:5',123))
            req=owner(SchoolBase(),Job(BASE_JOB),5)
            self.assertIs(req._sim_filter,BLANK)
            self.assertIsNone(req.clone_for_replace())
            self.assertFalse(prepared.snapshot()['attendance_verified'])
        finally:
            self.assertTrue(graph['no_show_guard']['restore']())
            self.assertTrue(graph['school_filter_scope']['restore']())

    def test_merge_requires_all_three_other_real_stages(self):
        pair,_,owner,prepared,context=native_pair()
        bouncer=pair.stage_graph(filter_proofs(),guard_proofs())
        self.assertIsNone(compose_m113_late_graph({},bouncer))
        other={key:{'install':lambda m,e:True,'restore':lambda:True}
               for key in ('native_precreate','unified_lessons',
                           'post_bouncer_observer')}
        merged=compose_m113_late_graph(other,bouncer)
        self.assertEqual(set(merged),set(LATE_STAGES))
        self.assertIsNone(compose_m113_late_graph(
            dict(other,unexpected={'install':lambda m,e:True,
                                  'restore':lambda:True}),bouncer))


if __name__=='__main__':
    unittest.main()
