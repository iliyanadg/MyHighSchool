"""M150 offline: next-day identity continuity and 09:40 observations."""
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'classroom_control'))
sys.path.insert(0,str(ROOT/'src'/'m148_clock'))
from mhs150_day_continuity import snapshot,record,compare
from mhs150_early_preparation import audit_940_preparation

def classes():
    return (tuple(str(i) for i in range(1,9)),
            tuple(str(i) for i in range(9,17)))

class M150Tests(unittest.TestCase):
    def test_two_days_same_students_and_staff(self):
        with tempfile.TemporaryDirectory() as folder:
            staff={'teacher1':('21',),'teacher2':('22',),
                   'custodians':('23','24')}
            day1=snapshot('15',('15',3),classes(),staff)
            day2=snapshot('15',('15',4),classes(),staff)
            first=record(folder,day1)
            self.assertEqual(first['status'],'FIRST_DAY_BASELINE')
            repeat=record(folder,day1)
            self.assertEqual(repeat['status'],'SAME_SCHOOL_DAY')
            next_day=record(folder,day2)
            self.assertEqual(next_day['status'],
                             'SAME_SAVED_SELECTIONS_ON_NEXT_SCHOOL_DAY')
            self.assertTrue(next_day['identical_selected_staff'])
            self.assertTrue(next_day['identical_class_1_ids'])
            self.assertTrue(next_day['identical_class_2_ids'])

    def test_day_with_one_changed_teacher_not_certified(self):
        original=snapshot('15',('15',4),classes(),{'teacher1':('21',)})
        changed=snapshot('15',('15',5),classes(),{'teacher1':('22',)})
        r=compare(original,changed)
        self.assertEqual(r['status'],'REGISTRY_OR_PERSONNEL_CHANGED')
        self.assertFalse(r['identical_selected_staff'])

    def test_wrong_slot_or_bad_roster_refused(self):
        with self.assertRaises(ValueError):
            snapshot('15',('16',4),classes(),{})
        with self.assertRaises(ValueError):
            snapshot('15',('15',4),(('1',),('9',)),{})
        with self.assertRaises(ValueError):
            snapshot('15',('15',4),classes(),{'teacher1':('0',)})

    def test_no_0940_snapshot_is_unknown(self):
        r=audit_940_preparation([],classes(),{})
        self.assertIsNone(r['all_present'])
        self.assertEqual(r['reason'],'NO_0940_SIM_TIME_SAMPLE')

    def test_0940_native_action_uses_correct_board_only(self):
        sample={'period':'morning',
                'clock':{'hour':9,'minute':40,'repr':'09:40'},
                'dual_clock':{'lag_minutes':36,
                    'game_time_displayed':{'repr':'10:16'}},
                'students':[
                    {'sim_id':'1','registered_class':1,'sim_present':True,
                     'running_action':'super_HighSchool_Active_AttendClass_NPC',
                     'action_target_id':'100'},
                    {'sim_id':'9','registered_class':2,'sim_present':True,
                     'running_action':'super_HighSchool_Active_Whiteboard_Attend_Art',
                     'action_target_id':'200'},
                    {'sim_id':'2','registered_class':1,'sim_present':True,
                     'running_action':'super_HighSchool_Active_AttendClass_NPC',
                     'action_target_id':'200'}]}
        r=audit_940_preparation([sample],classes(),
                                {1:{'id':'100'},2:{'id':'200'}})
        self.assertEqual(r['class_actions'],3)
        self.assertEqual(r['correct_native_board_actions'],2)
        self.assertEqual(r['lag_minutes'],36)
        self.assertEqual(r['sample_displayed_time'] if 'sample_displayed_time' in r
                         else r['displayed_clock'],'10:16')
        self.assertFalse(r['all_present'])
        self.assertTrue(r['does_not_prove_routing_or_seating'])
        self.assertEqual(r['world_mutations'],0)

if __name__=='__main__':
    unittest.main()
