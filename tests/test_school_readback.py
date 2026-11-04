"""Native membership evidence must not become assignment or attendance."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]
for folder in ('classroom_control', 'm148_clock', 'm53_staff', 'm2_registry'):
    sys.path.insert(0, str(ROOT / 'src' / folder))
from mhs53_staff_store import StaffRoster
from mhs_school_readback import entry_window, entry_snapshot, staff_snapshot, school_memberships, staff_sample_period


class Queue:
    def __init__(self):
        self.running = None
    def __iter__(self):
        return iter(()) if self.running is None else iter((self.running,))


class Info:
    def __init__(self, sid, present=True, trait=False):
        self.sim_id = sid
        self.first_name = 'Chosen'
        self.last_name = str(sid)
        self.sim = NS(queue=Queue()) if present else None
        self.trait_tracker = NS(has_trait=lambda _: trait)
    def get_sim_instance(self):
        return self.sim


class Infos:
    def __init__(self, *infos):
        self.rows = {info.sim_id: info for info in infos}
    def get(self, sid):
        return self.rows.get(sid)
    def get_all(self):
        return self.rows.values()


def situation(sid, job, role=1):
    return NS(guid64=sid,
              get_current_job_for_sim=lambda _: NS(guid64=job),
              get_current_role_state_for_sim=lambda _: NS(guid64=role))


class ReadbackTests(unittest.TestCase):
    def test_both_entry_windows_include_boundaries_and_reject_unknown_time(self):
        for hour, minute, expected in ((9,29,None),(9,30,'morning'),
                (10,30,'morning'),(10,31,None),(13,30,'afternoon'),
                (14,30,'afternoon'),(14,31,None),(True,30,None)):
            self.assertEqual(entry_window({'hour':hour,'minute':minute}),expected)

    def test_staff_reads_are_limited_to_five_original_school_phases(self):
        samples=((7,59,None),(8,0,'arrival'),(9,29,'arrival'),
                 (9,30,'morning_lesson'),(10,59,'morning_lesson'),
                 (11,0,'lunch_and_preparation'),
                 (13,59,'lunch_and_preparation'),
                 (14,0,'afternoon_lesson'),
                 (14,59,'afternoon_lesson'),
                 (15,0,'school_end'),(16,0,'school_end'),
                 (16,1,None),(24,0,None),(True,30,None))
        for hour,minute,expected in samples:
            self.assertEqual(
                staff_sample_period({'hour':hour,'minute':minute}),expected)

    def test_staff_read_period_refuses_unknown_clock_without_fabricating_result(self):
        for clock in (None,0,{},[],{'hour':'9','minute':30},
                      {'hour':9,'minute':60}):
            self.assertIsNone(staff_sample_period(clock))

    def test_preparation_job_277919_is_retained_for_class_two_without_guessing(self):
        info = Info(1)
        manager = NS(get_situations_sim_is_in=lambda _: [situation(297774,277919)])
        result = entry_snapshot({'hour':9,'minute':33}, ((),('1',)),
                                Infos(info),manager,object())
        row = result['students'][0]
        self.assertEqual(row['registered_class'],2)
        self.assertIs(row['ea_class1_trait_present'],False)
        self.assertEqual(row['native_school_memberships']['jobs'][0]['job_guid'],277919)
        self.assertEqual(row['name'],'Chosen 1')
        self.assertEqual(result['world_mutations'],0)

    def test_mixer_parent_is_read_without_changing_running_interaction(self):
        info=Info(1)
        parent=type('super_HighSchool_Active_AttendClass_NPC',(),{})()
        mixer=type('mixer_HighSchool_Active_React',(),{})()
        mixer.super_interaction=parent
        info.sim.queue.running=mixer
        result=entry_snapshot({'hour':10,'minute':3},(('1',),()),Infos(info),
                              NS(get_situations_sim_is_in=lambda _:()),object())
        self.assertEqual(result['students'][0]['running_parent_actions'],
                         ('super_HighSchool_Active_AttendClass_NPC',))
        self.assertIs(info.sim.queue.running,mixer)
        self.assertIs(mixer.super_interaction,parent)

    def test_missing_student_remains_identifiable_without_fabricated_presence(self):
        row=entry_snapshot({'hour':14,'minute':3},(('1',),()),Infos(),None,None)['students'][0]
        self.assertEqual(row['sim_id'],'1')
        self.assertFalse(row['sim_present'])
        self.assertFalse(row['queue_details_available'])
        self.assertFalse(row['native_school_memberships']['available'])

    def test_staff_comparison_uses_actual_jobs_not_presence_on_lot(self):
        chosen,actual=Info(1),Info(2)
        roles={'principal':'1','teacher1':None,'teacher2':None,'teacher3':None,
               'cafeteria':[],'custodians':[]}
        roster=StaffRoster('11',roles)
        before=roster.to_json()
        manager=NS(get_situations_sim_is_in=lambda sim:
                   [situation(298096,278223)] if sim is actual.sim else ())
        result=staff_snapshot(roster,Infos(chosen,actual),manager,None)
        self.assertTrue(result['complete'])
        self.assertTrue(result['selected_sims'][0]['sim_present'])
        self.assertEqual(result['comparison']['principal']['observed'],['2'])
        self.assertFalse(result['comparison']['principal']['matches'])
        self.assertFalse(result['selection_bridge_implemented'])
        self.assertEqual(roster.to_json(),before)

    def test_same_teacher_in_core_and_lesson_is_one_observed_person(self):
        info=Info(1)
        roles={'principal':None,'teacher1':'1','teacher2':None,'teacher3':None,
               'cafeteria':[],'custodians':[]}
        manager=NS(get_situations_sim_is_in=lambda _: [
            situation(298052,277895),situation(304565,277918)])
        result=staff_snapshot(StaffRoster('11',roles),Infos(info),manager,None)
        self.assertEqual(result['comparison']['teacher1']['observed'],['1'])
        self.assertTrue(result['comparison']['teacher1']['matches'])

    def test_unavailable_membership_api_cannot_certify_staff_matches(self):
        result=staff_snapshot(StaffRoster('11'),Infos(Info(1)),object(),None)
        self.assertFalse(result['complete'])
        self.assertIsNone(result['comparison']['principal']['matches'])

    def test_partial_membership_and_bounded_world_reads_are_explicit(self):
        bad=NS(guid64=298096)
        result=school_memberships(object(),NS(get_situations_sim_is_in=lambda _:[bad]))
        self.assertFalse(result['available'])
        pending=NS(guid64=298096,get_current_job_for_sim=lambda _:None)
        result=staff_snapshot(StaffRoster('11'),Infos(Info(1)),
            NS(get_situations_sim_is_in=lambda _:[pending]),None)
        self.assertFalse(result['complete'])
        self.assertIsNone(result['comparison']['principal']['matches'])
        infos=Infos()
        infos.get_all=lambda:(Info(i,present=False) for i in range(4097))
        result=staff_snapshot(StaffRoster('11'),infos,None,None)
        self.assertFalse(result['complete'])
        self.assertIn('SIM_INFO_LIMIT',result['errors'])
        self.assertIsNone(result['comparison']['teacher1']['matches'])


if __name__=='__main__':
    unittest.main()
