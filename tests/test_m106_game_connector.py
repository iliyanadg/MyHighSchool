"""AST-isolated checks of M106 EA game-facing connector."""
import ast
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src'/'m106_roster_first'/'mhs106_game_controller.py'
CODE=SRC.read_text()
FN={node.name:node for node in ast.parse(CODE).body
    if isinstance(node,ast.FunctionDef)}

def compile_one(name,env):
    exec(compile(ast.Module(body=[FN[name]],type_ignores=[]),
                 str(SRC),'exec'),env)
    return env[name]


class GameControllerTests(unittest.TestCase):
    def test_native_bridge_calls_m57_original_exactly_once(self):
        calls=[]
        session=SimpleNamespace(
            decide=lambda *a,**k:('CONSTRAIN',(1,'EA_BASE'),{
                'sim_constraints':(101,)}),
            evidence=lambda:{'core_requests_constrained':1,
                'actual_attendance_verified':False})
        def old(original,service,args,kwargs,mode):
            calls.append((args,kwargs,mode))
            return 'EA_RESULT'
        env={'_SESSION':session,'_OLD_FILTER':old,
             '_BASE_TUNING':'EA_BASE','_LAST':{},'_save':lambda:None,
             'guid_for_filter':lambda x:303766,
             'current_slot':lambda allow_travel:11,
             '_day':lambda:20,'_zone':lambda:'200',
             '_original_bouncer_origin':lambda:True,
             '_school_schedule_verified':lambda:True}
        result=compile_one('_filtered',env)(
            None,None,(1,'EA_MEAN'),{},'matching')
        self.assertEqual(result,'EA_RESULT')
        self.assertEqual(calls,[( (1,'EA_BASE'),{
            'sim_constraints':(101,)},'matching')])
        self.assertFalse(env['_LAST']['actual_attendance_verified'])

    def test_malformed_context_never_calls_ea_twice(self):
        calls=[]
        def old(o,s,args,kwargs,mode):
            calls.append(args)
            return 'VANILLA'
        def broken(*a,**k):
            raise RuntimeError('EA venue unavailable')
        env={'_SESSION':SimpleNamespace(decide=broken),
             '_OLD_FILTER':old,'_BASE_TUNING':None,
             '_LAST':{},'_save':lambda:None,
             'guid_for_filter':lambda x:303766,
             'current_slot':lambda allow_travel:11,
             '_day':lambda:20,'_zone':lambda:'201',
             '_original_bouncer_origin':lambda:False,
             '_school_schedule_verified':lambda:False}
        fn=compile_one('_filtered',env)
        self.assertEqual(fn(None,None,(1,'EA_MEAN'),{},'matching'),'VANILLA')
        self.assertEqual(calls,[(1,'EA_MEAN')])
        self.assertEqual(env['_LAST']['status'],'EA_CALL_CONTEXT_UNVERIFIED')

    def test_outside_arm_controller_is_inert(self):
        called=[]
        env={'_SESSION':None,'_OLD_FILTER':lambda *a:called.append(a) or 'EA'}
        fn=compile_one('_filtered',env)
        self.assertEqual(fn(None,None,(1,'EA'),{},'matching'),'EA')
        self.assertEqual(len(called),1)

    def test_arm_has_no_changes_on_preflight_failure(self):
        ns={'_SESSION':None,'_LAST':{},
            'prepare_live_roster_first':lambda:{'status':'BLOCKED',
                'reason':'No valid sixteen'},
            '_save':lambda:None,
            'human_summary':lambda r:'M106 BLOCCATA: '+r['reason']}
        message=compile_one('arm',ns)()
        self.assertIn('No valid sixteen',message)
        self.assertEqual(ns['_LAST']['status'],'PREFLIGHT_BLOCKED')

    def test_check_is_not_false_attendance_certificate(self):
        self.assertIn('16 presenze NON provate',CODE)
        self.assertNotIn('create_situation(',CODE)
        self.assertNotIn('add_trait(',CODE)
        self.assertNotIn('setattr(',CODE)


if __name__=='__main__':
    unittest.main()
