"""M118 morning admission and lesson preflight, entirely synthetic tests."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for directory in ('m108_native_roster','m109_activation','m114_bouncer',
                  'm116_admission','m117_spinup','m118_controller'):
    sys.path.insert(0,str(ROOT/'src'/directory))

from mhs118_admission_before_lessons import (
    ADMISSION_STAGE_ORDER, build_morning_admission_stages,
    inspect_lesson_admission_gate,
)
from tests.test_m117_post_spinup_admission import (
    setting, evidence, callback_owner,
)
from tests.test_m114_school_bouncer_pair import native_pair
from tests.test_m116_native_guest_job_readback import (
    inspect_created_native_guest_jobs,
)


def report_and_playables():
    guest,original,observer,reads= None,None,None,None
    guest, manager, native, watcher, counters=setting()
    proof=evidence()
    watcher.install(manager,proof)
    try:
        engine_manager=manager(native)
        engine_manager.on_all_sims_spawned_during_zone_spin_up()
        report=watcher.observations[0]
    finally:
        watcher.restore()
    playable={
        'source':'EA_SIM_INFO_MANAGER_LIVE_INSTANCES',
        'save_slot':'11','sim_day':12,'school_zone':'777',
        'playable_present_ids':('1','9','16'),
        'all_instances_on_current_school_zone':True,
    }
    return guest,report,playable


class M118AdmissionThenLessonsTests(unittest.TestCase):
    def test_thirteen_jobs_and_three_playables_only_unlock_preflight_not_lessons(self):
        guest,report,playable=report_and_playables()
        got=inspect_lesson_admission_gate(guest,report,playable)
        self.assertEqual(got['status'],
                         'MORNING_ADMISSION_16_OBSERVED_LESSONS_STILL_GATED')
        self.assertTrue(got['morning_native_job_receipts_sufficient'])
        self.assertTrue(got['all_3_playables_on_school_zone_verified'])
        self.assertFalse(got['lesson_stage_install_authorized'])
        self.assertFalse(got['classroom_1_and_2_job_assignment_verified'])

    def test_created_receipts_cannot_substitute_for_bouncer_jobs(self):
        guest,report,playable=report_and_playables()
        untrusted=dict(report, post_bouncer_callback_provenance_verified=False)
        got=inspect_lesson_admission_gate(guest,untrusted,playable)
        self.assertEqual(got['status'],
                         'THIRTEEN_NPC_NATIVE_EA_JOB_RECEIPTS_MISMATCH')
        self.assertFalse(got['morning_native_job_receipts_sufficient'])

    def test_wrong_or_missing_playable_cannot_enable_lessons(self):
        guest,report,playable=report_and_playables()
        for malformed in (
            dict(playable,playable_present_ids=('1','9')),
            dict(playable,playable_present_ids=('1','9','999')),
            dict(playable,playable_present_ids=('1','1','9')),
            dict(playable,school_zone='999'),
            dict(playable,sim_day=13),
            dict(playable,save_slot='12'),
            dict(playable,all_instances_on_current_school_zone=False),
            dict(playable,source='MANUAL_ROSTER_GUESS'),
        ):
            got=inspect_lesson_admission_gate(guest,report,malformed)
            self.assertNotEqual(got['status'],
                'MORNING_ADMISSION_16_OBSERVED_LESSONS_STILL_GATED')
            self.assertFalse(got['lesson_stage_install_authorized'])

    def test_morning_graph_requires_four_real_named_stages(self):
        pair,why,owner,invited,context=native_pair()
        from tests.test_m108_school_filter_scope import proofs
        from tests.test_m108_no_show_guard import guard_proofs
        bouncer=pair.stage_graph(proofs(),guard_proofs())
        self.assertIsNotNone(bouncer)
        guest,original,native,observer,reads=setting()
        stage=observer.stage(original,evidence())
        real_precreate={'install':lambda m,c:True,
                        'restore':lambda:True}
        graph=build_morning_admission_stages(
            real_precreate,pair,observer,stage)
        self.assertEqual(set(graph),set(ADMISSION_STAGE_ORDER))
        self.assertNotIn('unified_lessons',graph)
        self.assertIsNone(build_morning_admission_stages(
            real_precreate,pair,observer,{}))
        self.assertIsNone(build_morning_admission_stages(
            real_precreate,pair,observer,{'install':lambda m,c:True,
                                         'restore':None}))

    def test_no_installed_observer_can_be_reused_in_new_morning_graph(self):
        pair,why,owner,invited,context=native_pair()
        from tests.test_m108_school_filter_scope import proofs
        from tests.test_m108_no_show_guard import guard_proofs
        pair.stage_graph(proofs(),guard_proofs())
        guest,original,native,observer,reads=setting()
        stage=observer.stage(original,evidence())
        self.assertTrue(observer.install(original,evidence()))
        try:
            self.assertIsNone(build_morning_admission_stages(
                {'install':lambda m,c:True,'restore':lambda:True},
                pair,observer,stage))
        finally:
            self.assertTrue(observer.restore())


if __name__=='__main__':
    unittest.main()
