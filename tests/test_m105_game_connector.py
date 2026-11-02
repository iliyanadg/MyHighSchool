"""M105 native runtime binding: read-only school identity and safety checks.

Execute game-controller method bodies without EA Sims runtime. The source
is NOT bundled into a Mac release until these tests and EA capacity checks
are complete.
"""
import ast
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'src'/'m105_day_controller'/'mhs105_game_controller.py'
SOURCE=PATH.read_text(encoding='utf-8')
FN={n.name:n for n in ast.parse(SOURCE).body
    if isinstance(n,ast.FunctionDef)}

def compile_fn(name,namespace):
    exec(compile(ast.Module(body=[FN[name]],type_ignores=[]),
                 str(PATH),'exec'),namespace)
    return namespace[name]

class ControllerTests(unittest.TestCase):
    def test_only_two_known_real_ea_school_schedules_are_accepted(self):
        namespace={'_EA_SCHOOL_SCHEDULES':frozenset((277657,279958))}
        for guid,expected in ((277657,True),(279958,True),
                              (99999,False),(None,False)):
            director=SimpleNamespace(
                _schedule=SimpleNamespace(guid64=guid))
            namespace['services']=SimpleNamespace(
                venue_service=lambda:SimpleNamespace(
                    get_zone_director=lambda:director))
            func=compile_fn('_school_schedule_verified',namespace)
            self.assertIs(func(),expected)

    def test_missing_venue_or_school_schedule_fails_closed(self):
        for service in (None,SimpleNamespace(get_zone_director=lambda:None)):
            namespace={'_EA_SCHOOL_SCHEDULES':frozenset((277657,279958)),
                       'services':SimpleNamespace(venue_service=lambda:service)}
            self.assertFalse(compile_fn('_school_schedule_verified',namespace)())

    def test_original_filter_not_called_twice_when_rewrite_succeeds(self):
        core_calls=[]
        session=SimpleNamespace(
            constrain=lambda *args,**kwargs:(
                'constrain',(1,'EA_TUNING'),
                {'sim_constraints':(17,)}),
            evidence=lambda:{'core_requests_constrained':1})
        def delegated(original,service,args,kwargs,mode):
            core_calls.append((args,kwargs,mode))
            return 'ORIGINAL_EA_RESULT'
        namespace={
            '_SESSION':session,'_OLD_FILTER':delegated,
            '_LAST':{},'_save':lambda:None,
            'EXPECTED_SCHOOL_FILTERS':frozenset((276592,280516)),
            'guid_for_filter':lambda _:276592,
            'current_slot':lambda allow_travel:11,
            '_day':lambda:13,'_zone':lambda:'201',
            '_original_bouncer_origin':lambda:True,
            '_school_schedule_verified':lambda:True}
        func=compile_fn('_filtered',namespace)
        result=func(object(),object(),(1,'EA_TUNING'),{},'matching')
        self.assertEqual(result,'ORIGINAL_EA_RESULT')
        self.assertEqual(len(core_calls),1)
        self.assertEqual(core_calls[0][1]['sim_constraints'],(17,))

    def test_unrelated_ea_filter_passes_unchanged(self):
        calls=[]
        def delegated(orig,svc,args,kwargs,mode):
            calls.append((args,kwargs,mode))
            return 'VANILLA'
        namespace={
            '_SESSION':object(),'_OLD_FILTER':delegated,
            'EXPECTED_SCHOOL_FILTERS':frozenset((276592,)),
            'guid_for_filter':lambda _:888888}
        fn=compile_fn('_filtered',namespace)
        self.assertEqual(fn(None,None,(1,'TUNING'),{'x':5},'matching'),
                         'VANILLA')
        self.assertEqual(calls,[( (1,'TUNING'),{'x':5},'matching')])

    def test_failed_context_uses_original_arguments_only_once(self):
        calls=[]
        def delegated(orig,svc,args,kwargs,mode):
            calls.append((args,kwargs))
            return 'VANILLA'
        def failure(**kwargs):
            raise RuntimeError('School zone not verified')
        namespace={
            '_SESSION':SimpleNamespace(constrain=failure),
            '_OLD_FILTER':delegated,'_LAST':{},'_save':lambda:None,
            'EXPECTED_SCHOOL_FILTERS':frozenset((276592,)),
            'guid_for_filter':lambda _:276592,
            'current_slot':lambda allow_travel:11,
            '_day':lambda:13,'_zone':lambda:'201',
            '_original_bouncer_origin':lambda:False,
            '_school_schedule_verified':lambda:False}
        fn=compile_fn('_filtered',namespace)
        self.assertEqual(fn(None,None,(1,'TUNING'),{},'matching'),'VANILLA')
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0],(1,'TUNING'))

    def test_other_high_school_controller_prevents_m105_hook(self):
        ns={}
        gate=compile_fn('_m57_compatible',ns)
        ok=SimpleNamespace(installed=lambda:True,
                           _filtered=lambda *a:None,_CONFLICTS=())
        conflict=SimpleNamespace(installed=lambda:True,
                                 _filtered=lambda *a:None,
                                 _CONFLICTS=('OtherHSController.ts4script',))
        missing=SimpleNamespace(installed=lambda:False,
                                _filtered=lambda *a:None,_CONFLICTS=())
        self.assertTrue(gate(ok))
        self.assertFalse(gate(conflict))
        self.assertFalse(gate(missing))

    def test_check_never_claims_ea_role_if_not_at_verified_school(self):
        captured={}
        session=SimpleNamespace(
            save_slot='11',sim_day=24,home_zone='100',
            evidence=lambda:{
                'core_requests_constrained':5,
                'base_student_targets_constrained':8,
                'school_zone':'401'})
        ns={'_SESSION':session,'_LAST':captured,'_REPORT':'report.json',
            '_save':lambda:None,
            'current_slot':lambda allow_travel:'11',
            '_day':lambda:24,'_zone':lambda:'100',
            '_school_schedule_verified':lambda:False}
        fn=compile_fn('check',ns)
        message=fn()
        self.assertIn('UNKNOWN',message)
        self.assertEqual(
            captured['actual_ea_core_role_evidence']['status'],'UNKNOWN')
        self.assertFalse(
            captured['actual_ea_core_role_evidence'][
                'actual_ea_core_binding_verified'])

    def test_no_situation_guest_change_or_slot_count_activated(self):
        self.assertNotIn('create_situation(',SOURCE)
        self.assertNotIn('SituationGuestList',SOURCE)
        self.assertNotIn('approved_base_count(',SOURCE)
        self.assertNotIn('spawn_sim(',SOURCE)

if __name__=='__main__':
    unittest.main()
