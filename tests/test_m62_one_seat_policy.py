"""M62 pure policy: preserve working EA lessons until a validated, single seat exists."""
import ast
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m58_selection'))
from mhs62_one_seat_policy import plan_one_registered_base_guest

ROSTER=tuple(str(x) for x in range(1,17))
BASE=[(277894,0)]

def plan(**kwargs):
    args={'situation_guid':277733,
          'job_guests':BASE,
          'ordered_registered_ids':ROSTER,
          'verified_eligible_ids':['4','5','6'],
          'verified_school_zone':True,
          'active':True}
    args.update(kwargs)
    return plan_one_registered_base_guest(**args)

class M62OneSeatPolicyTests(unittest.TestCase):
    def test_one_verified_student_from_registry_is_only_a_plan(self):
        choice=plan(present_ids=['4'],occupied_role_ids=['5'])
        self.assertEqual(choice,{'action':'candidate','candidate_id':'6',
                                 'kind':'plan-only','requested_count':1})
        self.assertEqual(BASE,[(277894,0)])
    def test_never_override_explicit_guest_or_other_school_jobs(self):
        self.assertEqual(plan(job_guests=[(277894,17)])['action'],'preserve')
        self.assertEqual(plan(job_guests=[])['action'],'preserve')
        self.assertEqual(plan(job_guests=[(277895,0)])['action'],'preserve')
        self.assertEqual(plan(situation_guid=298052)['action'],'preserve')
        self.assertEqual(plan(situation_guid=298096)['action'],'preserve')
        self.assertEqual(plan(job_guests=[(277894,0),(277894,0)])['action'],'preserve')
    def test_school_zone_activation_and_eligibility_require_verified_evidence(self):
        self.assertEqual(plan(active=False)['action'],'preserve')
        self.assertEqual(plan(verified_school_zone=False)['action'],'preserve')
        self.assertEqual(plan(verified_eligible_ids=None)['action'],'preserve')
        self.assertEqual(plan(verified_eligible_ids=['99'])['action'],'preserve')
        self.assertEqual(plan(ordered_registered_ids=['4','4'])['action'],'preserve')
        self.assertEqual(plan(verified_eligible_ids=['oops'])['action'],'preserve')
    def test_never_steal_playables_or_already_present_students(self):
        self.assertEqual(plan(playable_ids=['4','5','6'],
                              verified_eligible_ids=['4','5','6'])['action'],
                         'preserve')
        self.assertEqual(plan(present_ids=['4','5','6'])['action'],'preserve')
        self.assertEqual(plan(occupied_role_ids=['4','5','6'])['action'],'preserve')
        self.assertEqual(plan(verified_eligible_ids=['4','5'],
                              occupied_role_ids=['4'],
                              present_ids=['5'])['action'],'preserve')
    def test_only_pure_offline_code_no_ea_side_effects(self):
        src=(ROOT/'src'/'m58_selection'/'mhs62_one_seat_policy.py').read_text()
        ast.parse(src)
        for forbidden in ('import services','import alarms','create_situation(',
                          'add_guest_info(', 'remove_guest_info(', 'setattr(',
                          'os.remove(', 'create_student_request('):
            self.assertNotIn(forbidden,src)

class M62IsolationRegressionTests(unittest.TestCase):
    def test_known_good_build_does_not_constrain_school_filters(self):
        src=(ROOT/'src'/'m57_selection'/'mhs57_filter_runtime.py').read_text()
        ast.parse(src)
        self.assertIn('MHS_EA_FILTER_CONSTRAINTS_ENABLED=False',src)
        # Prevent accidentally shipping a build that reactivates M57/M60.
        tree=ast.parse(src)
        flags=[node for node in tree.body if isinstance(node,ast.Assign)
               and any(isinstance(t,ast.Name) and
                       t.id=='MHS_EA_FILTER_CONSTRAINTS_ENABLED'
                       for t in node.targets)]
        self.assertEqual(len(flags),1)
        self.assertIsInstance(flags[0].value,ast.Constant)
        self.assertIs(flags[0].value.value,False)

    def test_disabled_school_filter_passes_through_unmodified(self):
        src=(ROOT/'src'/'m57_selection'/'mhs57_filter_runtime.py').read_text()
        tree=ast.parse(src)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                and n.name=='_filtered')
        calls=[]
        def original(self,*args,**kwargs):
            calls.append((self,args,kwargs))
            return 'EA unchanged'
        def forbidden(*args,**kwargs):
            raise AssertionError('isolation must not consult registry/policy')
        ctx={
            'guid_for_filter':lambda f:f.guid64,
            'SCHOOL_FILTERS':{280516,296396},
            'MHS_EA_FILTER_CONSTRAINTS_ENABLED':False,
            '_record_filter_call':lambda *args:None,
            '_manifest':forbidden,
            'apply_constraints':forbidden,
        }
        exec(compile(ast.Module(body=[fn],type_ignores=[]),
                     '<M62 isolation regression>', 'exec'),ctx)
        token=object()
        kw={'sim_filter':type('SchoolFilter',(),{'guid64':280516})(),
            'number_of_sims_to_find':6}
        self.assertEqual(ctx['_filtered'](original,token,(),kw,'filter'),
                         'EA unchanged')
        self.assertEqual(calls,[(token,(),kw)])
        self.assertNotIn('sim_constraints',kw)

    def test_m55_additive_invitation_stays_disabled_when_m57_installed(self):
        src=(ROOT/'src'/'m55_attendance'/'mhs55_attendance_auto.py').read_text()
        tree=ast.parse(src)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                and n.name=='_tick')
        self.assertIn('mhs57_filter_runtime.installed()',ast.get_source_segment(src,fn))
        self.assertIn('_process(current, situation_mgr, sim_mgr)',
                      ast.get_source_segment(src,fn))

if __name__=='__main__':
    unittest.main()
