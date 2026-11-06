"""Regression tests from the verified slot-15 school day (2026-11-06).

The report showed all 16 on-lot at 08:15 but two Class2 students carrying
EA Class1 trait until 09:57; cafeteria detection reported zero stations.
No native job is considered successful without real EA readback.
"""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for subdir in ('classroom_control','m128_alignment'):
    sys.path.insert(0,str(ROOT/'src'/subdir))
from mhs_native_schedule_staff import cafeteria_native_schedule_count
from mhs_additional_native_staff import (
    school_cafeteria_station_probe,count_verified_school_cafeteria_stations)
from mhs128_ea_class_trait_alignment import planned_changes,align_roster_trait
from tests.test_classroom_runtime import RuntimeTests


class NativeCafeteriaScheduleTests(unittest.TestCase):
    def test_requires_three_real_distinct_cafeteria_stations(self):
        workers=('41','42','43')
        self.assertEqual(cafeteria_native_schedule_count(
            (1,1),workers,3),((3,3),'NATIVE_EA_SCHEDULE_VENDOR_COUNT_ADJUSTED'))
        self.assertEqual(cafeteria_native_schedule_count(
            (1,1),workers,2),((1,1),'ADDITIONAL_CAFETERIA_STATION_REQUIRED'))
        self.assertEqual(cafeteria_native_schedule_count(
            (1,1),workers,None),((1,1),'ADDITIONAL_CAFETERIA_STATION_REQUIRED'))

    def test_no_extra_vendor_when_ea_own_schedule_unknown(self):
        workers=('41','42')
        for original in ((0,0),(4,4),(1,2),(True,True),('1','1'),1):
            decided,reason=cafeteria_native_schedule_count(original,workers,3)
            self.assertEqual(decided,original)
            self.assertEqual(reason,'EA_VENDOR_COUNT_UNSUPPORTED')
        self.assertEqual(cafeteria_native_schedule_count(
            (1,1),('41','41'),3)[0],(1,1))
        self.assertEqual(cafeteria_native_schedule_count(
            (2,2),workers,2),((2,2),'EA_NATIVE_VENDOR_COUNT_ALREADY_SUFFICIENT'))
        self.assertEqual(cafeteria_native_schedule_count(
            (3,3),workers,3),((3,3),'EA_VENDOR_COUNT_MORE_THAN_SELECTED'))

    def test_station_object_manager_values_is_used_not_only_get_all(self):
        counter=types.SimpleNamespace(id=19,name='object_CafeteriaStation_HighSchool')
        objects=[types.SimpleNamespace(id=i,definition=counter)
                 for i in (11,12,13)]
        objects.append(types.SimpleNamespace(
            id=15,definition=types.SimpleNamespace(
                id=21,name='object_Desk')))
        manager=types.SimpleNamespace(values=lambda:objects)
        self.assertEqual(count_verified_school_cafeteria_stations(manager),3)
        result=school_cafeteria_station_probe(manager)
        self.assertEqual(result['count'],3)
        self.assertEqual(result['reason'],'NAMED_CAFETERIA_STATIONS_MATCHED')
        self.assertEqual(result['matched_definition_ids'],[19])

    def test_university_only_stalls_and_school_desks_not_counted(self):
        manager=types.SimpleNamespace(values=lambda:[
            types.SimpleNamespace(id=1,definition=types.SimpleNamespace(
                id=21,name='object_DU_UniversityCafeteriaStation')),
            types.SimpleNamespace(id=2,definition=types.SimpleNamespace(
                id=20,name='object_BarFoodService')),
            types.SimpleNamespace(id=3,definition=types.SimpleNamespace(
                id=23,name='object_LunchTable')),
        ])
        self.assertEqual(count_verified_school_cafeteria_stations(manager),0)

    def test_opaque_real_vendor_station_definitions_can_match_by_id(self):
        item=lambda sid:types.SimpleNamespace(
            id=sid,definition=types.SimpleNamespace(id=89,name='opaque'))
        data=[item(1),item(2),item(3)]
        self.assertEqual(count_verified_school_cafeteria_stations(
            types.SimpleNamespace(values=lambda:data),item(1)),3)


class EarlyTraitAlignmentRuntimeTests(unittest.TestCase):
    def test_native_day_preflight_aligns_two_wrong_class2_npcs(self):
        runtime,_,_,groups=RuntimeTests().load_controller()
        runtime.active=True
        # The live trace saw Zelmira/Sofia Class1-trait on Class2
        # at 09:30 even though both were already summoned at 08:15.
        class Tracker:
            def __init__(self,has): self.present=has
            def has_trait(self,trait): return self.present
            def add_trait(self,trait): self.present=True
            def remove_trait(self,trait): self.present=False
        class SimInfo:
            age='TEEN'
            species='HUMAN'
            def __init__(self,initial): self.trait_tracker=Tracker(initial)
        infos={int(i):SimInfo(int(i)<=8 or int(i) in (12,13))
               for group in groups for i in group}
        live=types.SimpleNamespace(get=infos.get)
        trait=types.SimpleNamespace(guid64=293779)
        ea=types.ModuleType('sims4')
        resource=types.ModuleType('sims4.resources')
        resource.Types=types.SimpleNamespace(TRAIT='TRAIT')
        ea.resources=resource
        services=types.SimpleNamespace(
            get_instance_manager=lambda kind:types.SimpleNamespace(
                get=lambda key:trait),
            sim_info_manager=lambda:live,
            time_service=lambda:object())
        env=runtime.begin_school_day.__func__.__globals__
        old={key:env.get(key) for key in
             ('services','Age','Species','CLASS1_TRAIT_ID','planned_changes',
              'align_roster_trait','game_clock')}
        updates={
            'services':services,
            'Age':types.SimpleNamespace(TEEN='TEEN'),
            'Species':types.SimpleNamespace(HUMAN='HUMAN'),
            'CLASS1_TRAIT_ID':293779,
            'planned_changes':planned_changes,
            'align_roster_trait':align_roster_trait,
            'game_clock':lambda service:{'hour':8,'minute':0}}
        try:
            env.update(updates)
            with patch.dict(sys.modules,{'sims4':ea,'sims4.resources':resource}):
                runtime.begin_school_day(('1',1))
            self.assertEqual(runtime.m128_early_sync['result']['changed'],2)
            self.assertTrue(runtime.m128_early_sync['result']['success'])
            self.assertTrue(runtime.m131_sync_attempted)
            self.assertFalse(infos[12].trait_tracker.present)
            self.assertFalse(infos[13].trait_tracker.present)
            self.assertEqual(runtime.m128_early_sync['clock']['hour'],8)
        finally:
            for key,v in old.items():
                if v is None:
                    env.pop(key,None)
                else:
                    env[key]=v


if __name__=='__main__':
    unittest.main()
