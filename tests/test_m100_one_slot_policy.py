"""M100 one original EA slot uses verified Base SimFilter IDs only."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m100_precreate'))
from mhs100_one_slot_policy import select_one,OneSlotPilot

GROUPS=(tuple(str(i) for i in range(1,9)),
        tuple(str(i) for i in range(9,17)))
PLAYABLE=('1','9','10')
def policy(**overrides):
    options=dict(original_guid=277733,original_guest_ids=(),
                 class_ids=GROUPS,playable_ids=PLAYABLE,
                 eligible_base_ids=('2','3','11'),already_on_zone_ids=(),
                 active_school=True,save_verified=True,
                 zone_verified=True,day_verified=True)
    options.update(overrides)
    return select_one(**options)

class SingleEASlotTests(unittest.TestCase):
    def test_first_eligible_registered_npc_is_chosen_without_new_invite(self):
        self.assertEqual(policy(),('choose',2,
                         'one EA-filter-qualified enrolled NPC'))
        self.assertEqual(policy(eligible_base_ids=('6','8')),(
                         'choose',6,'one EA-filter-qualified enrolled NPC'))

    def test_baby_ariel_not_assumed_eligible_just_because_enrolled(self):
        # ID 2 is a registered teenager, but if EA's true filter 280516
        # did NOT return it, the one-slot policy cannot choose it.
        self.assertEqual(policy(eligible_base_ids=('3',))[1],3)
        self.assertEqual(policy(eligible_base_ids=())[0],'block')

    def test_skip_playables_present_students_and_nonregistered_candidates(self):
        self.assertEqual(policy(eligible_base_ids=('1','9','10','99'))[0],'block')
        self.assertEqual(policy(already_on_zone_ids=('2','3'),
                                eligible_base_ids=('2','3','11'))[1],11)

    def test_original_guest_and_unrelated_job_must_remain_unmodified(self):
        self.assertEqual(policy(original_guid=298052)[0],'bypass')
        self.assertEqual(policy(original_guest_ids=(('EA',123),))[0],'bypass')
        self.assertEqual(policy(active_school=False)[0],'bypass')
        self.assertEqual(policy(zone_verified=False)[0],'bypass')
        self.assertEqual(policy(day_verified=False)[0],'bypass')

    def test_incomplete_roster_and_unverified_filter_fail_closed(self):
        self.assertEqual(policy(class_ids=(GROUPS[0],GROUPS[1][:-1]))[0],'block')
        self.assertEqual(policy(eligible_base_ids=None)[0],'block')
        self.assertEqual(policy(eligible_base_ids=(True,))[0],'block')

    def test_no_second_request_and_one_ack_per_school_day(self):
        pilot=OneSlotPilot()
        key=('11','568605179472948277',1)
        response=pilot.resolve(key,277733,(),class_ids=GROUPS,
            playable_ids=PLAYABLE,eligible_base_ids=('2','3'),
            already_on_zone_ids=(),active_school=True,save_verified=True,
            zone_verified=True,day_verified=True)
        self.assertEqual(response[0],'choose')
        self.assertEqual(response[1],2)
        response=pilot.resolve(key,277733,(),class_ids=GROUPS,
            playable_ids=PLAYABLE,eligible_base_ids=('3',),
            already_on_zone_ids=(),active_school=True,save_verified=True,
            zone_verified=True,day_verified=True)
        self.assertEqual(response[0],'bypass')
        self.assertTrue(pilot.confirm(2))
        self.assertFalse(pilot.confirm(2))

    def test_new_day_allows_one_new_slot_if_runtime_verifies_day(self):
        p=OneSlotPilot()
        opts=dict(class_ids=GROUPS,playable_ids=PLAYABLE,
                  eligible_base_ids=('2',),already_on_zone_ids=(),
                  active_school=True,save_verified=True,zone_verified=True,
                  day_verified=True)
        self.assertEqual(p.resolve(('11','zone',1),277733,(),**opts)[0],'choose')
        self.assertEqual(p.resolve(('11','zone',2),277733,(),**opts)[0],'choose')

if __name__=='__main__':
    unittest.main()
