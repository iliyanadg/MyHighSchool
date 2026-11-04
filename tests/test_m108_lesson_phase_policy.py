"""M108 real EA lesson-phase XML contract and 2x8 roster gating."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))

from mhs108_lesson_phase_policy import (
    PHASE_DATA, WINDOWS, propose_phase_students,
    assess_native_phase_result,
)
from tests.test_m108_native_invitation import (
    CLASSES, CORE, prepare_fixed_manifest,
)

EA = ROOT / 'assets' / 'ea_2026_11_01'


def manifest(playable=('1', '9', '16')):
    return prepare_fixed_manifest(CLASSES, playable, CORE, 11, 12, 777)


def observation_context(window='10:00', **changes):
    data = {
        'verified_ea_phase_origin': True,
        'verified_school_zone': True,
        'schedule_guid': 277657,
        'save_slot': '11',
        'sim_day': 12,
        'zone_id': '777',
        'time_window': window,
    }
    data.update(changes)
    return data


def propose(phase_data=304570, playable=('1', '9', '16'),
            eligible=None, on_lot=None, ea_students=None,
            context=None, sit=None, job=None):
    m = manifest(playable)
    kind, class_num, s, j, upper = PHASE_DATA[phase_data]
    if context is None:
        context = observation_context('10:00' if kind == 'lesson'
                                      else '09:30')
    if on_lot is None:
        on_lot = CLASSES[0] + CLASSES[1] + ('200',)
    if ea_students is None:
        ea_students = CLASSES[0] + CLASSES[1]
    if eligible is None:
        eligible = CLASSES[0] + CLASSES[1]
    return propose_phase_students(
        m, phase_data, s if sit is None else sit,
        j if job is None else job, context, on_lot,
        ea_students, eligible)


class RealEANativePhaseTunings(unittest.TestCase):
    def test_six_phase_ids_situations_jobs_and_upper_bounds_match_xml(self):
        for guid, spec in PHASE_DATA.items():
            kind, class_num, situation, student_job, cap = spec
            root = ET.parse(str(EA / ('%s.xml' % guid))).getroot()
            self.assertEqual(
                int(root.find("./T[@n='situation']").text),
                situation, msg=str(guid))
            assignment = root.find("./L[@n='job_assignments']/U")
            self.assertEqual(
                int(assignment.find("./T[@n='job']").text),
                student_job, msg=str(guid))
            self.assertEqual(
                int(assignment.find(
                    "./U[@n='sim_count']/T[@n='upper_bound']").text),
                cap, msg=str(guid))
            self.assertEqual(
                int(assignment.find(
                    "./U[@n='sim_count']/T[@n='lower_bound']").text), 0)

    def test_class2_get_ready_uses_same_ea_student_job_as_class1(self):
        # Routing by situation-data GUID is necessary: job 277919 alone
        # does NOT tell whether this is the student's registered class.
        self.assertEqual(PHASE_DATA[297773][3], 277919)
        self.assertEqual(PHASE_DATA[293642][3], 277919)
        self.assertEqual(PHASE_DATA[304570][3], 280777)

    def test_class1_trait_branch_is_not_registration_proof(self):
        for guid in (293642, 304563):
            root = ET.parse(str(EA / ('%s.xml' % guid))).getroot()
            traits = [
                (x.text or '').strip() for x in
                root.findall(".//L[@n='whitelist_traits']/T")]
            self.assertIn('293779', traits)
        for guid in (293644, 304561):
            root = ET.parse(str(EA / ('%s.xml' % guid))).getroot()
            self.assertFalse(root.findall(
                ".//L[@n='whitelist_traits']/T"))
        # Both Class1 variants belong to ONE MHS Class 1.
        self.assertEqual(PHASE_DATA[293642][1], 1)
        self.assertEqual(PHASE_DATA[293644][1], 1)

    def test_class2_lesson_also_has_separate_staff_jobs_untouched(self):
        root = ET.parse(str(EA / '304570.xml')).getroot()
        jobs = [
            int(row.find("./T[@n='job']").text)
            for row in root.findall("./L[@n='job_assignments']/U")]
        self.assertEqual(jobs, [280777, 277918, 278224])
        self.assertEqual(len(PHASE_DATA[304570]), 5)


class FixedTwoClassLessonPolicies(unittest.TestCase):
    def test_only_four_real_ea_school_phase_windows(self):
        self.assertEqual(
            WINDOWS, {'09:30': 'prepare', '10:00': 'lesson',
                      '13:30': 'prepare', '14:00': 'lesson'})
        for kind, window in (
                ('prepare', '09:30'), ('lesson', '10:00'),
                ('prepare', '13:30'), ('lesson', '14:00')):
            data = 293642 if kind == 'prepare' else 304563
            outcome = propose(data, context=observation_context(window))
            self.assertEqual(outcome['phase'], kind)

    def test_no_playable_assumed_in_every_class(self):
        # 1 playable Class1, 2 playable Class2:
        # Class1 needs 7 NPC, more than EA's 6-cap.
        left = propose(304563)
        self.assertEqual(left['status'], 'NATIVE_PHASE_CAPACITY_BLOCKED')
        self.assertEqual(left['playable_ids'], ('1',))
        self.assertEqual(left['exact_npc_ids'],
                         ('2', '3', '4', '5', '6', '7', '8'))
        self.assertEqual(left['minimum_tuned_slot_shortfall'], 1)
        right = propose(304570)
        self.assertEqual(right['status'], 'PROPOSED_NOT_EA_ASSIGNED')
        self.assertEqual(right['playable_ids'], ('9', '16'))
        self.assertEqual(right['exact_npc_ids'],
                         ('10', '11', '12', '13', '14', '15'))
        self.assertEqual(right['minimum_tuned_slot_shortfall'], 0)
        self.assertFalse(right['native_phase_job_assignment_verified'])
        self.assertFalse(right['seating_verified'])

    def test_phase_2_class_one_can_have_six_npcs_when_two_playable(self):
        played = ('1', '5', '9')
        a = propose(304561, playable=played)
        self.assertEqual(a['status'], 'PROPOSED_NOT_EA_ASSIGNED')
        self.assertEqual(a['npc_count_required'], 6)
        self.assertEqual(a['exact_npc_ids'], ('2', '3', '4', '6', '7', '8'))
        # Class2 now needs 7, within EA's nominal 8 cap.
        b = propose(304570, playable=played)
        self.assertEqual(b['npc_count_required'], 7)
        self.assertEqual(b['status'], 'PROPOSED_NOT_EA_ASSIGNED')

    def test_class_one_can_need_all_eight_npc_slots(self):
        played = ('9', '12', '16')
        report = propose(304563, playable=played)
        self.assertEqual(report['status'], 'NATIVE_PHASE_CAPACITY_BLOCKED')
        self.assertEqual(report['npc_count_required'], 8)
        self.assertEqual(report['minimum_tuned_slot_shortfall'], 2)

    def test_original_ea_role_acceptance_required_no_trait_changes(self):
        # Original phase tests can reject an otherwise registered NPC.
        all_ids = CLASSES[0] + CLASSES[1]
        report = propose(304570, eligible=all_ids[:-2])
        self.assertEqual(report['status'], 'NATIVE_PHASE_ELIGIBILITY_BLOCKED')
        self.assertEqual(report['rejected_registered_ids'], ('15',))
        self.assertFalse(report['changes_to_game'])
        self.assertTrue(report['hidden_class_one_trait_not_modified'])

    def test_absent_registered_sim_never_replaced(self):
        report = propose(304570, on_lot=(CLASSES[0] + CLASSES[1])[:-1])
        self.assertEqual(report['status'], 'REGISTERED_STUDENT_ABSENT')
        self.assertEqual(report['missing_ids'], ('16',))
        self.assertFalse(report['native_phase_job_assignment_verified'])

    def test_extra_student_or_missing_ea_school_role_blocks(self):
        original = CLASSES[0] + CLASSES[1]
        extra = propose(304570, ea_students=original + ('999',))
        self.assertEqual(extra['status'], 'EA_SCHOOL_ROLE_MISMATCH')
        self.assertEqual(extra['extraneous_ids'], ('999',))
        absent = propose(304570, ea_students=original[:-1])
        self.assertEqual(absent['status'], 'EA_SCHOOL_ROLE_MISMATCH')
        self.assertEqual(absent['missing_ids'], ('16',))

    def test_wrong_phase_job_school_or_save_remains_untouched(self):
        for changed in (
            {'verified_ea_phase_origin': False},
            {'verified_school_zone': False},
            {'schedule_guid': 444444},
            {'sim_day': 13},
            {'save_slot': '12'},
            {'zone_id': 3},
            {'time_window': '13:30'},
            {'time_window': '15:00'},
        ):
            report = propose(304570, context=observation_context(**changed))
            self.assertEqual(report['status'], 'UNVERIFIED_CONTEXT')
        self.assertEqual(propose(304570, sit=293815)['status'],
                         'UNVERIFIED_PHASE')
        self.assertEqual(propose(297773, job=280777)['status'],
                         'UNVERIFIED_PHASE')
        self.assertEqual(
            propose_phase_students(
                manifest(), 999, 304567, 280777,
                observation_context(), (), (), ())['status'],
            'UNVERIFIED_PHASE')

    def test_duplicate_observations_rejected(self):
        report = propose(304570, ea_students=('1', '1'))
        self.assertEqual(report['status'], 'OBSERVATIONS_MISSING')

    def test_corrupted_special_role_or_base_roster_blocks_phase(self):
        original = manifest()
        for change in (
            {'base_ids': ('99',) * 8},
            {'core_assignments': ((278965, '9'),)},
            {'all_16': CLASSES[0] + CLASSES[0]},
        ):
            bad = dict(original, **change)
            result = propose_phase_students(
                bad, 304570, 304567, 280777,
                observation_context(), CLASSES[0] + CLASSES[1],
                CLASSES[0] + CLASSES[1], CLASSES[0] + CLASSES[1])
            self.assertEqual(result['status'], 'INVALID_MANIFEST')

    def test_no_native_assignment_or_seat_proof_from_proposal(self):
        report = propose(304570)
        self.assertEqual(report['status'], 'PROPOSED_NOT_EA_ASSIGNED')
        self.assertFalse(report['native_modifiers_verified'])
        self.assertFalse(report['native_phase_job_assignment_verified'])
        self.assertFalse(report['seating_verified'])

    def test_actual_job_membership_vs_seating_are_separate(self):
        m = manifest()
        c1 = tuple(x for x in CLASSES[0] if x != '1')
        c2 = tuple(x for x in CLASSES[1] if x not in ('9', '16'))
        result = assess_native_phase_result(
            m, 'lesson', '10:00', c1, c2)
        self.assertEqual(result['status'],
                         'LESSON_NPC_JOBS_MATCH_SEATING_UNKNOWN')
        self.assertTrue(result['native_phase_job_assignment_verified'])
        self.assertFalse(result['seating_verified'])
        self.assertEqual(
            assess_native_phase_result(m, 'prepare', '13:30', c1, c2)['status'],
            'PREPARATION_NPC_JOBS_MATCH')
        self.assertEqual(
            assess_native_phase_result(
                m, 'lesson', '14:00', c1, c2,
                actual_seated_by_class=CLASSES)['status'],
            'LESSON_8_PLUS_8_SEATED_OBSERVED')

    def test_swapped_job_membership_or_wrong_seating_never_verified(self):
        m = manifest()
        c1 = tuple(x for x in CLASSES[0] if x != '1')
        c2 = tuple(x for x in CLASSES[1] if x not in ('9', '16'))
        swapped = assess_native_phase_result(m, 'lesson', '10:00', c2, c1)
        self.assertEqual(swapped['status'], 'WRONG_NATIVE_CLASSROOM_PHASE')
        result = assess_native_phase_result(m, 'lesson', '10:00', c1, c2,
                                            (CLASSES[1], CLASSES[0]))
        self.assertEqual(result['status'], 'SEATING_NOT_VERIFIED')
        self.assertTrue(result['native_phase_job_assignment_verified'])
        self.assertFalse(result['seating_verified'])
        self.assertEqual(
            assess_native_phase_result(
                m, 'lesson', '09:30', c1, c2)['status'],
            'UNVERIFIED_PHASE')


if __name__ == '__main__':
    unittest.main()
