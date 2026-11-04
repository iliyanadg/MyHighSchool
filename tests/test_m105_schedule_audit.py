"""M105: real EA scheduler count audit must remain read-only."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m105_day_controller'))
from mhs105_atomic_school_roster import plan_school_day,ALL_JOBS,CORE_JOBS
from mhs105_schedule_audit import NativeScheduleAudit,_valid_plan,MAX_EVENTS

CLASSES=(tuple(str(i) for i in range(1,9)),
         tuple(str(i) for i in range(9,17)))
PLAYED=('1','9','10')
NPCS=tuple(s for group in CLASSES for s in group if s not in PLAYED)
PINS=dict(zip(CORE_JOBS,('2','3','4','11','12')))
PLAN=plan_school_day(CLASSES,PLAYED,
                     {job:NPCS for job in ALL_JOBS},PINS)


def class_fixture(result=(4,6)):
    class Week:
        called=0

        @classmethod
        def get_long_term_situation_count(cls,data,resolver):
            cls.called+=1
            return result

    class Main(Week):
        guid64=277657

    class Venue(Week):
        guid64=279958

    class Other(Week):
        guid64=100000

    return Week,Main,Venue,Other


def data(guid=277733):
    return SimpleNamespace(situation=SimpleNamespace(guid64=guid))


def context(**changes):
    value=dict(school_verified=True,save_slot='11',sim_day=24,
               school_zone='401')
    value.update(changes)
    return value


class NativeScheduleAuditTests(unittest.TestCase):
    def test_plan_has_exact_sixteen_and_no_fake_authority(self):
        self.assertTrue(_valid_plan(PLAN))
        audit=NativeScheduleAudit(PLAN,'11',24)
        value=audit.observe(277657,277733,(4,6),context())
        self.assertEqual(value,(4,6))
        event=audit.snapshot()['last_event']
        self.assertEqual(event['minimum_shortfall'],4)
        self.assertEqual(event['maximum_shortfall'],2)
        self.assertFalse(event['vanilla_max_can_reach_eight'])
        self.assertFalse(event['m96_override_authorized'])
        self.assertFalse(event['attendance_verified'])

    def test_min_guarantees_vs_max_only_possible(self):
        audit=NativeScheduleAudit(PLAN,11,24)
        for original in ((6,8),(8,10),(8,8)):
            self.assertEqual(audit.observe(279958,277733,original,context()),
                             original)
        events=audit.events
        self.assertFalse(events[0]['vanilla_min_guarantees_eight'])
        self.assertTrue(events[0]['vanilla_max_can_reach_eight'])
        self.assertTrue(events[1]['vanilla_min_guarantees_eight'])
        self.assertTrue(events[2]['vanilla_min_guarantees_eight'])

    def test_original_classmethod_runs_exactly_once_for_school_and_non_school(self):
        Week,Main,Venue,Other=class_fixture((4,6))
        audit=NativeScheduleAudit(PLAN,'11',24)
        self.assertTrue(audit.install(Week,lambda:context()))
        self.assertEqual(Main.get_long_term_situation_count(data(),None),(4,6))
        self.assertEqual(Venue.get_long_term_situation_count(data(),None),(4,6))
        self.assertEqual(Main.get_long_term_situation_count(data(298052),None),(4,6))
        self.assertEqual(Other.get_long_term_situation_count(data(),None),(4,6))
        self.assertEqual(Main.called,2)
        self.assertEqual(Venue.called,1)
        self.assertEqual(Other.called,1)
        self.assertEqual(audit.snapshot()['observations'],2)
        self.assertFalse(audit.snapshot()['game_count_changed'])

    def test_invalid_context_never_records_or_modifies_ea(self):
        Week,Main,_,_=class_fixture()
        audit=NativeScheduleAudit(PLAN,'11',24)
        ctx=context(save_slot='12')
        self.assertTrue(audit.install(Week,lambda:ctx))
        self.assertEqual(Main.get_long_term_situation_count(data(),None),(4,6))
        self.assertEqual(audit.snapshot()['observations'],0)
        self.assertEqual(audit.observe(277657,277733,(4,6),
                                      context(school_verified=False)),(4,6))
        self.assertEqual(audit.observe(277657,277733,(4,6),
                                      context(sim_day=25)),(4,6))
        self.assertEqual(audit.observe(277657,277733,(4,6),
                                      context(school_zone=None)),(4,6))
        self.assertEqual(audit.snapshot()['observations'],0)

    def test_scheduler_exception_does_not_affect_original(self):
        Week,Main,_,_=class_fixture()
        audit=NativeScheduleAudit(PLAN,'11',24)
        self.assertTrue(audit.install(Week,lambda:1/0))
        self.assertEqual(Main.get_long_term_situation_count(data(),None),(4,6))
        self.assertEqual(audit.errors,1)

    def test_unknown_ea_count_and_bounded_history(self):
        audit=NativeScheduleAudit(PLAN,'11',24)
        self.assertEqual(audit.observe(277657,277733,('x',8),context()),('x',8))
        self.assertEqual(audit.errors,1)
        for i in range(MAX_EVENTS+5):
            audit.observe(277657,277733,(i,i),context())
        self.assertEqual(len(audit.events),MAX_EVENTS)
        self.assertEqual(audit.events[-1]['ea_original_min'],MAX_EVENTS+4)

    def test_no_hook_if_m96_already_replaced_count(self):
        Week,_,_,_=class_fixture()
        f=Week.__dict__['get_long_term_situation_count'].__func__
        f._mhs96_count_hook=True
        audit=NativeScheduleAudit(PLAN,11,24)
        self.assertFalse(audit.install(Week,lambda:context()))
        self.assertEqual(audit.snapshot()['observations'],0)

    def test_no_installs_twice_and_no_instance_method_patch(self):
        Week,_,_,_=class_fixture()
        audit=NativeScheduleAudit(PLAN,11,24)
        self.assertTrue(audit.install(Week,lambda:context()))
        self.assertFalse(audit.install(Week,lambda:context()))
        class Wrong:
            def get_long_term_situation_count(self,data,resolver):
                return (4,6)
        self.assertFalse(NativeScheduleAudit(PLAN,11,24).install(
            Wrong,lambda:context()))

    def test_malformed_or_partial_plan_cannot_audit_eight(self):
        bad=dict(PLAN,base_invites_needed=7)
        self.assertFalse(_valid_plan(bad))
        with self.assertRaises(ValueError):
            NativeScheduleAudit(bad,'11',24)
        with self.assertRaises(ValueError):
            NativeScheduleAudit(PLAN,'invalid',24)

    def test_audit_cannot_spoof_reserved_core_roles(self):
        data=NativeScheduleAudit(PLAN,11,24).snapshot()
        self.assertFalse(data['core_roles_pre_spawn_reserved'])
        self.assertFalse(data['m96_override_authorized'])
        self.assertFalse(data['student_arrival_verified'])


if __name__=='__main__':
    unittest.main()
