"""M111 offline readback regressions: source EA methods, NOT game success."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'/'m111_bouncer'))
sys.path.insert(0, str(ROOT/'src'/'m57_selection'))
from mhs111_school_job_readback import (
    observe_school_job_memberships, CLASS_PHASES,
)
from mhs57_school_manifest import SchoolManifest


def manifest():
    return SchoolManifest('11',
        [tuple(str(n) for n in range(1,9)),
         tuple(str(n) for n in range(9,17))],
        {}, ('1','9','16'))


class Job(object):
    def __init__(self, guid):
        self.guid64 = guid


class Situation(object):
    def __init__(self, guid, jobs):
        self.guid64 = guid
        self.jobs = jobs
        self.calls = 0

    def get_current_job_for_sim(self, sim):
        self.calls += 1
        result = self.jobs.get(sim.id)
        return Job(result) if result is not None else None


class Sim(object):
    def __init__(self, sid):
        self.id = str(sid)


class Info(object):
    def __init__(self, sid, age='teen', species='human', instantiated=True):
        self.sim_id = int(sid)
        self.age = age
        self.species = species
        self.sim = Sim(sid) if instantiated else None

    def get_sim_instance(self):
        return self.sim


class Manager(object):
    def __init__(self, memberships):
        self.memberships = memberships
        self.calls = 0

    def get_situations_sim_is_in(self, sim):
        self.calls += 1
        return self.memberships.get(sim.id, ())


def setup(phase='lesson', no_trait=()):
    cohort = [Info(i) for i in range(1, 17)]
    memberships = {}
    one_a = Situation(304565 if phase == 'lesson' else 293815, {
        str(i): 277919 for i in range(1, 9) if i not in no_trait})
    one_b = Situation(304703 if phase == 'lesson' else 304701, {
        str(i): 277919 for i in no_trait})
    two = Situation(304567 if phase == 'lesson' else 297774, {
        str(i): 280777 if phase == 'lesson' else 277919
        for i in range(9, 17)})
    for i in range(1, 9):
        memberships[str(i)] = [one_b if i in no_trait else one_a]
    for i in range(9, 17):
        memberships[str(i)] = [two]
    return cohort, Manager(memberships), (one_a, one_b, two)


def read(m, infos=None, manager=None, phase='lesson'):
    if manager is None or infos is None:
        infos,manager,_ = setup(phase)
    return observe_school_job_memberships(m,manager,infos,
                                           'teen','human',phase)


class NativeEAJobReadbackTests(unittest.TestCase):
    def test_six_native_situations_map_to_correct_ea_classes(self):
        self.assertEqual(len(CLASS_PHASES),6)
        self.assertEqual(CLASS_PHASES[293815],('prepare',1,277919))
        self.assertEqual(CLASS_PHASES[297774],('prepare',2,277919))
        self.assertEqual(CLASS_PHASES[304567],('lesson',2,280777))
        self.assertEqual(CLASS_PHASES[304703],('lesson',1,277919))

    def test_all_16_jobs_match_one_phase_but_not_bouncer_or_seating_proof(self):
        infos,manager,situations=setup()
        result=read(manifest(),infos,manager)
        self.assertEqual(result['status'],'SINGLE_PHASE_JOB_MEMBERSHIPS_MATCH_OBSERVED')
        self.assertEqual(result['observed_class_job_ids']['1'],
                         tuple(str(i) for i in range(1,9)))
        self.assertEqual(result['observed_class_job_ids']['2'],
                         tuple(str(i) for i in range(9,17)))
        self.assertEqual(result['enrolled_instantiated_count'],16)
        self.assertFalse(result['post_bouncer_barrier_verified'])
        self.assertFalse(result['exact_16_native_membership_verified'])
        self.assertFalse(result['two_classroom_seating_verified'])
        self.assertEqual(manager.calls,16)

    def test_class1_withtrait_and_notrait_combine_into_one_class(self):
        infos,manager,_=setup(no_trait=(2,4,6))
        result=read(manifest(),infos,manager)
        self.assertEqual(result['status'],'SINGLE_PHASE_JOB_MEMBERSHIPS_MATCH_OBSERVED')
        self.assertEqual(len(result['observed_class_job_ids']['1']),8)

    def test_class_two_preparation_shared_job_is_not_class_one(self):
        infos,manager,_=setup(phase='prepare',no_trait=(1,3))
        result=read(manifest(),infos,manager,'prepare')
        self.assertEqual(result['status'],'SINGLE_PHASE_JOB_MEMBERSHIPS_MATCH_OBSERVED')
        self.assertEqual(result['observed_class_job_ids']['2'],
                         tuple(str(i) for i in range(9,17)))

    def test_wrong_class_placement_detected_even_with_sixteen_on_lot(self):
        infos,manager,situations=setup()
        manager.memberships['2'] = (situations[2],)
        situations[2].jobs['2'] = 280777
        result=read(manifest(),infos,manager)
        self.assertEqual(result['status'],'SINGLE_PHASE_JOB_MEMBERSHIPS_DIFFER')
        self.assertIn(('2',2),result['unexpected_class_memberships'])
        self.assertIn('2',result['missing_current_phase_jobs'][1])

    def test_wrong_student_job_not_silently_accepted(self):
        infos,manager,situations=setup()
        situations[2].jobs['10'] = 277919
        result=read(manifest(),infos,manager)
        self.assertEqual(result['status'],'SINGLE_PHASE_JOB_MEMBERSHIPS_DIFFER')
        self.assertEqual(result['wrong_native_job_guids'][0],
                         ('10',304567,277919,280777))
        self.assertIn('10',result['missing_current_phase_jobs'][2])

    def test_absent_student_extra_npc_pet_and_adult(self):
        infos,manager,_=setup()
        infos[9].sim=None
        infos.extend([Info(999),Info(123,age='adult'),
                      Info(555,species='dog')])
        result=read(manifest(),infos,manager)
        self.assertEqual(result['status'],'SINGLE_PHASE_JOB_MEMBERSHIPS_DIFFER')
        self.assertEqual(result['missing_enrolled_ids'],('10',))
        self.assertEqual(result['extra_instantiated_teen_ids'],('999',))
        self.assertEqual(result['enrolled_instantiated_count'],15)

    def test_membership_unknown_is_fail_closed(self):
        infos,manager,_=setup()
        manager.memberships['3']=None
        result=read(manifest(),infos,manager)
        self.assertEqual(result['status'],'EA_READBACK_INCOMPLETE')
        self.assertIn('EA_SITUATION_GETTER_RETURNED_NONE',
                      result['untrusted_observation_reasons'])

    def test_no_job_getter_never_establishes_assignment(self):
        infos,manager,_=setup()
        class NoJobGetter(object):
            guid64=304565
        manager.memberships['1']=[NoJobGetter()]
        result=read(manifest(),infos,manager)
        self.assertEqual(result['status'],'EA_READBACK_INCOMPLETE')
        self.assertIn('EA_JOB_API_UNAVAILABLE',
                      result['untrusted_observation_reasons'])

    def test_duplicate_alternative_situation_not_counted_twice(self):
        infos,manager,situations=setup()
        situations[1].jobs['4']=277919
        manager.memberships['4']=(situations[0],situations[1])
        result=read(manifest(),infos,manager)
        self.assertEqual(result['status'],'SINGLE_PHASE_JOB_MEMBERSHIPS_DIFFER')
        self.assertEqual(result['duplicate_memberships'],('4',))

    def test_manifest_incomplete_or_missing_getter_never_claims_success(self):
        infos,manager,_=setup()
        bad=SchoolManifest('11',[(str(i) for i in range(1,8)),
             tuple(str(i) for i in range(9,17))],{},())
        self.assertEqual(read(bad,infos,manager)['status'],
                         'ROSTER_NOT_TWO_FULL_CLASSES')
        self.assertEqual(read(manifest(),infos,object())['status'],
                         'EA_SITUATION_MEMBERSHIP_API_UNAVAILABLE')
        self.assertEqual(read(manifest(),infos,manager,'lunch')['status'],
                         'UNVERIFIED_SCHOOL_PHASE')

    def test_no_native_phase_situation_is_not_a_fake_pass(self):
        infos,manager,_=setup()
        manager.memberships={}
        result=read(manifest(),infos,manager)
        self.assertEqual(result['status'],'SINGLE_PHASE_JOB_MEMBERSHIPS_DIFFER')
        self.assertEqual(result['observed_class_job_ids'],{'1':(),'2':()})
        self.assertFalse(result['exact_16_native_membership_verified'])


if __name__=='__main__':
    unittest.main()
