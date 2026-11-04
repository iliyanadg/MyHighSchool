"""M108 disabled original EA WeeklyScheduleSituationData.try_start contract.

Tests use synthetic EA classes only. No confirmation of actual classroom
attendance or seated students is implied by these offline unit tests.
"""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))

from mhs108_ea_phase_adapter import install_offline_only, REQUIRED_LIVE_GATES
from tests.test_m108_lesson_phase_policy import (
    manifest as mhs_manifest, observation_context,
)
from tests.test_m108_native_invitation import CLASSES, CORE


class Reference(object):
    def __init__(self, guid):
        self.guid64 = guid


class JobEntry(object):
    def __init__(self, job):
        self.job = Reference(job)


class Sim(object):
    def __init__(self, sim_id):
        self.sim_id = sim_id
    def __hash__(self):
        return self.sim_id
    def __eq__(self, other):
        return isinstance(other, Sim) and other.sim_id == self.sim_id


ALL = CLASSES[0] + CLASSES[1]
EXTRA = ('200', '201', '999')


def proof():
    return {name: True for name in REQUIRED_LIVE_GATES}


def context(window='10:00', staff=('200', '201'), **updates):
    c = observation_context(window)
    c.update({
        'mhs_lesson_router_active': True,
        'observed_on_lot': ALL + EXTRA,
        'observed_ea_school_members': ALL,
        'verified_native_eligible_ids': ALL,
        'verified_staff_roles': True,
        'verified_staff_ids': staff,
    })
    c.update(updates)
    return c


def fixture(create=True):
    class WeeklyScheduleSituationData(object):
        @classmethod
        def try_start(cls, sims, sim_info, duration,
                      additional_sim_ids, situation_job_count):
            cls.called += 1
            # Simulates the EA method mutating the exact 'sims' argument
            # ONLY after successfully creating an original EA situation.
            if not create:
                return None
            taken = tuple(sorted(sims, key=lambda s: s.sim_id))
            cls.seen = tuple(s.sim_id for s in taken)
            sims.difference_update(taken)
            situation_job_count[cls.guid64] = len(taken)
            return cls.guid64 + 1

    class Class1Lesson(WeeklyScheduleSituationData):
        guid64 = 304563
        situation = Reference(304565)
        job_assignments = (JobEntry(277919),)
        called = 0
        seen = ()

    class Class2Lesson(WeeklyScheduleSituationData):
        guid64 = 304570
        situation = Reference(304567)
        job_assignments = (JobEntry(280777), JobEntry(277918),
                           JobEntry(278224))
        called = 0
        seen = ()

    class Class2Ready(WeeklyScheduleSituationData):
        guid64 = 297773
        situation = Reference(297774)
        job_assignments = (JobEntry(277919), JobEntry(277918))
        called = 0
        seen = ()

    class OtherEvent(WeeklyScheduleSituationData):
        guid64 = 88888
        situation = Reference(77777)
        job_assignments = (JobEntry(123),)
        called = 0
        seen = ()

    return (WeeklyScheduleSituationData, Class1Lesson,
            Class2Lesson, Class2Ready, OtherEvent)


def simulate(klass, sims):
    job_count = {}
    result = klass.try_start(sims, None, 'EA_DURATION', (), job_count)
    return result, job_count


