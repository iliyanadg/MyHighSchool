"""M105 require 16 physically present before 8+8 EA lesson validation."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m105_day_controller'))
from mhs105_lesson_gate import assess_lesson_phase

A=tuple(str(i) for i in range(1,9))
B=tuple(str(i) for i in range(9,17))
EVERYONE=A+B

class EAClassPhaseTests(unittest.TestCase):
    def test_missing_students_cannot_be_seated_by_schedule(self):
        result=assess_lesson_phase((A,B),EVERYONE[:-1],EVERYONE[:-1])
        self.assertEqual(result['status'],'INSUFFICIENT_PHYSICAL_ATTENDANCE')
        self.assertEqual(result['registered_on_lot'],15)
        self.assertFalse(result['eight_plus_eight_class_jobs_verified'])

    def test_random_ea_extras_preclude_clean_16_day(self):
        result=assess_lesson_phase((A,B),EVERYONE,EVERYONE+('99',))
        self.assertEqual(result['status'],'UNREGISTERED_EA_STUDENTS')
        self.assertEqual(result['extra_count'],1)
        self.assertFalse(result['ea_school_membership_verified'])

    def test_active_ea_school_roles_must_cover_all_16(self):
        result=assess_lesson_phase((A,B),EVERYONE,EVERYONE[:-1])
        self.assertEqual(result['status'],'SCHOOL_ROLE_MISSING')
        self.assertFalse(result['ea_school_membership_verified'])

    def test_on_lot_and_in_school_is_not_classroom_or_seating_proof(self):
        result=assess_lesson_phase((A,B),EVERYONE,EVERYONE)
        self.assertEqual(result['status'],'PHYSICALLY_PRESENT_NOT_CLASS_VERIFIED')
        self.assertTrue(result['actual_students_present'])
        self.assertTrue(result['ea_school_membership_verified'])
        self.assertFalse(result['eight_plus_eight_class_jobs_verified'])
        self.assertFalse(result['seated_correctly_verified'])

    def test_two_ea_class_jobs_exact_but_seating_unknown(self):
        result=assess_lesson_phase((A,B),EVERYONE,EVERYONE,
                                   observed_ea_class_members=(A,B))
        self.assertEqual(result['status'],'EA_CLASSES_VERIFIED_NOT_SEATED')
        self.assertTrue(result['eight_plus_eight_class_jobs_verified'])
        self.assertFalse(result['seated_correctly_verified'])

    def test_wrong_or_swapped_lecture_aulas_not_verified(self):
        result=assess_lesson_phase((A,B),EVERYONE,EVERYONE,
                                   observed_ea_class_members=(B,A))
        self.assertEqual(result['status'],'WRONG_EA_CLASS_ASSIGNMENT')
        self.assertEqual(result['class1_verified'],0)
        self.assertEqual(result['class2_verified'],0)
        self.assertFalse(result['eight_plus_eight_class_jobs_verified'])

    def test_exact_16_roles_8_each_and_sitting_confirmed(self):
        result=assess_lesson_phase(
            (A,B),EVERYONE,EVERYONE,
            observed_ea_class_members=(A,B),
            observed_sitting_by_class=(A,B))
        self.assertEqual(result['status'],
                         'SCHOOL_DAY_16_8_8_SEATED_VERIFIED')
        self.assertTrue(result['seated_correctly_verified'])
        self.assertFalse(result['game_modified'])

    def test_sim_registration_without_real_observation_is_not_proof(self):
        self.assertEqual(assess_lesson_phase(
            (A,B),None,None)['status'],'UNKNOWN')
        self.assertEqual(assess_lesson_phase(
            (A,A),EVERYONE,EVERYONE)['status'],'BLOCKED')

if __name__=='__main__':
    unittest.main()
