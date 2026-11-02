"""Regression: the real M106 pilot was blocked despite synthetic CI green.

The live save had 13 registered NPCs, 12 passed vanilla EA Base,
no registered NPC passed original EA Mean, and the user does not want
automatic replacement, role changes, or personality modifications.
"""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for folder in ('m105_day_controller','m106_roster_first'):
    sys.path.insert(0,str(ROOT/'src'/folder))

from mhs106_fixed_roster_audit import audit_fixed_roster,summary
from mhs105_atomic_school_roster import BASE_JOB

CLASSES=(tuple(str(x) for x in range(1,9)),
         tuple(str(x) for x in range(9,17)))
PLAYABLE=('1','9','10')
NPC=tuple(x for group in CLASSES for x in group if x not in PLAYABLE)
PINS={278965:'2',278966:'3',278967:'4',278968:'11',303765:'12'}
FILTERS={
    BASE_JOB:tuple(x for x in NPC if x!='16'),
    278965:('2',),278966:('3',),278967:('4',),
    278968:('11',),303765:()
}

class RealSaveRegression(unittest.TestCase):
    def test_non_base_teen_never_silently_reassigned(self):
        report=audit_fixed_roster(CLASSES,PLAYABLE,PINS,FILTERS)
        self.assertEqual(report['status'],
            'FIXED_16_REQUIRES_UNVERIFIED_SCHOOL_SELECTION')
        self.assertEqual(report['all_16'],CLASSES[0]+CLASSES[1])
        self.assertEqual(report['original_assigned_core'],
                         tuple((job,PINS[job]) for job in PINS))
        self.assertEqual(len(report['remaining_original_base']),8)
        self.assertEqual(report['remaining_base_filter_rejected'],('16',))
        self.assertEqual(report['registered_npc_base_filter_rejected'],('16',))
        self.assertEqual(report['assigned_core_filter_rejected'],
                         ((303765,'12'),))
        self.assertEqual(report['no_original_ea_student_filter'],('16',))
        self.assertEqual(report['core_rejected_but_original_base_eligible'],
                         ((303765,'12'),))
        for key in ('roster_changed','roles_changed','traits_changed',
                    'filter_overrides_authorized','ea_job_binding_verified',
                    'attendance_verified'):
            self.assertFalse(report[key])

    def test_original_filters_all_eligible_still_not_attendance(self):
        ok=dict(FILTERS)
        ok[BASE_JOB]=NPC
        ok[303765]=('12',)
        p=audit_fixed_roster(CLASSES,PLAYABLE,PINS,ok)
        self.assertEqual(p['status'],
            'FIXED_16_ORIGINAL_FILTERS_MATCH_NOT_EA_BOUND')
        self.assertFalse(p['attendance_verified'])
        self.assertFalse(p['ea_job_binding_verified'])

    def test_no_registered_sim_id_may_be_substituted(self):
        p=audit_fixed_roster(CLASSES,PLAYABLE,PINS,FILTERS)
        ids=set(p['all_16'])
        self.assertTrue(set(x for _,x in p['original_assigned_core'])<=ids)
        self.assertTrue(set(p['remaining_original_base'])<=ids)
        self.assertNotIn('99999',ids)
        self.assertIn('filtro autonomo',summary(p))
        
    def test_missing_real_filter_data_is_not_a_success(self):
        f=dict(FILTERS)
        f.pop(303765)
        self.assertEqual(audit_fixed_roster(
            CLASSES,PLAYABLE,PINS,f)['status'],'INVALID_ROSTER_AUDIT')

    def test_invalid_manual_roles_are_not_reallocated(self):
        p=dict(PINS,**{303765:'9'})
        self.assertEqual(audit_fixed_roster(
            CLASSES,PLAYABLE,p,FILTERS)['status'],'INVALID_ROSTER_AUDIT')


if __name__=='__main__':
    unittest.main()
