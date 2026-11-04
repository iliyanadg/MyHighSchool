import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m101_original_slot'))
from mhs101_original_slot_gate import original_school_call,validated_filter_ids

def opts(**change):
    val={'spawn_sims_during_zone_spin_up':True,
         'duration_override':234,'user_facing':False,
         'creation_source':"WeeklyScheduleDay"}
    val.update(change)
    return val
class TestOneOriginalEASchoolSlot(unittest.TestCase):
    def test_ea_schedule_spinup_is_only_eligible_origin(self):
        self.assertTrue(original_school_call(
            277733,(),opts(),('weekly_schedule_zone_director',)))
        self.assertFalse(original_school_call(
            277733,(),opts(),('other_runtime',)))
        self.assertFalse(original_school_call(
            298052,(),opts(),('weekly_schedule_zone_director',)))
        self.assertFalse(original_school_call(
            277733,(1,),opts(),('weekly_schedule_zone_director',)))
    def test_late_m61_additional_situation_never_intercepted(self):
        self.assertFalse(original_school_call(
            277733,(),{'user_facing':False},
            ('weekly_schedule_zone_director',)))
        for change in (
            {'spawn_sims_during_zone_spin_up':False},
            {'user_facing':True},
            {'creation_source':None},
        ):
            self.assertFalse(original_school_call(
                277733,(),opts(**change),('weekly_schedule_zone_director',)))
        broken=opts()
        del broken['duration_override']
        self.assertFalse(original_school_call(
            277733,(),broken,('weekly_schedule_zone_director',)))

    def test_real_scored_filter_members_only(self):
        def scored(sid,score):
            return SimpleNamespace(sim_info=SimpleNamespace(sim_id=sid),
                                   score=score)
        results=(scored(200,8),scored(100,0),scored(201,11),
                 scored(201,6),scored(999,14))
        self.assertEqual(validated_filter_ids(results,(200,100,201)),(200,201))
    def test_missing_score_not_ea_filter_proof(self):
        self.assertEqual(validated_filter_ids(
            (SimpleNamespace(sim_info=SimpleNamespace(sim_id=200)),),(200,)),())
        self.assertEqual(validated_filter_ids(None,(200,)),())
        self.assertEqual(validated_filter_ids(
            (SimpleNamespace(sim_info=SimpleNamespace(sim_id=200),score=1),),
            (True,)),())
if __name__=='__main__':
    unittest.main()
