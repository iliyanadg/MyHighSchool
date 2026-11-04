"""Exercise the real controller bookkeeping/hooks without importing EA."""
import ast
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/classroom_control'))
from mhs_attendance_policy import LessonRequestLedger
import mhs_classroom_bootstrap as bootstrap


class RuntimeTests(unittest.TestCase):
    def load_controller(self,base_count=8):
        source=ROOT/'src/m145_class2_playable/mhs145_classroom_controller.py'
        tree=ast.parse(source.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef)
                  and n.name=='ThirteenNPCController')
        groups=(tuple(str(i) for i in range(1,9)),tuple(str(i) for i in range(9,17)))
        targets=tuple(str(i) for i in range(100,100+base_count))
        jobs=(278965,278966,278967,278968,303765)
        pinned={j:str(i+1) for i,j in enumerate(jobs)}
        class Store(object):
            def __init__(self,_):pass
            def load(self,_):return self
            def class_members(self,k):return groups[k-1]
        class Manager(object):
            def create_situation(self,*args,**kwargs):return 123
        class Request(object):
            def __init__(self,*args,**kwargs):pass
            def get_additional_filter_terms(self):return ('original',)
            def clone_for_replace(self,*args,**kwargs):return 'original'
        class Day(object):
            guid64=277657
            @classmethod
            def get_long_term_situation_count(cls,data,resolver):return (3,3)
        day=[('1',1)]
        ns={'LessonRequestLedger':LessonRequestLedger,'FOLDER':'unused',
            'RosterStore':Store,'CORE_JOBS':jobs,'BASE_SITUATION':277733,
            'SCHOOL_SCHEDULES':frozenset((277657,279958)),
            'current_school_day':lambda slot:day[0],
            'registered_for_school_travel':lambda slot:('1',targets,pinned),
            '_m141_stop_trace':lambda runtime:None,
            '_install_school_adapters':lambda runtime:True}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
        runtime=ns['ThirteenNPCController']('1',targets,pinned,1,Manager,Request,
            Day,SimpleNamespace(guid64=277894),
            {j:SimpleNamespace(guid64=j) for j in jobs},object(),object(),object())
        runtime.in_school=lambda:True
        return runtime,Day,day,groups

    def test_real_count_hook_uses_save_partition_not_eight_constant(self):
        for count in (0,3,8,11):
            runtime,day,_,_=self.load_controller(count)
            self.assertTrue(runtime.install())
            data=SimpleNamespace(situation=SimpleNamespace(guid64=277733))
            self.assertEqual(day.get_long_term_situation_count(data,None),(count,count))
            # Other EA situations retain their exact original schedule count.
            other=SimpleNamespace(situation=SimpleNamespace(guid64=999))
            self.assertEqual(day.get_long_term_situation_count(other,None),(3,3))

    def test_new_day_resets_actual_controller_and_unchanged_day_does_not(self):
        runtime,_,_,groups=self.load_controller()
        runtime.begin_school_day(('1',1))
        runtime.created['100']=123
        runtime.lesson_attempted.add(1)
        runtime.m142_afternoon_rearmed=True
        runtime.lesson_requests.record_result('morning','1',{'hour':10,'minute':1},
                                             False,'EA_REJECTED')
        runtime.begin_school_day(('1',1))
        self.assertEqual(runtime.created,{'100':123})
        self.assertTrue(runtime.m142_afternoon_rearmed)
        runtime.begin_school_day(('1',2))
        self.assertEqual(runtime.created,{})
        self.assertEqual(runtime.lesson_attempted,set())
        self.assertFalse(runtime.m142_afternoon_rearmed)
        self.assertEqual(runtime.lesson_requests.state('morning','1')['attempts'],0)
        self.assertEqual(runtime.lesson_classes,groups)

    def test_zone_hook_preserves_result_installs_once_and_calls_owner(self):
        events=[]
        class Zone(object):
            def on_loading_screen_animation_finished(self,value):
                events.append(('EA',value))
                return 'EA_RESULT'
        original_refresh=bootstrap.refresh
        try:
            bootstrap.refresh=lambda:events.append(('MHS',None))
            self.assertTrue(bootstrap.install(Zone))
            wrapped=Zone.on_loading_screen_animation_finished
            self.assertTrue(bootstrap.install(Zone))
            self.assertIs(Zone.on_loading_screen_animation_finished,wrapped)
            self.assertEqual(Zone().on_loading_screen_animation_finished(9),'EA_RESULT')
            self.assertEqual(events,[('EA',9),('MHS',None)])
        finally:
            bootstrap.refresh=original_refresh


if __name__=='__main__':unittest.main()
