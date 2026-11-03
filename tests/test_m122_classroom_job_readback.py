"""M122: original EA Class 1 dual path / Class 2 lesson job readback."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m122_classrooms'))
from mhs122_classroom_job_readback import school_classroom_snapshot


CLASS1=tuple(str(i) for i in range(1,9))
CLASS2=tuple(str(i) for i in range(9,17))
PLAY=('1','9','16')


class Job(object):
    def __init__(self,guid):
        self.guid64=guid


class Situation(object):
    def __init__(self,guid,assigned):
        self.guid64=guid
        self.assigned=assigned
    def get_current_job_for_sim(self,sim):
        return Job(self.assigned)


class Info(object):
    age='TEEN'
    species='HUMAN'
    def __init__(self,sid,instanced=True):
        self.sim_id=int(sid)
        self.instanced=instanced
    def get_sim_instance(self):
        return self if self.instanced else None


class SimManager(object):
    def __init__(self,instanced=True):
        self.infos={int(s):Info(s,instanced) for s in CLASS1+CLASS2}
    def get(self,sid):
        return self.infos.get(sid)
    def get_all(self):
        return tuple(self.infos.values())


class SituationManager(object):
    def __init__(self,wrong=None):
        self.wrong=wrong or {}
    def get_situations_sim_is_in(self,info):
        sid=info.sim_id
        if sid<=8:
            kind=304565 if sid%2 else 304703
            job=277919
        else:
            kind=304567
            job=280777
        if sid in self.wrong:
            kind,job=self.wrong[sid]
        return (Situation(kind,job),)


class NativeTwoClassSnapshotTests(unittest.TestCase):
    def test_exact_sixteen_members_in_native_school_jobs(self):
        r=school_classroom_snapshot(
            (CLASS1,CLASS2),PLAY,SimManager(),SituationManager(),
            'TEEN','HUMAN','lesson')
        self.assertEqual(r['status'],'TWO_NATIVE_CLASS_JOB_SETS_MATCH_OBSERVED')
        self.assertTrue(r['exact_two_class_jobs_verified'])
        self.assertEqual(r['native_class1_job_count'],8)
        self.assertEqual(r['native_class2_job_count'],8)
        self.assertTrue(r['all_playable_instances_verified'])
        self.assertFalse(r['two_classroom_seating_verified'])

    def test_detect_student_who_enters_wrong_EA_class(self):
        r=school_classroom_snapshot(
            (CLASS1,CLASS2),PLAY,SimManager(),
            SituationManager({2:(304567,280777)}),
            'TEEN','HUMAN','lesson')
        self.assertEqual(r['status'],'NATIVE_CLASSROOM_JOB_MEMBERSHIPS_DIFFER')
        self.assertEqual(r['native_class1_job_count'],7)
        self.assertEqual(r['native_class2_job_count'],9)
        self.assertIn(('2',2),r['wrong_class_memberships'])

    def test_wrong_job_guid_cannot_look_like_correct_class(self):
        r=school_classroom_snapshot(
            (CLASS1,CLASS2),PLAY,SimManager(),
            SituationManager({4:(304565,280777)}),
            'TEEN','HUMAN','lesson')
        self.assertEqual(r['status'],'NATIVE_CLASSROOM_JOB_MEMBERSHIPS_DIFFER')
        self.assertIn('4',r['missing_class1_job_ids'])
        self.assertEqual(len(r['wrong_native_job_guids']),1)

    def test_missing_playable_sim_is_not_faked_by_roster(self):
        sims=SimManager()
        sims.infos[9].instanced=False
        r=school_classroom_snapshot(
            (CLASS1,CLASS2),PLAY,sims,SituationManager(),
            'TEEN','HUMAN','lesson')
        self.assertEqual(r['enrolled_instanced_count'],15)
        self.assertEqual(len(r['playable_instanced_ids']),2)
        self.assertFalse(r['all_playable_instances_verified'])
        self.assertFalse(r['exact_two_class_jobs_verified'])

    def test_duplicate_registration_blocks_everything(self):
        r=school_classroom_snapshot(
            (CLASS1,CLASS1),PLAY,SimManager(),SituationManager(),
            'TEEN','HUMAN','lesson')
        self.assertEqual(r['status'],'ROSTER_OR_PHASE_INVALID')

    def test_native_preparation_is_distinct_from_lesson(self):
        class PreparationSituationManager(object):
            def get_situations_sim_is_in(self,info):
                sid=info.sim_id
                kind=(293815 if sid%2 else 304701) if sid<=8 else 297774
                return (Situation(kind,277919),)
        r=school_classroom_snapshot(
            (CLASS1,CLASS2),PLAY,SimManager(),
            PreparationSituationManager(),'TEEN','HUMAN','prepare')
        self.assertEqual(r['status'],'TWO_NATIVE_CLASS_JOB_SETS_MATCH_OBSERVED')
        r2=school_classroom_snapshot(
            (CLASS1,CLASS2),PLAY,SimManager(),
            PreparationSituationManager(),'TEEN','HUMAN','lesson')
        self.assertEqual(r2['status'],'NATIVE_CLASSROOM_JOB_MEMBERSHIPS_DIFFER')

    def test_random_extra_student_in_ea_class_is_never_exact(self):
        infos=SimManager()
        infos.infos[999]=Info(999)
        r=school_classroom_snapshot(
            (CLASS1,CLASS2),PLAY,infos,
            SituationManager(),'TEEN','HUMAN','lesson')
        self.assertFalse(r['exact_two_class_jobs_verified'])
        self.assertEqual(r['status'],
                         'NATIVE_CLASSROOM_JOB_MEMBERSHIPS_DIFFER')
        self.assertTrue(r['extra_nonregistered_native_class_memberships'])

    def test_unknown_all_teen_source_cannot_claim_exact_class_sizes(self):
        infos=SimManager()
        infos.get_all=None
        r=school_classroom_snapshot(
            (CLASS1,CLASS2),PLAY,infos,
            SituationManager(),'TEEN','HUMAN','lesson')
        self.assertEqual(r['status'],'NATIVE_EA_CLASS_JOB_READ_INCOMPLETE')
        self.assertTrue(r['nonregistered_teen_scan_incomplete'])
        self.assertFalse(r['exact_two_class_jobs_verified'])

    def test_missing_ea_member_api_blocks(self):
        r=school_classroom_snapshot(
            (CLASS1,CLASS2),PLAY,SimManager(),object(),
            'TEEN','HUMAN','lesson')
        self.assertEqual(r['status'],'EA_NATIVE_MEMBERSHIP_API_UNAVAILABLE')


if __name__=='__main__':
    unittest.main()
