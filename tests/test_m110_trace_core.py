"""M110 synthetic pass-through tests: never a gameplay validation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m110_trace'))
from mhs110_call_trace_core import M110Trace, EVENT_LIMIT


def native():
    activity = {'count': 0, 'phase': 0, 'created': 0, 'raise': 0}
    def count(cls, data, resolver):
        activity['count'] += 1
        return (6, 6)
    def phase(cls, *args, **kwargs):
        activity['phase'] += 1
        return 123456
    def created(self, situation_type, *args, **kwargs):
        activity['created'] += 1
        return 'EA ID'
    attrs = [
        ('venues.weekly_schedule_zone_director', 'WeeklyScheduleDay',
         {'get_long_term_situation_count': classmethod(count), 'guid64':277657}),
        ('venues.weekly_schedule_zone_director', 'WeeklyScheduleSituationData',
         {'try_start':classmethod(phase), 'guid64':293642}),
        ('situations.situation_manager', 'SituationManager',
         {'create_situation':created}),
    ]
    result = {}
    for key, (mod, name, definition) in zip(
            ('weekly_day','weekly_data','situation_manager'),attrs):
        result[key] = type(name,(object,),dict(definition,__module__=mod))
    return result, activity


class TraceTest(unittest.TestCase):
    def test_three_calls_identical_results_and_one_original_invocation(self):
        classes, calls = native()
        old = {key:dict(cls.__dict__) for key,cls in classes.items()}
        trace = M110Trace()
        self.assertTrue(trace.start(classes))
        self.assertEqual(classes['weekly_day'].get_long_term_situation_count(None,None),(6,6))
        self.assertEqual(classes['weekly_data'].try_start([],None,42,[],{}),123456)
        self.assertEqual(classes['situation_manager']().create_situation(
            type('S',(object,),{'guid64':277733}),None),'EA ID')
        self.assertEqual(calls, {'count':1,'phase':1,'created':1,'raise':0})
        self.assertEqual(trace.report()['event_counts'],{
            'get_long_term_situation_count':1,'try_start':1,'create_situation':1})
        self.assertEqual([x['phase'] for x in trace.report()['events']],
                         ['enter','return','enter','return','enter','return'])
        self.assertTrue(trace.stop())
        self.assertEqual(old,{key:dict(cls.__dict__) for key,cls in classes.items()})
        self.assertFalse(trace.report()['runtime_descriptors_temporarily_modified'])
        self.assertEqual(trace.report()['events'][1]['ea_count_pair'],[6,6])

    def test_known_mhs_hook_blocks_all_targets_without_partial_install(self):
        classes,_ = native()
        first=classes['weekly_day'].__dict__['get_long_term_situation_count']
        classes['weekly_data'].__dict__['try_start'].__func__._mhs108_unified_lessons = True
        trace=M110Trace()
        self.assertFalse(trace.start(classes))
        self.assertIs(first,classes['weekly_day'].__dict__['get_long_term_situation_count'])
        self.assertFalse(trace.report()['temporary_runtime_wrappers_active'])

    def test_cannot_rearm_or_change_another_mod_wrapper_on_stop(self):
        classes,_=native()
        trace=M110Trace()
        self.assertTrue(trace.start(classes))
        self.assertFalse(trace.start(classes))
        original=classes['weekly_data'].__dict__['try_start']
        def other(cls,*a,**kw): return None
        classes['weekly_data'].try_start=classmethod(other)
        self.assertFalse(trace.stop())
        self.assertEqual(trace.report()['status'],'RESTORE_CONFLICT')
        self.assertIsNot(original, classes['weekly_data'].__dict__['try_start'])

    def test_exception_from_native_method_propagated_without_retry(self):
        classes,calls=native()
        def fail(cls,*args,**kwargs):
            calls['raise']+=1
            raise LookupError('EA native exception')
        classes['weekly_data'].try_start=classmethod(fail)
        trace=M110Trace()
        self.assertTrue(trace.start(classes))
        with self.assertRaisesRegex(LookupError,'EA native exception'):
            classes['weekly_data'].try_start(None)
        self.assertEqual(calls['raise'],1)
        self.assertEqual(trace.report()['events'][-1]['phase'],'raise')
        self.assertTrue(trace.stop())

    def test_missing_owner_or_invalid_descriptor_never_installs(self):
        classes,_=native()
        cls=classes['weekly_data']
        cls.try_start=lambda self,*a,**kw:None
        trace=M110Trace()
        self.assertFalse(trace.start(classes))
        self.assertFalse(trace.report()['temporary_runtime_wrappers_active'])

    def test_atomic_partial_install_failure_restores_first_wrappers(self):
        classes,_=native()
        class RejectTryStart(type):
            def __setattr__(cls, key, value):
                if key == 'try_start':
                    raise RuntimeError('EA descriptor immutable')
                return type.__setattr__(cls, key, value)
        old_data=classes['weekly_data']
        attrs={k:v for k,v in old_data.__dict__.items()
               if k not in ('__dict__','__weakref__','__doc__','__module__')}
        attrs['__module__']='venues.weekly_schedule_zone_director'
        classes['weekly_data']=RejectTryStart('WeeklyScheduleSituationData',
                                              (object,),attrs)
        old=classes['weekly_day'].__dict__['get_long_term_situation_count']
        trace=M110Trace()
        self.assertFalse(trace.start(classes))
        self.assertIs(old,classes['weekly_day'].__dict__[
            'get_long_term_situation_count'])
        self.assertEqual(trace.report()['status'],'INACTIVE')
        self.assertFalse(trace.report()['runtime_descriptors_temporarily_modified'])

    def test_full_school_day_covers_374_events_without_truncation(self):
        classes, calls = native()
        trace = M110Trace()
        self.assertTrue(trace.start(classes))
        for _ in range(187):
            classes['weekly_day'].get_long_term_situation_count(None, None)
        self.assertTrue(trace.stop())
        report = trace.report()
        self.assertEqual(report['event_total'], 374)
        self.assertEqual(report['events_kept'], 374)
        self.assertFalse(report['event_details_truncated'])

    def test_school_count_records_which_native_situation_was_counted(self):
        classes, calls = native()
        trace = M110Trace()
        self.assertTrue(trace.start(classes))
        data = type('ScheduleRow', (object,), {
            'situation': type('Base', (object,), {'guid64': 277733})()
        })()
        self.assertEqual(
            classes['weekly_day'].get_long_term_situation_count(data, None),
            (6, 6))
        self.assertTrue(trace.stop())
        self.assertEqual(
            trace.report()['events'][0]['related_situation_guid'], 277733)
        self.assertEqual(
            trace.report()['events'][1]['ea_count_pair'], [6, 6])

    def test_try_start_related_situation_and_return_value_state(self):
        classes, calls = native()
        phase = classes['weekly_data']
        phase.situation = type('EAType', (object,), {'guid64': 304565})()
        trace = M110Trace()
        self.assertTrue(trace.start(classes))
        self.assertEqual(phase.try_start([], None, 15, [], {}), 123456)
        self.assertTrue(trace.stop())
        events = trace.report()['events']
        self.assertEqual(events[0]['related_situation_guid'], 304565)
        self.assertEqual(events[1]['ea_return_state'], 'POSITIVE_INT')
        self.assertNotIn('ea_return_id', events[1])

    def test_capped_events_never_contain_sim_ids_or_names(self):
        classes,_=native()
        trace=M110Trace()
        self.assertTrue(trace.start(classes))
        for _ in range(EVENT_LIMIT+10):
            classes['weekly_day'].get_long_term_situation_count(None,None)
        report=trace.report()
        self.assertEqual(report['events_kept'],EVENT_LIMIT)
        self.assertEqual(report['event_counts']['get_long_term_situation_count'],EVENT_LIMIT+10)
        self.assertFalse(any('sim' in str(x).lower() for x in report['events']))
        self.assertTrue(trace.stop())


if __name__=='__main__':
    unittest.main()
