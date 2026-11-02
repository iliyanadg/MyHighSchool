"""M105 game-side, read-only EA CoreClassNPC role binding inspection."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m105_day_controller'))
from mhs105_atomic_school_roster import plan_school_day,ALL_JOBS,CORE_JOBS
from mhs105_live_core_binding import inspect_core_jobs

A=tuple(str(i) for i in range(1,9))
B=tuple(str(i) for i in range(9,17))
PLAYABLE=('1','9','10')
NPCS=tuple(s for s in A+B if s not in PLAYABLE)
PINS=dict(zip(CORE_JOBS,('2','3','4','11','12')))
PLAN=plan_school_day((A,B),PLAYABLE,{job:NPCS for job in ALL_JOBS},PINS)

def sample(known=True,misassigned=False,other=False):
    assignments={int(s):job for job,s in PINS.items()}
    if misassigned:
        assignments[2]=278966
    sims={}
    infos=[]
    for sid in (2,3,4,11,12)+( (99,) if other else ()):
        sim=SimpleNamespace(sim_id=sid)
        sims[sid]=sim
        infos.append(SimpleNamespace(sim_id=sid,age='TEEN',species='HUMAN',
                     get_sim_instance=lambda sim=sim:sim))
    class CoreSituation:
        guid64=298052
        def get_job_for_sim(self,sim):
            job=assignments.get(sim.sim_id)
            return SimpleNamespace(guid64=job) if job is not None else None
    situation=CoreSituation()
    if not known:
        situation=SimpleNamespace(guid64=298052)
    manager=SimpleNamespace(
        get_situations_sim_is_in=lambda sim:(situation,))
    return infos,manager

def probe(infos=None,manager=None,**options):
    if infos is None and manager is None:
        infos,manager=sample()
    flags={'school_verified':True,'save_verified':True,'day_verified':True}
    flags.update(options)
    return inspect_core_jobs(PLAN,infos,manager,'TEEN','HUMAN',**flags)

class LiveEACoreProbeTests(unittest.TestCase):
    def test_five_actual_job_members_are_distinct_and_on_zone(self):
        r=probe()
        self.assertEqual(r['status'],'FIVE_ACTUAL_EA_CORE_MEMBERS_VERIFIED')
        self.assertTrue(r['actual_ea_core_binding_verified'])
        self.assertFalse(r['before_school_spawn_reservation_proved'])

    def test_missing_job_getter_unknown_not_a_successful_binding(self):
        infos,manager=sample(known=False)
        r=probe(infos,manager)
        self.assertEqual(r['status'],'UNKNOWN')
        self.assertIn('job APIs',r['reason'])
        self.assertFalse(r['actual_ea_core_binding_verified'])

    def test_wrong_role_is_rejected_even_when_sim_on_zone(self):
        infos,manager=sample(misassigned=True)
        r=probe(infos,manager)
        self.assertEqual(r['status'],'NOT_VERIFIED')
        self.assertFalse(r['actual_ea_core_binding_verified'])

    def test_unknown_extra_member_in_core_is_not_ignored(self):
        infos,manager=sample(other=True)
        r=probe(infos,manager)
        self.assertEqual(r['status'],'UNKNOWN')
        self.assertEqual(r['unreadable_core_members'],1)

    def test_unavailable_ea_membership_service_or_wrong_context(self):
        self.assertEqual(probe(school_verified=False)['status'],'UNKNOWN')
        infos,manager=sample()
        manager=SimpleNamespace()
        self.assertEqual(probe(infos,manager)['status'],'UNKNOWN')

    def test_no_modifying_game_functions(self):
        src=(ROOT/'src'/'m105_day_controller'/
             'mhs105_live_core_binding.py').read_text()
        for forbidden in ('create_situation(','.spawn_sim(','.destroy_situation',
                          '.add_guest_info(','.set_job('):
            self.assertNotIn(forbidden,src)

if __name__=='__main__':
    unittest.main()
