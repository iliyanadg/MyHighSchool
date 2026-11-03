"""M109 offline atomic activation transaction tests (Python 3.7).

The preflight fixture contains SYNTHETIC booleans; no test here has access
to live Sims EA classes. These tests validate only installation isolation
and deterministic rollback, NEVER real 16/16 in-game attendance.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'm108_native_roster'))
sys.path.insert(0, str(ROOT / 'src' / 'm109_activation'))

from mhs109_atomic_activation import (
    M109SchoolActivation, INSTALL_ORDER, REQUIRED_RUNTIME_EVIDENCE,
)
from tests.test_m108_native_invitation import (
    CLASSES, CORE, prepare_fixed_manifest,
)


def roster():
    return prepare_fixed_manifest(
        CLASSES, ('1', '9', '16'), CORE, 11, 12, 777)


def simulated_evidence(**changes):
    """Test-only declaration. It is NOT backed by any live EA runtime."""
    proof = {key: True for key in REQUIRED_RUNTIME_EVIDENCE}
    proof.update({
        'source': 'EA_RUNTIME_OBSERVATION',
        'activation_authorized_by_game': True,
        'save_slot': '11', 'sim_day': 12, 'school_zone': '777',
        'native_schedule_guid': 277657,
    })
    proof.update(changes)
    return proof


def stages(log, failing=None, failed_restore=None, false_result=None):
    result = {}
    cells = {}
    for name in INSTALL_ORDER:
        cell = {'active': False}
        cells[name] = cell

        def install(manifest, proof, name=name, cell=cell):
            # Deliberately mutate before failure: test the hardest rollback.
            cell['active'] = True
            log.append(('install', name))
            if name == failing:
                raise RuntimeError('partial hook install failed')
            if name == false_result:
                return False
            return True

        def restore(name=name, cell=cell):
            log.append(('restore', name))
            if name == failed_restore:
                raise RuntimeError('cannot restore modified EA method')
            cell['active'] = False
            return True

        result[name] = {'install': install, 'restore': restore}
    return result, cells


def coordinator(log, **kwargs):
    graph, cells = stages(log, **kwargs)
    obj = M109SchoolActivation(roster(),
                               lambda manifest: simulated_evidence(),
                               graph)
    return obj, cells


class M109AtomicActivationTests(unittest.TestCase):

    def test_six_hooks_install_in_order_and_restore_in_reverse(self):
        log = []
        obj, cells = coordinator(log)
        self.assertTrue(obj.arm())
        self.assertEqual(obj.state, 'ARMED')
        self.assertEqual(obj.active_stages, list(INSTALL_ORDER))
        self.assertTrue(all(cells[k]['active'] for k in INSTALL_ORDER))
        self.assertEqual(
            log[:len(INSTALL_ORDER)],
            [('install', k) for k in INSTALL_ORDER])
        self.assertTrue(obj.disarm())
        self.assertEqual(obj.state, 'FINISHED')
        self.assertEqual(
            log[-len(INSTALL_ORDER):],
            [('restore', k) for k in reversed(INSTALL_ORDER)])
        self.assertTrue(all(not cells[k]['active']
                            for k in INSTALL_ORDER))
        self.assertFalse(obj.snapshot()['attendance_16_verified'])
        self.assertFalse(obj.snapshot()['mod_installed_in_game'])

    def test_failed_hook_rolls_back_its_own_partial_patch_and_prior_hooks(self):
        log = []
        obj, cells = coordinator(log, failing='unified_lessons')
        self.assertFalse(obj.arm())
        self.assertEqual(obj.state, 'BLOCKED')
        self.assertEqual(obj.error, 'unified_lessons: RuntimeError')
        self.assertEqual(obj.active_stages, [])
        self.assertEqual(obj.rollback_errors, [])
        self.assertEqual(log, [
            ('install','native_base_count'),
            ('install','native_precreate'),
            ('install','school_filter_scope'),
            ('install','no_show_guard'),
            ('install','unified_lessons'),
            ('restore','unified_lessons'),
            ('restore','no_show_guard'),
            ('restore','school_filter_scope'),
            ('restore','native_precreate'),
            ('restore','native_base_count')])
        self.assertTrue(all(not c['active'] for c in cells.values()))
        self.assertFalse(obj.arm())

    def test_returning_false_is_an_install_failure_and_rolls_back(self):
        log = []
        obj, cells = coordinator(log, false_result='native_precreate')
        self.assertFalse(obj.arm())
        self.assertEqual(obj.state,'BLOCKED')
        self.assertEqual(log, [
            ('install','native_base_count'),
            ('install','native_precreate'),
            ('restore','native_precreate'),
            ('restore','native_base_count')])
        self.assertFalse(cells['native_base_count']['active'])
        self.assertFalse(cells['native_precreate']['active'])

    def test_uninstall_failure_never_claims_clean_ea_or_rearms(self):
        log = []
        obj, cells = coordinator(log,
                                 failing='unified_lessons',
                                 failed_restore='no_show_guard')
        self.assertFalse(obj.arm())
        self.assertEqual(obj.state, 'ROLLBACK_INCOMPLETE')
        self.assertEqual(obj.active_stages,['no_show_guard'])
        self.assertEqual(obj.rollback_errors,
                         ['no_show_guard: RuntimeError'])
        self.assertTrue(cells['no_show_guard']['active'])
        self.assertFalse(cells['native_base_count']['active'])
        self.assertFalse(obj.arm())
        self.assertFalse(obj.disarm())

    def test_manual_disarm_partial_failure_is_detected(self):
        log = []
        obj, cells = coordinator(log, failed_restore='no_show_guard')
        self.assertTrue(obj.arm())
        self.assertFalse(obj.disarm())
        self.assertEqual(obj.state, 'ROLLBACK_INCOMPLETE')
        self.assertEqual(obj.error, 'HOOK_RESTORATION_INCOMPLETE')
        self.assertEqual(obj.active_stages, ['no_show_guard'])
        self.assertFalse(obj.disarm())

    def test_missing_runtime_proof_never_calls_an_installer(self):
        for missing in REQUIRED_RUNTIME_EVIDENCE:
            log = []
            hooks, _ = stages(log)
            obj = M109SchoolActivation(
                roster(),
                lambda m, missing=missing: simulated_evidence(
                    **{missing: False}),
                hooks)
            self.assertFalse(obj.arm())
            self.assertEqual(obj.state,'BLOCKED')
            self.assertEqual(obj.error,'UNVERIFIED_EA_RUNTIME_EVIDENCE')
            self.assertEqual(log, [],msg=missing)

    def test_wrong_save_day_zone_or_school_calendar_is_not_activated(self):
        for changes in (
            {'sim_day': 13}, {'sim_day': True}, {'save_slot':'12'},
            {'school_zone':'888'}, {'native_schedule_guid':1234},
            {'source':'FAKE'}, {'activation_authorized_by_game':False},
            {'before_ea_schedule_verified':False},
        ):
            log=[]
            hooks,_=stages(log)
            obj=M109SchoolActivation(
                roster(),lambda m,changes=changes:
                simulated_evidence(**changes),hooks)
            self.assertFalse(obj.arm(),msg=str(changes))
            self.assertEqual(log,[])

    def test_missing_or_bad_install_graph_rejected_before_any_mutation(self):
        for broken in (
            None, {}, {'native_base_count': lambda m,e:True},
        ):
            obj=M109SchoolActivation(
                roster(),lambda m:simulated_evidence(),broken)
            self.assertFalse(obj.arm())
            self.assertEqual(obj.error,'INVALID_HOOK_GRAPH')
        log=[]
        hooks,_=stages(log)
        del hooks['post_bouncer_observer']
        obj=M109SchoolActivation(
            roster(),lambda m:simulated_evidence(),hooks)
        self.assertFalse(obj.arm())
        self.assertEqual(log,[])

    def test_corrupted_core_assignments_or_class_not_installed(self):
        bad=roster()
        bad['base_ids']=('99',)*8
        log=[]
        hooks,_=stages(log)
        obj=M109SchoolActivation(bad,lambda m:simulated_evidence(),hooks)
        self.assertFalse(obj.arm())
        self.assertEqual(obj.error,'INVALID_ROSTER')
        self.assertEqual(log,[])

    def test_missing_provider_or_provider_exception_is_closed(self):
        log=[]
        hooks,_=stages(log)
        obj=M109SchoolActivation(roster(),None,hooks)
        self.assertFalse(obj.arm())
        self.assertEqual(obj.error,'NO_LIVE_PREFLIGHT_PROVIDER')

        def broken_provider(manifest):
            raise RuntimeError('unavailable EA tuning')
        obj=M109SchoolActivation(roster(),broken_provider,hooks)
        self.assertFalse(obj.arm())
        self.assertEqual(obj.error,'LIVE_PREFLIGHT_RAISED_RuntimeError')
        self.assertEqual(log,[])

    def test_once_disarmed_requires_fresh_daily_activation(self):
        log=[]
        obj,_=coordinator(log)
        self.assertTrue(obj.arm())
        self.assertFalse(obj.arm())
        self.assertTrue(obj.disarm())
        self.assertFalse(obj.arm())
        self.assertEqual(obj.state,'FINISHED')
        self.assertEqual(obj.snapshot()['activation_key'],
                         ('11',12,'777',277657))


if __name__ == '__main__':
    unittest.main()
