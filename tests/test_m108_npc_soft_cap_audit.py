"""M108 original EA Bouncer soft-cap margin, without cap cheats."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m108_native_roster'))

from mhs108_npc_soft_cap_audit import assess_npc_school_capacity
from tests.test_m108_native_invitation import (
    CLASSES,CORE,prepare_fixed_manifest)

MANIFEST=prepare_fixed_manifest(CLASSES,('1','9','16'),CORE,11,12,777)
STUDENTS=('2','3','4','5','6','7','8','10','11','12','13','14','15')
STAFF=('200','201','202','203','204')


def context(**updates):
    data={
        'native_ea_spawner_counters_verified':True,
        'school_staff_ids_verified':True,
        'active_household_present':True,
        'zone_running':True,
        'save_slot':'11','sim_day':12,'zone_id':'777',
    }
    data.update(updates)
    return data


def audit(
        present=STUDENTS+STAFF, leaving=(),
        count=18, nleaving=0, cap=22, staff=STAFF, ctx=None,
        manifest=MANIFEST):
    return assess_npc_school_capacity(
        manifest,staff,present,leaving,count,nleaving,cap,
        context() if ctx is None else ctx)


class NPCSpawnerAuditTests(unittest.TestCase):
    def test_13_fixed_school_npcs_plus_five_real_staff(self):
        result=audit()
        self.assertEqual(result['status'],'SCHOOL_NPC_CAPACITY_SNAPSHOT_OK')
        self.assertEqual(result['enrolled_school_npc_count'],13)
        self.assertEqual(result['verified_staff_npc_count'],5)
        self.assertEqual(result['required_school_npc_total'],18)
        self.assertEqual(result['projected_soft_cap_margin'],4)
        self.assertTrue(result['npc_spawner_capacity_verified'])
        self.assertFalse(result['school_attendance_verified'])
        self.assertFalse(result['seating_verified'])

    def test_spawner_cap_has_to_account_for_unrelated_npcs_too(self):
        present=STUDENTS+STAFF+('900','901','902')
        result=audit(present=present,count=21,cap=20)
        self.assertEqual(result['status'],'SCHOOL_NPC_SOFT_CAP_SHORTFALL')
        self.assertEqual(result['projected_soft_cap_margin'],-1)

    def test_missing_registered_students_increase_projected_load(self):
        present=tuple(x for x in STUDENTS+STAFF if x not in ('14','15'))
        result=audit(present=present,count=16,cap=17)
        self.assertEqual(result['status'],'SCHOOL_NPC_SOFT_CAP_SHORTFALL')
        self.assertEqual(result['missing_required_ids'],('14','15'))
        self.assertEqual(result['predicted_instantiated_npcs'],18)

    def test_equal_to_cap_is_not_guarantee_against_later_arrivals(self):
        result=audit(count=18,cap=18)
        self.assertEqual(result['status'],'SCHOOL_NPC_SOFT_CAP_AT_LIMIT')
        self.assertEqual(result['projected_soft_cap_margin'],0)
        self.assertFalse(result['npc_spawner_capacity_verified'])
        self.assertFalse(result['school_attendance_verified'])

    def test_school_student_or_staff_departing_fails_immediately(self):
        result=audit(leaving=('2','200'),nleaving=2)
        self.assertEqual(
            result['status'],'REGISTERED_STUDENT_OR_STAFF_LEAVING')
        self.assertEqual(result['leaving_required_ids'],('2','200'))

    def test_npc_leaving_counter_uses_real_ea_counter_not_guessed(self):
        present=STUDENTS+STAFF+('900',)
        result=audit(present=present,leaving=('900',),
                     count=19,nleaving=1,cap=18)
        self.assertEqual(result['status'],'SCHOOL_NPC_SOFT_CAP_AT_LIMIT')
        self.assertEqual(result['existing_npcs_not_leaving'],18)

    def test_missing_or_unsafe_ea_counters_are_blocked(self):
        for kwargs in (
            {'count':-1},{'cap':0},{'cap':True},
            {'nleaving':-1},{'nleaving':19},
            {'count':3},{'nleaving':True},
            {'present':('2','2')},
            {'leaving':('999',)},
            {'staff':('2','200')},
            {'staff':()},
            {'ctx':context(native_ea_spawner_counters_verified=False)},
            {'ctx':context(school_staff_ids_verified=False)},
            {'ctx':context(zone_running=False)},
            {'ctx':context(active_household_present=False)},
            {'ctx':context(sim_day=13)},
            {'ctx':context(zone_id=888)},
        ):
            result=audit(**kwargs)
            self.assertNotEqual(result['status'],
                                'SCHOOL_NPC_CAPACITY_SNAPSHOT_OK',
                                msg=str(kwargs))
            self.assertFalse(result['npc_spawner_capacity_verified'])

    def test_no_arbitrary_hardcoded_twenty_sim_limit(self):
        result=audit(count=18,cap=40)
        self.assertEqual(result['status'],'SCHOOL_NPC_CAPACITY_SNAPSHOT_OK')
        self.assertEqual(result['projected_soft_cap_margin'],22)
        self.assertFalse(result['school_attendance_verified'])


if __name__=='__main__':
    unittest.main()
