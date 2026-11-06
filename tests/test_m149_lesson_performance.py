"""M149: read-only lesson evidence and sampling regression tests."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m148_clock'))
from mhs149_lesson_audit import audit_lesson_entry,audit_manual_whiteboard_choice
from mhs148_clock_and_sampling import should_capture_entry_snapshot


def sample(period, rows, lag=31.0):
    return {'period':period,'students':rows,
            'dual_clock':{'lag_minutes':lag}}


def row(sid, klass, present=True, action=None):
    return {'sim_id':str(sid),'registered_class':klass,
            'sim_present':present,'running_action':action}


class M149LessonAuditTests(unittest.TestCase):
    def test_half_as_many_heavy_entry_reads_without_touching_ea_polls(self):
        # Sim ticks per minute are 1500; 3-minute automation cadence.
        ticks=[1500*(570+3*i) for i in range(21)]
        stored=[]
        skipped=0
        for tick in ticks:
            if should_capture_entry_snapshot(
                    tick,stored[-1] if stored else None):
                stored.append(tick)
            else:
                skipped+=1
        self.assertEqual(len(ticks),21)
        self.assertEqual(len(stored),11)
        self.assertEqual(skipped,10)
        self.assertEqual(stored[-1],ticks[-1])
        self.assertTrue(should_capture_entry_snapshot(
            ticks[1],ticks[0],forced=True))

    def test_reports_actions_not_fabricated_lesson_completion(self):
        register=(('1','2'),('3','4'))
        npc='sims4.tuning.instances.super_HighSchool_Active_AttendClass_NPC'
        playable='sims4.tuning.instances.super_HighSchool_Active_Whiteboard_Attend_Art'
        entries=[
            sample('morning',[row('1',1,True,npc),row('2',1,True),
                              row('3',2,True,npc),row('4',2,True)],lag=30),
            sample('morning',[row('1',1),row('2',1,True,playable),
                              row('3',2),row('4',2,True,playable)],lag=35),
            sample('afternoon',[row('1',1,True,npc),row('2',1,True,playable),
                                row('3',2,True,npc),row('4',2,True,playable)],lag=40)]
        r=audit_lesson_entry(entries,register)
        self.assertEqual(r['sample_count'],3)
        self.assertTrue(r['all_registered_present_in_every_sample'])
        self.assertTrue(r['all_registered_have_running_lesson_evidence'])
        self.assertTrue(r['does_not_prove_completed_lesson_or_grade'])
        self.assertEqual(r['lesson_completion'],
                         'NOT_VERIFIED_BY_ENTRY_ACTIONS')
        self.assertEqual(r['periods']['morning']['snapshot_count'],2)
        self.assertEqual(r['periods']['afternoon']['snapshot_count'],1)
        self.assertEqual(r['clock_lag_minutes']['minimum'],30)
        self.assertEqual(r['clock_lag_minutes']['median'],35)
        self.assertEqual(r['clock_lag_minutes']['maximum'],40)
        self.assertTrue(r['lag_not_attributed_to_this_mod'])
        self.assertEqual(r['student_or_staff_mutations'],0)

    def test_missing_student_is_not_silently_counted_present(self):
        r=audit_lesson_entry([
            sample('morning',[row('1',1),row('2',1,False),row('3',2)])],
            (('1','2'),('3','4')))
        self.assertFalse(r['all_registered_present_in_every_sample'])
        self.assertEqual(
            r['periods']['morning']['class_results']['1']['minimum_instanced'],1)
        self.assertEqual(
            r['periods']['morning']['class_results']['2']['minimum_instanced'],1)
        self.assertFalse(r['all_registered_have_running_lesson_evidence'])

    def test_no_afternoon_snapshot_is_unknown_not_a_failed_lesson(self):
        r=audit_lesson_entry([sample('morning',[row('1',1)])],
                             (('1',),()))
        result=r['periods']['afternoon']
        self.assertEqual(result['snapshot_count'],0)
        self.assertIsNone(result['class_results']['1']['minimum_instanced'])
        self.assertIsNone(result['class_results']['1']['all_instanced_each_sample'])

    def test_queued_action_does_not_count_as_running_lesson(self):
        entries=[sample('morning',[dict(
            row('1',1),queued_actions=[
                'super_HighSchool_Active_Whiteboard_Attend_Art'])])]
        r=audit_lesson_entry(entries,(('1',),()))
        self.assertFalse(r['all_registered_have_running_lesson_evidence'])
        self.assertEqual(
            r['periods']['morning']['class_results']['1']['running_lesson_seen'],[])

    def test_manual_whiteboard_original_ea_menu_coexists_with_automation(self):
        audit=audit_manual_whiteboard_choice(
            {'applied':True,'variant':'ZERBU'},
            {'applied':True,'reason':'EA_EIGHT_SUBJECTS_CLASS_PICKER_REUSED'},
            {1:{'id':'101'},2:{'id':'202'}},67)
        self.assertTrue(audit['manual_click_preserved_by_original_ea_menu'])
        self.assertTrue(audit['auto_push_defers_to_existing_class_or_board_navigation'])
        self.assertTrue(audit['ea_schedule_and_subject_availability_still_apply'])
        self.assertFalse(audit['manual_menu_visibility_verified_in_game'])
        self.assertEqual(audit['world_mutations'],0)
        self.assertEqual(audit['assigned_board_ids'],{'1':'101','2':'202'})

    def test_manual_mode_not_claimed_without_own_unique_boards_and_patches(self):
        for picker,subs,boards in (
            (None,{'applied':True},{1:{'id':'101'},2:{'id':'202'}}),
            ({'applied':True},None,{1:{'id':'101'},2:{'id':'202'}}),
            ({'applied':True},{'applied':True},
             {1:{'id':'101'},2:{'id':'101'}}),
        ):
            audit=audit_manual_whiteboard_choice(picker,subs,boards,0)
            self.assertFalse(audit['manual_click_preserved_by_original_ea_menu'])
            self.assertFalse(audit['manual_menu_visibility_verified_in_game'])

    def test_empty_report_is_unknown_not_success(self):
        r=audit_lesson_entry([],(('1',),('2',)))
        self.assertIsNone(r['all_registered_present_in_every_sample'])
        self.assertIsNone(r['all_registered_have_running_lesson_evidence'])
        self.assertEqual(r['clock_lag_minutes']['observed_samples'],0)


if __name__=='__main__':
    unittest.main()
