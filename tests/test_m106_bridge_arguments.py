"""M106 school-only filter proposal tests; not a game runtime hook."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for folder in ('m93_core','m105_day_controller','m106_roster_first'):
    sys.path.insert(0,str(ROOT/'src'/folder))
from mhs106_bridge_arguments import propose_school_only_filter_arguments as propose
from mhs106_roster_first_policy import propose_roster_first
from mhs105_atomic_school_roster import BASE_JOB

CLASSES=(tuple(str(i) for i in range(1,9)),tuple(str(i) for i in range(9,17)))
PLAYABLE=('1','9','10')
NPC=[sid for group in CLASSES for sid in group if sid not in PLAYABLE]
FILTERS={BASE_JOB:tuple(sid for sid in NPC if sid!='16'),
         278965:('2','16'),278966:('3',),278967:('4',),
         278968:('11',),303765:()}
PINS={278965:'16',278966:'3',278967:'4',278968:'11',303765:'12'}
PLAN=propose_roster_first(CLASSES,PLAYABLE,FILTERS,PINS)


class CoreFilterProposalTests(unittest.TestCase):
    def request(self,guid,args=(1,'EA_MEAN_FILTER'),kwargs=None,**scope):
        verified={'school':True,'same_save':True,'same_day':True,
                  'native_bouncer':True}
        verified.update(scope)
        return propose(PLAN,guid,args,kwargs or {},'EA_BASE_FILTER',
                       **verified)

    def test_mean_candidate_school_only_replaces_filter_not_traits(self):
        self.assertEqual(PLAN['status'],'BRIDGE_CANDIDATE_ONLY_NOT_EA_BOUND')
        action,args,kwargs,reason=self.request(303766)
        self.assertEqual(action,'PROPOSAL_ONLY')
        self.assertEqual(args,(1,'EA_BASE_FILTER'))
        self.assertEqual(kwargs['sim_constraints'],(12,))
        self.assertFalse(kwargs['conform_if_constraints_fail'])
        self.assertFalse(kwargs['continue_if_constraints_fail'])
        self.assertFalse(PLAN['adapter_authorized'])
        self.assertFalse(PLAN['traits_mutated'])
        self.assertIn('binding unproved',reason)

    def test_original_eligible_cheer_keeps_its_real_filter(self):
        action,args,kwargs,_=self.request(276592,(1,'EA_CHEER_FILTER'))
        self.assertEqual(action,'PROPOSAL_ONLY')
        self.assertEqual(args,(1,'EA_CHEER_FILTER'))
        self.assertEqual(kwargs['sim_constraints'],(16,))

    def test_never_rewrite_outside_original_school_bouncer(self):
        for gate in ('school','same_save','same_day','native_bouncer'):
            action,args,kwargs,_=self.request(303766,**{gate:False})
            self.assertEqual(action,'PRESERVE')
            self.assertEqual(args,(1,'EA_MEAN_FILTER'))
            self.assertEqual(kwargs,{})

    def test_preserve_explicit_target_and_ambiguous_ea_count(self):
        for args,kwargs in (
                ((1,'EA_MEAN_FILTER'),{'sim_constraints':(999,)}),
                ((1,'EA_MEAN_FILTER'),{'sim_constraints':(12,)}),
                ((2,'EA_MEAN_FILTER'),{}),
                ((1,'EA_MEAN_FILTER'),{'number_of_sims_to_find':1})):
            action,after_args,after_kwargs,_=self.request(303766,args,kwargs)
            self.assertEqual(action,'PRESERVE')
            self.assertEqual(after_args,args)
            self.assertEqual(after_kwargs,kwargs)

    def test_staff_and_unrelated_filters_cannot_be_overridden(self):
        for guid in (0,1234,280516,280457):
            action,_,_,_=self.request(guid)
            self.assertEqual(action,'PRESERVE')

    def test_no_false_approval_of_unverified_plan(self):
        invalid=dict(PLAN,adapter_authorized=True)
        action,_,_,_=propose(
            invalid,303766,(1,'EA_MEAN_FILTER'),{},'EA_BASE_FILTER',
            school=True,same_save=True,same_day=True,native_bouncer=True)
        self.assertEqual(action,'PRESERVE')


if __name__=='__main__':
    unittest.main()
