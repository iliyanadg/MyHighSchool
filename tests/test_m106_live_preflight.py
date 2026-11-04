"""M106 live bridge reads original Sims filter evidence, without Sims runtime."""
import ast
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for directory in ('m93_core','m105_day_controller','m106_roster_first'):
    sys.path.insert(0,str(ROOT/'src'/directory))
from mhs106_roster_first_policy import propose_roster_first
from mhs105_atomic_school_roster import ALL_JOBS,BASE_JOB

PATH=ROOT/'src'/'m106_roster_first'/'mhs106_live_preflight.py'
SOURCE=PATH.read_text(encoding='utf-8')
FN={x.name:x for x in ast.parse(SOURCE).body if isinstance(x,ast.FunctionDef)}
GROUPS=(tuple(str(x) for x in range(1,9)),
        tuple(str(x) for x in range(9,17)))
PLAYED=('1','9','10')
NPC=tuple(int(sid) for group in GROUPS for sid in group if sid not in PLAYED)
ROLES={278965:'16',278966:'3',278967:'4',278968:'11',303765:'12'}
FILTERS={
    BASE_JOB:tuple(str(sid) for sid in NPC if sid!=16),
    278965:('2','16'),278966:('3',),278967:('4',),
    278968:('11',),303765:()
}

def compile_functions(ns):
    for method in ('prepare_live_roster_first','human_summary'):
        exec(compile(ast.Module(body=[FN[method]],type_ignores=[]),
                     str(PATH),'exec'),ns)
    return ns

def fake_env(state='LOCAL_REGISTRY_VERIFIED',filter_results=FILTERS,
             assigned_roles=None):
    calls=[]
    local={'status':state,'classes':GROUPS,
           'playable':PLAYED,'save_slot':'11',
           'assigned_roles':dict(ROLES if assigned_roles is None
                                 else assigned_roles)}
    def query(ordinary):
        calls.append(tuple(ordinary))
        return filter_results,{'calls':{'original_ea_filters':6}}
    env=compile_functions({
        '_base_data':lambda:local,
        '_query_ea_filters':query,
        'propose_roster_first':propose_roster_first
    })
    return env,calls

class LiveRosterFirstTests(unittest.TestCase):
    def test_real_live_input_prepares_fixed_sixteen_without_mean_filter(self):
        env,calls=fake_env()
        result=env['prepare_live_roster_first']()
        self.assertEqual(result['status'],'ROSTER_FIRST_CANDIDATE_ONLY')
        self.assertTrue(result['manual_roles_preserved'])
        self.assertEqual(result['plan']['all_16'],GROUPS[0]+GROUPS[1])
        self.assertEqual(result['plan']['school_only_bridge_count'],1)
        self.assertEqual(result['plan']['school_only_bridge_candidates'],
                         ((303765,'12'),))
        self.assertEqual(calls,[NPC])
        self.assertIn('16 presenze NON verificate',env['human_summary'](result))
        for key in ('game_modified','ea_filters_modified',
                    'core_jobs_reserved','ea_role_binding_verified',
                    'base_count_overridden','lot_capacity_verified',
                    'attendance_verified'):
            self.assertFalse(result[key])

    def test_optimizer_cannot_silently_change_a_selected_core_sim(self):
        # Sim 16 fails EA Base; only Core cheer accepts them. A naive
        # optimizer moves the player's selected Sim 2 out of cheer.
        # Experimental live M106 must block rather than change that choice.
        selected=dict(ROLES)
        selected[278965]='2'
        env,calls=fake_env(assigned_roles=selected)
        result=env['prepare_live_roster_first']()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('manual EA Core role assignments',result['reason'])
        self.assertFalse(result['game_modified'])
        self.assertFalse(result['attendance_verified'])
        self.assertFalse(result['manual_roles_preserved'])
        self.assertEqual(calls,[NPC])

    def test_registry_block_does_not_query_ea(self):
        env,calls=fake_env(state='BLOCKED')
        result=env['prepare_live_roster_first']()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(calls,[])

    def test_missing_native_ea_eligibility_fails_closed(self):
        env,calls=fake_env(filter_results=None)
        result=env['prepare_live_roster_first']()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('EA SimFilter eligibility unavailable',result['reason'])
        self.assertEqual(len(calls),1)

    def test_unsatisfiable_fixed_roster_is_not_assumed_eligible(self):
        f=dict(FILTERS)
        f[BASE_JOB]=('2','3','4')
        env,calls=fake_env(filter_results=f)
        result=env['prepare_live_roster_first']()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('fewer than eight',result['reason'])
        self.assertEqual(len(calls),1)

    def test_no_trait_changes_situation_spawns_or_ea_hooks(self):
        for banned in ('create_situation(', 'spawn_sim(', 'add_trait(',
                       'remove_trait(', 'setattr(', 'install_filter_hooks('):
            self.assertNotIn(banned,SOURCE)


if __name__=='__main__':
    unittest.main()
