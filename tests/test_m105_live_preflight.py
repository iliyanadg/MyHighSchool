"""Test M105 pre-travel EA SimFilter preflight without importing the game."""
import ast
from itertools import combinations
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
for loc in ('m105_day_controller','m93_core','m101_original_slot'):
    sys.path.insert(0,str(ROOT/'src'/loc))
from mhs93_verified_jobs import VERIFIED_SPECS
from mhs101_original_slot_gate import validated_filter_ids
from mhs105_atomic_school_roster import plan_school_day,CORE_JOBS,BASE_JOB

PATH=ROOT/'src'/'m105_day_controller'/'mhs105_live_preflight.py'
SOURCE=PATH.read_text(encoding='utf-8')
FUNCTIONS={node.name:node for node in ast.parse(SOURCE).body
           if isinstance(node,ast.FunctionDef)}

CLASSES=(tuple(str(n) for n in range(1,9)),
         tuple(str(n) for n in range(9,17)))
PLAYABLE=('1','9','10')
NPCS=tuple(int(i) for group in CLASSES for i in group if i not in PLAYABLE)
PINS={278965:'2',278966:'3',278967:'4',278968:'11',303765:'12'}

def create_runtime(bad_guid=None,bad_kind=None,missing_roles=False):
    counters=[]
    def submit_filter(callback,sim_filter,sim_constraints,allow_yielding):
        counters.append((callback,sim_filter.guid,tuple(sim_constraints),allow_yielding))
        if bad_guid==sim_filter.guid:
            if bad_kind=='exception':
                raise TypeError('invalid native EA argument')
            if bad_kind=='unverified':
                return [SimpleNamespace(sim_info=SimpleNamespace(sim_id=2))]
            if bad_kind=='none':
                return None
            if bad_kind=='empty':
                return []
        return [SimpleNamespace(sim_info=SimpleNamespace(sim_id=i),score=1)
                for i in sim_constraints]
    class Manager:
        def get(self,guid):
            return SimpleNamespace(guid=guid)
    svc=SimpleNamespace(
        get_instance_manager=lambda resource:Manager(),
        sim_filter_service=lambda:SimpleNamespace(submit_filter=submit_filter))
    settings=SimpleNamespace(active=True,class_count=2)
    info=SimpleNamespace(age='TEEN',species='HUMAN')
    registry=SimpleNamespace(class_members=lambda index:CLASSES[index-1])
    saved_roles=SimpleNamespace(complete=not missing_roles,
        chosen=lambda:dict(PINS) if not missing_roles else {})
    household=SimpleNamespace(sim_info_gen=lambda:(SimpleNamespace(
        sim_id=int(i),age='TEEN',species='HUMAN') for i in PLAYABLE))
    game=SimpleNamespace(active_household=lambda:household,
        sim_info_manager=lambda:SimpleNamespace(get=lambda sid:info))
    values={
       'services':SimpleNamespace(**vars(svc),**vars(game)),
       'Types':SimpleNamespace(SIM_FILTER=17),
       'Age':SimpleNamespace(TEEN='TEEN'),
       'Species':SimpleNamespace(HUMAN='HUMAN'),
       'current_slot':lambda allow_travel:11,
       '_SETTINGS':SimpleNamespace(load=lambda slot:settings),
       '_ROSTER':SimpleNamespace(load=lambda slot:registry),
       '_ROLES':SimpleNamespace(load=lambda slot:saved_roles),
       'VERIFIED_SPECS':VERIFIED_SPECS,
       'ALL_JOBS':(277894,278965,278966,278967,278968,303765),
       'validated_filter_ids':validated_filter_ids,
       'plan_school_day':plan_school_day,
       'CORE_JOBS':CORE_JOBS,'BASE_JOB':BASE_JOB,
       'combinations':combinations,
       '_DIAGNOSTIC_ROLE_NAMES':(
           (278965,'Cheerleader'),(278966,'Scacchi'),
           (278967,'Football'),(278968,'Informatica'),
           (303765,'Sim perfido'))}
    for key in ('_result','_teen','_base_data','_query_ea_filters',
                'prepare_live_school_day','diagnose_live_role_choices'):
        code=compile(ast.Module(body=[FUNCTIONS[key]],type_ignores=[]),
                     str(PATH),'exec')
        exec(code,values)
    return values,counters