class EAOriginalPhaseAdapterTests(unittest.TestCase):
    def test_live_gates_cannot_be_assumed(self):
        for missing in REQUIRED_LIVE_GATES:
            Base, _, _, _, _ = fixture()
            gates = proof()
            gates[missing] = False
            self.assertIsNone(install_offline_only(
                Base, mhs_manifest(), lambda cls: context(), gates))

    def test_class2_uses_exact_six_npcs_and_verified_teacher_staff(self):
        Base, _, Class2, _, _ = fixture()
        manifest = mhs_manifest()
        uninstall = install_offline_only(
            Base, manifest, lambda cls: context(), proof())
        self.assertTrue(callable(uninstall))
        original = set(Sim(int(x)) for x in ALL + EXTRA)
        result, counts = simulate(Class2, original)
        self.assertEqual(result, 304571)
        self.assertEqual(Class2.called, 1)
        self.assertEqual(
            Class2.seen, (10, 11, 12, 13, 14, 15, 200, 201))
        self.assertEqual(
            counts[304570], 8)
        self.assertEqual(set(x.sim_id for x in original),
                         {1, 2, 3, 4, 5, 6, 7, 8, 9, 16, 999})
        self.assertTrue(uninstall())
        self.assertFalse(uninstall())

    def test_class2_ready_same_student_job_does_not_take_class1(self):
        Base, _, _, Ready, _ = fixture()
        uninstall = install_offline_only(
            Base, mhs_manifest(), lambda cls: context('09:30'), proof())
        students = set(Sim(int(x)) for x in ALL + EXTRA)
        result, counts = simulate(Ready, students)
        self.assertEqual(result, 297774)
        self.assertEqual(Ready.seen,
                         (10, 11, 12, 13, 14, 15, 200, 201))
        self.assertTrue(uninstall())

    def test_class1_with_two_playables_can_only_consume_its_npcs(self):
        Base, Class1, _, _, _ = fixture()
        manifest = mhs_manifest(playable=('1', '5', '9'))
        uninstall = install_offline_only(
            Base, manifest, lambda cls: context(), proof())
        sims = set(Sim(int(x)) for x in ALL + EXTRA)
        result, counts = simulate(Class1, sims)
        self.assertEqual(result, 304564)
        self.assertEqual(Class1.seen, (2, 3, 4, 6, 7, 8))
        self.assertTrue(all(x not in Class1.seen for x in (200, 201, 999)))
        self.assertEqual(len(sims), len(ALL + EXTRA) - 6)
        self.assertTrue(uninstall())

    def test_class1_seven_npcs_refused_until_native_phase_cap_solved(self):
        Base, Class1, _, _, _ = fixture()
        uninstall = install_offline_only(
            Base, mhs_manifest(), lambda cls: context(), proof())
        sims = set(Sim(int(x)) for x in ALL + EXTRA)
        original = sims.copy()
        result, counts = simulate(Class1, sims)
        self.assertIsNone(result)
        self.assertEqual(Class1.called, 0)
        self.assertEqual(sims, original)
        self.assertEqual(counts, {})
        self.assertTrue(uninstall())

    def test_failed_original_creation_does_not_remove_from_shared_set(self):
        Base, _, Class2, _, _ = fixture(create=False)
        uninstall = install_offline_only(
            Base, mhs_manifest(), lambda cls: context(), proof())
        sims = set(Sim(int(x)) for x in ALL + EXTRA)
        original = sims.copy()
        result, counts = simulate(Class2, sims)
        self.assertIsNone(result)
        self.assertEqual(Class2.called, 1)
        self.assertEqual(sims, original)
        self.assertEqual(counts, {})
        self.assertTrue(uninstall())

    def test_no_unknown_student_or_unverified_phase_provenance(self):
        Base, _, Class2, _, Other = fixture()
        uninstall = install_offline_only(
            Base, mhs_manifest(), lambda cls: context(
                verified_native_eligible_ids=ALL[:-2]), proof())
        sims = set(Sim(int(x)) for x in ALL + EXTRA)
        self.assertIsNone(simulate(Class2, sims)[0])
        self.assertEqual(Class2.called, 0)
        result, counts = simulate(Other, sims)
        self.assertEqual(result, 88889)  # Vanilla outside school.
        self.assertIn(999, Other.seen)
        self.assertTrue(uninstall())

    def test_inactive_context_runs_vanilla_unchanged(self):
        Base, _, Class2, _, _ = fixture()
        uninstall = install_offline_only(
            Base, mhs_manifest(),
            lambda cls: context(mhs_lesson_router_active=False),
            proof())
        sims = set(Sim(int(x)) for x in ALL + EXTRA)
        result, _ = simulate(Class2, sims)
        self.assertEqual(result, 304571)
        self.assertEqual(len(Class2.seen), 19)
        self.assertIn(999, Class2.seen)
        self.assertTrue(uninstall())

    def test_mismatch_ea_situation_or_student_job_fails_closed(self):
        Base, _, Class2, _, _ = fixture()
        Class2.job_assignments = (JobEntry(277919), JobEntry(277918))
        undo = install_offline_only(
            Base, mhs_manifest(), lambda cls: context(), proof())
        sims = set(Sim(int(x)) for x in ALL + EXTRA)
        before = sims.copy()
        result, counts = simulate(Class2, sims)
        self.assertIsNone(result)
        self.assertEqual(Class2.called, 0)
        self.assertEqual(before, sims)
        self.assertTrue(undo())

    def test_staff_identity_missing_is_a_blocker_not_random_replacement(self):
        Base, _, Class2, _, _ = fixture()
        undo = install_offline_only(
            Base, mhs_manifest(), lambda cls: context(staff=()), proof())
        sims = set(Sim(int(x)) for x in ALL + EXTRA)
        self.assertIsNone(simulate(Class2, sims)[0])
        self.assertEqual(Class2.called, 0)
        self.assertTrue(undo())

    def test_second_hook_rejected_and_original_restored(self):
        Base, _, Class2, _, _ = fixture()
        undo = install_offline_only(
            Base, mhs_manifest(), lambda cls: context(), proof())
        self.assertIsNone(install_offline_only(
            Base, mhs_manifest(), lambda cls: context(), proof()))
        self.assertTrue(undo())
        sims = set(Sim(int(x)) for x in ALL + EXTRA)
        result, _ = simulate(Class2, sims)
        self.assertEqual(result, 304571)
        self.assertEqual(len(Class2.seen), 19)


if __name__ == '__main__':
    unittest.main()
