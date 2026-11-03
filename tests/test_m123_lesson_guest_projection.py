"""M123 school lesson guest projection: 2x8, Core unchanged, safety."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m123_class_repair'))
from mhs123_lesson_guest_projection import (
    project_original_lesson_guests,LESSON_JOBS
)
from tests.test_m119_one_base_live_trial import (
    GuestList,Guest,GuestInfo,Job
)

GROUPS=(tuple(str(i) for i in range(1,9)),
        tuple(str(i) for i in range(9,17)))
JOBS={277919:Job(277919),280777:Job(280777)}


class LessonGuestProjectionTests(unittest.TestCase):
    def test_class1_two_native_variants_share_same_eight_students(self):
        for situation in (304565,304703):
            original=GuestList()
            original.add_guest_info(Guest(5555,Job(277918)))
            original.add_guest_info(Guest(999,Job(277919)))
            new,reason=project_original_lesson_guests(
                situation,original,GROUPS,JOBS,GuestInfo,'INVITED',set())
            self.assertEqual(reason,
                'EIGHT_EXACT_REGISTERED_LESSON_GUESTS_PROJECTED')
            guests=tuple(new.guest_info_gen())
            self.assertEqual([x.sim_id for x in guests[1:]],
                             list(range(1,9)))
            self.assertEqual(guests[0].sim_id,5555)
            self.assertEqual(len(tuple(original.guest_info_gen())),2)

    def test_class2_eight_original_students_and_staff_survive(self):
        original=GuestList()
        original.add_guest_info(Guest(2222,Job(277918)))
        original.add_guest_info(Guest(3333,Job(278224)))
        original.add_guest_info(Guest(999,Job(280777)))
        new,reason=project_original_lesson_guests(
            304567,original,GROUPS,JOBS,GuestInfo,'INVITED',set())
        self.assertIsNotNone(new)
        self.assertEqual([x.sim_id for x in new.guest_info_gen()],
                         [2222,3333]+list(range(9,17)))

    def test_second_class1_native_branch_cannot_duplicate_class(self):
        value,reason=project_original_lesson_guests(
            304703,GuestList(),GROUPS,JOBS,GuestInfo,'INVITED',{1})
        self.assertIsNone(value)
        self.assertEqual(reason,'CLASS_ALREADY_ATTEMPTED')

    def test_unknown_jobs_not_silently_dropped(self):
        original=GuestList()
        original.add_guest_info(Guest(1,Job(987654)))
        value,reason=project_original_lesson_guests(
            304565,original,GROUPS,JOBS,GuestInfo,'INVITED',set())
        self.assertIsNone(value)
        self.assertEqual(reason,'UNRECOGNISED_EA_JOB_PRESERVE_VANILLA')

    def test_staff_occupying_student_registry_id_blocks(self):
        original=GuestList()
        original.add_guest_info(Guest(3,Job(277918)))
        value,reason=project_original_lesson_guests(
            304565,original,GROUPS,JOBS,GuestInfo,'INVITED',set())
        self.assertIsNone(value)
        self.assertEqual(reason,'STAFF_GUEST_AMBIGUOUS')

    def test_missing_natively_resolved_job_blocks(self):
        value,reason=project_original_lesson_guests(
            304565,GuestList(),GROUPS,{},GuestInfo,'INVITED',set())
        self.assertIsNone(value)
        self.assertEqual(reason,'EA_LESSON_JOB_NOT_FOUND')

    def test_no_registry_duplication_allowed(self):
        invalid=(tuple(str(i) for i in range(1,9)),)*2
        value,reason=project_original_lesson_guests(
            304565,GuestList(),invalid,JOBS,GuestInfo,'INVITED',set())
        self.assertIsNone(value)
        self.assertEqual(reason,'REGISTRY_2X8_INVALID')

    def test_same_original_guest_list_never_mutated(self):
        original=GuestList()
        old=Guest(999,Job(277919))
        original.add_guest_info(old)
        new,reason=project_original_lesson_guests(
            304565,original,GROUPS,JOBS,GuestInfo,'INVITED',set())
        self.assertIsNot(new,original)
        self.assertEqual(list(original.guest_info_gen()),[old])
        self.assertEqual(len(list(new.guest_info_gen())),8)


if __name__=='__main__':
    unittest.main()
