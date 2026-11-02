"""Unit tests for exact live-EA-filter diagnostics in M101b, without Sims imports."""
import ast
import inspect
import os
import sys
import types
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m101_original_slot'))
from mhs101_original_slot_gate import validated_filter_ids

FILE=Path('src/m101_original_slot/mhs101_original_slot_runtime.py')
SRC=FILE.read_text(encoding='utf-8')
NODE=next(n for n in ast.parse(SRC).body
          if isinstance(n,ast.FunctionDef) and n.name=='_actual_filter_ids')

def run_filter(manager=None,service=None,resource_type='SIM_FILTER'):
    types_obj=types.SimpleNamespace()
    if resource_type:
        setattr(types_obj,resource_type,42)
    services_obj=types.SimpleNamespace(
        get_instance_manager=lambda _:manager,
        sim_filter_service=lambda :service)
    namespace={'services':services_obj,'Types':types_obj,
               '_FILTER':280516,
               'validated_filter_ids':validated_filter_ids,
               'inspect':inspect,'os':os}
    executable=compile(ast.Module(body=[NODE],type_ignores=[]),
                       '<m101b-runtime-filter>','exec')
    exec(executable,namespace)
    return namespace['_actual_filter_ids']((555,777))

def manager(tuning=True):
    return types.SimpleNamespace(get=lambda key:object() if tuning else None)
class M101bFilterEvidenceTests(unittest.TestCase):
    def test_no_resource_type_is_not_mistaken_for_no_eligible_teens(self):
        ids,diagnostic=run_filter(manager=manager(),service=object(),
                                  resource_type=None)
        self.assertEqual(ids,())
        self.assertEqual(diagnostic['phase'],'MISSING_SIM_FILTER_RESOURCE_TYPE')

    def test_tuning_absent_and_service_absent_have_distinct_phases(self):
        ids,a=run_filter(manager=manager(False),service=object())
        self.assertEqual(a['phase'],'MISSING_EA_BASE_FILTER_TUNING')
        ids,b=run_filter(manager=manager(),service=None)
        self.assertEqual(b['phase'],'NO_EA_FILTER_SERVICE')

    def test_missing_submit_method_is_reported(self):
        _,record=run_filter(manager=manager(),service=object())
        self.assertEqual(record['phase'],'NO_SUBMIT_FILTER_METHOD')

    def test_query_exception_is_not_labeled_all_students_ineligible(self):
        def throw(**kwargs):
            raise TypeError('EA signature not compatible')
        _,record=run_filter(manager=manager(),
            service=types.SimpleNamespace(submit_filter=throw))
        self.assertEqual(record['phase'],'EA_FILTER_QUERY_EXCEPTION')
        self.assertEqual(record['exception_type'],'TypeError')
        self.assertEqual(record['exception_message'],
                         'EA signature not compatible')
        self.assertIn('method_signature',record)
        self.assertEqual(record['runtime_source'],
                         'M101C_EA_FILTER_DIAGNOSTICA')
        self.assertEqual(record['exception_location']['function'],'throw')

    def test_none_and_empty_are_different_from_bad_result_type(self):
        for returned,phase in (
                (None,'EA_FILTER_RETURNED_NONE'),
                ([], 'EA_FILTER_RETURNED_EMPTY'),
                ({'a':1},'EA_FILTER_UNEXPECTED_RESULT_TYPE')):
            _,record=run_filter(manager=manager(),
                service=types.SimpleNamespace(
                    submit_filter=lambda **_:returned))
            self.assertEqual(record['phase'],phase)

    def test_real_scored_result_sets_proved_eligibility(self):
        result=types.SimpleNamespace(sim_info=types.SimpleNamespace(sim_id=555),
                                     score=5.0)
        ids,record=run_filter(manager=manager(),service=types.SimpleNamespace(
            submit_filter=lambda **_:[result]))
        self.assertEqual(ids,(555,))
        self.assertEqual(record['phase'],'EA_FILTER_VERIFIED_MATCH')
        self.assertEqual(record['eligible_count'],1)

    def test_unscored_objects_do_not_pass(self):
        result=types.SimpleNamespace(sim_info=types.SimpleNamespace(sim_id=555))
        ids,record=run_filter(manager=manager(),service=types.SimpleNamespace(
            submit_filter=lambda **_:[result]))
        self.assertEqual(ids,())
        self.assertEqual(record['phase'],'EA_FILTER_RESULTS_NOT_VERIFIED')
        self.assertFalse(record['sample_has_score'])

if __name__=='__main__':
    unittest.main()