class M105NativePreflightTests(unittest.TestCase):
    def test_six_real_ea_filters_scored_and_without_sim_creation(self):
        env,calls=create_runtime()
        result=env['prepare_live_school_day']()
        self.assertEqual(result['status'],'PREFLIGHT_READY_NOT_EA_BOUND')
        self.assertEqual(result['plan']['base_invites_needed'],8)
        self.assertEqual(result['plan']['playable_count'],3)
        self.assertEqual(result['plan']['core_count'],5)
        self.assertFalse(result['ea_overrides_installed'])
        self.assertFalse(result['ea_school_roles_bound'])
        self.assertEqual(len(calls),6)
        self.assertEqual(set(g for _,g,_,_ in calls),
                         set(spec[0] for spec in VERIFIED_SPECS.values()))
        self.assertTrue(all(callback is None and ids==NPCS
                            and allow_yielding is False
                            for callback,_,ids,allow_yielding in calls))

    def test_native_query_exception_preserves_vanilla(self):
        env,calls=create_runtime(276594,'exception')
        result=env['prepare_live_school_day']()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['filter_details']['reason'],
                         'EA filter query failed')
        self.assertEqual(result['filter_details']['error_type'],'TypeError')
        self.assertFalse(result['ea_overrides_installed'])
        self.assertEqual(len(calls),4)

    def test_unscored_result_and_deferred_result_fail_closed(self):
        for kind in ('unverified','none'):
            env,calls=create_runtime(280516,kind)
            result=env['prepare_live_school_day']()
            self.assertEqual(result['status'],'BLOCKED',kind)
            self.assertFalse(result['students_spawned'])

    def test_zero_role_candidates_cannot_be_converted_to_fake_eligibility(self):
        env,calls=create_runtime(276592,'empty')
        result=env['prepare_live_school_day']()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('not eligible',result['plan_reason'].lower())

    def test_missing_manual_roles_does_not_call_game_filter(self):
        env,calls=create_runtime(missing_roles=True)
        result=env['prepare_live_school_day']()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('manual',result['reason'])
        self.assertEqual(calls,[])

    def test_diagnose_real_ea_eligibility_and_propose_without_saving(self):
        env,calls=create_runtime()
        filtered={job:tuple(str(sid) for sid in NPCS) for job in
                  (BASE_JOB,)+CORE_JOBS}
        # A menu-appointed Cheerleader does NOT pass the actual EA filter.
        filtered[278965]=tuple(sid for sid in filtered[278965] if sid!='2')
        inspections=[]
        def read_filters(ordinary):
            inspections.append(tuple(ordinary))
            return filtered,{'calls':{}}
        env['_query_ea_filters']=read_filters
        lines=env['diagnose_live_role_choices']()
        summary='\\n'.join(lines)
        self.assertIn('Cheerleader: ID 2 NON IDONEO',summary)
        self.assertIn('Cheerleader -> ID 5',summary)
        self.assertIn('Studenti Base EA idonei: 13/13',summary)
        self.assertIn('PROPOSTA (non salvata',summary)
        self.assertEqual(len(inspections),1)
        self.assertEqual(len(calls),0) # mock filters only, zero mutators

    def test_diagnose_no_solution_when_under_eight_base_candidates(self):
        env,_=create_runtime()
        filtered={job:tuple(str(sid) for sid in NPCS) for job in
                  (BASE_JOB,)+CORE_JOBS}
        filtered[BASE_JOB]=filtered[BASE_JOB][:7]
        env['_query_ea_filters']=lambda ordinary:(filtered,{'calls':{}})
        summary='\\n'.join(env['diagnose_live_role_choices']())
        self.assertIn('Studenti Base EA idonei: 7/13',summary)
        self.assertIn('NESSUN piano 5 Core + 8 Base',summary)

    def test_no_game_mutators_or_situation_hooks_in_preflight(self):
        self.assertNotIn('create_situation(',SOURCE)
        self.assertNotIn('spawn_sim(',SOURCE)
        self.assertNotIn('setattr(SimFilterService',SOURCE)
        self.assertNotIn('change_role(',SOURCE)
        self.assertNotIn('install(',SOURCE)

if __name__=='__main__':
    unittest.main()
