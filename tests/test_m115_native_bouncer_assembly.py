"""M115 real EA blank + BouncerRequest native assembly, synthetic imports."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for prefix in ('m108_native_roster','m109_activation','m113_controller',
               'm114_bouncer','m115_filter'):
    sys.path.insert(0,str(ROOT/'src'/prefix))
from mhs115_native_bouncer_assembly import prepare_original_ea_bouncer_pair
from tests.test_m114_native_bouncer_owner import fake_ea
from tests.test_m115_native_blank_filter import (
    modules as blank_modules, NativeBlank,
)
from tests.test_m108_native_invitation import session
from tests.test_m108_school_filter_scope import BASE_CONTEXT


def combined(blank=None,wrong_owner=False):
    mods=fake_ea()
    if wrong_owner:
        mods['situations.bouncer.bouncer_request'].BouncerRequest.__module__=(
            'non_ea_third_party')
    mods.update(blank_modules(blank))
    return mods


class M115NativeAssemblyTests(unittest.TestCase):
    def test_exact_EA_blank_and_original_Bouncer_pair_only_built(self):
        blank=NativeBlank()
        with patch.dict(sys.modules,combined(blank)):
            pair,report=prepare_original_ea_bouncer_pair(
                session(),lambda:dict(BASE_CONTEXT))
        self.assertIsNotNone(pair)
        self.assertIs(pair.scope.blank_filter,blank)
        self.assertEqual(report['status'],
                         'EA_BOUNCER_PAIR_PREPARED_NOT_ACTIVATED')
        self.assertTrue(report['native_blank_ea_resolved'])
        self.assertTrue(report['native_bouncer_owner_resolved'])
        self.assertTrue(report['shared_invitation_scope_constructed'])
        self.assertTrue(report['no_custom_sim_filter_created'])
        self.assertFalse(report['filter_override_authorized'])
        self.assertFalse(report['game_modified'])
        self.assertFalse(pair.snapshot()['ea_descriptors_currently_modified'])
        # No false flags supplied merely because a valid EA filter exists.
        self.assertIsNone(pair.stage_graph({},{}))

    def test_missing_native_filter_rejects_assembly(self):
        with patch.dict(sys.modules,combined(object())):
            pair,report=prepare_original_ea_bouncer_pair(
                session(),lambda:dict(BASE_CONTEXT))
        self.assertIsNone(pair)
        self.assertEqual(report['status'],'EA_NATIVE_BLANK_FILTER_NOT_READY')
        self.assertFalse(report['shared_invitation_scope_constructed'])

    def test_bouncer_owner_not_valid_blocks_even_with_valid_EA_blank(self):
        mods=combined(NativeBlank())
        owner=mods['situations.bouncer.bouncer_request'].BouncerRequest
        owner.__module__='thirdparty'
        with patch.dict(sys.modules,mods):
            pair,report=prepare_original_ea_bouncer_pair(
                session(),lambda:dict(BASE_CONTEXT))
        self.assertIsNone(pair)
        self.assertEqual(report['status'],'EA_BOUNCER_OWNER_NOT_READY')
        self.assertFalse(report['native_bouncer_owner_resolved'])

    def test_missing_context_provider_blocks_early_without_EA_access(self):
        pair,report=prepare_original_ea_bouncer_pair(session(),None)
        self.assertIsNone(pair)
        self.assertEqual(report['status'],
                         'MISSING_NATIVE_EA_CONTEXT_PROVIDER')

    def test_missing_MHS_guest_session_is_not_autofilled(self):
        with patch.dict(sys.modules,combined(NativeBlank())):
            pair,report=prepare_original_ea_bouncer_pair(
                None,lambda:dict(BASE_CONTEXT))
        self.assertIsNone(pair)
        self.assertEqual(report['status'],'NATIVE_EA_GUEST_SESSION_NOT_READY')
        self.assertFalse(report['filter_override_authorized'])


if __name__=='__main__':
    unittest.main()
