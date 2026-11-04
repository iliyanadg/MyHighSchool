"""M124 original EA school role-state + current interaction readback."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m124_behavior'))
sys.path.insert(0,str(ROOT/'src'/'m122_classrooms'))
from mhs124_lesson_action_readback import inspect_sixteen_lesson_actions

C1=tuple(str(i) for i in range(1,9))
C2=tuple(str(i) for i in range(9,17))


class Job(object):
    def __init__(self,guid):
        self.guid64=guid


class Role(object):
    guid64=177777


class DoingComputer(object):
    pass


class GoToClass(object):
    pass


class Sim(object):
    def __init__(self,sid,has_role=True):
        self.sim_id=sid
        self.age='TEEN'
        self.species='HUMAN'
        self.has_role=has_role
        self.queue=type('Queue',(),{
            'running':DoingComputer() if sid==7 else GoToClass(),
            '_queue':[],
        })()
    def get_sim_instance(self):
        return self


class Infos(object):
    def __init__(self):
        self.sims={i:Sim(i) for i in range(1,17)}
    def get(self,sid):
        return self.sims.get(sid)


class Situation(object):
    def __init__(self,guid):
        self.guid64=guid
    def get_current_job_for_sim(self,sim):
        return Job(277919 if sim.sim_id<=8 else 280777)
    def get_current_role_state_for_sim(self,sim):
        return Role()
    def get_current_role_state_instance_for_sim(self,sim):
        return Role()


class Manager(object):
    def get_situations_sim_is_in(self,sim):
        return (Situation(304565 if sim.sim_id<=8 else 304567),)


class M124ActionEvidenceTests(unittest.TestCase):
    def test_all_sixteen_roles_read_without_falsely_claiming_seating(self):
        r=inspect_sixteen_lesson_actions(
            (C1,C2),Infos(),Manager(),'TEEN','HUMAN')
        self.assertEqual(r['status'],'NATIVE_EA_ACTION_SNAPSHOT_CAPTURED')
        self.assertEqual(len(r['rows']),16)
        self.assertEqual(r['native_correct_class_job_count'],16)
        self.assertFalse(r['lessons_seated_verified'])
        self.assertFalse(r['pushed_interactions'])
        self.assertFalse(r['cancelled_actions'])

    def test_computer_user_keeps_correct_ea_job_but_shows_wrong_action(self):
        r=inspect_sixteen_lesson_actions(
            (C1,C2),Infos(),Manager(),'TEEN','HUMAN')
        row=r['rows'][6]
        self.assertEqual(row['sim_id'],'7')
        self.assertIn('DoingComputer',row['running_interaction'])
        self.assertEqual(row['state'],
                         'NATIVE_LESSON_JOB_ASSIGNED_ACTION_UNVERIFIED')
        self.assertEqual(row['native_role_states'][0][0],177777)

    def test_invalid_roster_is_blocked_without_touching_ea(self):
        r=inspect_sixteen_lesson_actions(
            (C1,C1),Infos(),Manager(),'TEEN','HUMAN')
        self.assertEqual(r['status'],'INVALID_ROSTER')
        self.assertEqual(r['rows'],())

    def test_missing_role_state_methods_fail_closed(self):
        class NoRole(object):
            guid64=304565
            def get_current_job_for_sim(self,sim):
                return Job(277919)
        class BrokenManager(object):
            def get_situations_sim_is_in(self,sim):
                return (NoRole(),)
        r=inspect_sixteen_lesson_actions(
            (C1,C2),Infos(),BrokenManager(),'TEEN','HUMAN')
        self.assertEqual(len(r['rows']),16)
        self.assertTrue(all(x['state']=='EA_ROLE_API_UNAVAILABLE'
                            for x in r['rows']))
        self.assertFalse(r['lessons_seated_verified'])

    def test_no_original_native_lecture_is_not_a_seated_student(self):
        class NoLesson(object):
            def get_situations_sim_is_in(self,sim):
                return ()
        r=inspect_sixteen_lesson_actions(
            (C1,C2),Infos(),NoLesson(),'TEEN','HUMAN')
        self.assertEqual(r['native_correct_class_job_count'],0)
        self.assertFalse(r['lessons_seated_verified'])


if __name__=='__main__':
    unittest.main()
