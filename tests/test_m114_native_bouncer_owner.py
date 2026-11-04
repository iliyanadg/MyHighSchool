"""M114 exact in-game BouncerRequest owner resolver, synthetic modules."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for prefix in ('m108_native_roster','m109_activation',
               'm113_controller','m114_bouncer'):
    sys.path.insert(0,str(ROOT/'src'/prefix))

from mhs114_native_bouncer_owner import inspect_original_ea_bouncer_owner
from mhs114_school_bouncer_pair import build_school_bouncer_pair
from tests.test_m114_school_bouncer_pair import native_request_owner
from tests.test_m108_native_invitation import session
from tests.test_m108_school_filter_scope import BLANK,BASE_CONTEXT


def fake_ea(owner=None,with_lookup=True):
    owner=owner or native_request_owner()
    packages={}
    situations=types.ModuleType('situations')
    situations.__path__=[]
    bouncer=types.ModuleType('situations.bouncer')
    bouncer.__path__=[]
    request_mod=types.ModuleType('situations.bouncer.bouncer_request')
    request_mod.BouncerRequest=owner
    situations.bouncer=bouncer
    bouncer.bouncer_request=request_mod
    packages['situations']=situations
    packages['situations.bouncer']=bouncer
    packages['situations.bouncer.bouncer_request']=request_mod
    sims=types.ModuleType('sims')
    sims.__path__=[]
    info=types.ModuleType('sims.sim_info_types')
    info.Age=type('Age',(),{'TEEN':'TEEN'})
    info.Species=type('Species',(),{'HUMAN':'HUMAN'})
    sims.sim_info_types=info
    packages['sims']=sims
    packages['sims.sim_info_types']=info
    services=types.ModuleType('services')
    manager=type('InfoMgr',(),{'get':lambda self,sid:None})()
    if not with_lookup:
        manager=object()
    services.sim_info_manager=lambda:manager
    packages['services']=services
    return packages


class M114OriginalEAOwnerTests(unittest.TestCase):
    def test_live_imports_resolve_exact_earlier_m109_owner_without_mutating(self):
        original=native_request_owner()
        before=original.__dict__['__init__']
        with patch.dict(sys.modules,fake_ea(original)):
            refs,report=inspect_original_ea_bouncer_owner()
        self.assertEqual(report['status'],'EA_OWNER_AVAILABLE_NOT_FILTER_AUTHORIZED')
        self.assertIs(refs['owner'],original)
        self.assertEqual(refs['teen_age'],'TEEN')
        self.assertEqual(refs['human_species'],'HUMAN')
        self.assertTrue(callable(refs['sim_info_lookup']))
        self.assertIs(original.__dict__['__init__'],before)
        self.assertFalse(report['native_blank_filter_verified'])
        self.assertFalse(report['runtime_override_authorized'])
        self.assertFalse(report['game_modified'])

    def test_renamed_or_patched_owner_blocks(self):
        wrong=native_request_owner()
        wrong.__module__='other.mods'
        with patch.dict(sys.modules,fake_ea(wrong)):
            refs,report=inspect_original_ea_bouncer_owner()
        self.assertIsNone(refs)
        self.assertEqual(report['status'],
                         'EA_BOUNCER_DESCRIPTOR_OWNER_MISMATCH')
        patched=native_request_owner()
        patched.__dict__['__init__']._mhs108_school_filter=True
        try:
            with patch.dict(sys.modules,fake_ea(patched)):
                refs,report=inspect_original_ea_bouncer_owner()
            self.assertIsNone(refs)
        finally:
            del patched.__dict__['__init__']._mhs108_school_filter

    def test_absent_sim_info_lookup_blocks(self):
        with patch.dict(sys.modules,fake_ea(with_lookup=False)):
            refs,report=inspect_original_ea_bouncer_owner()
        self.assertIsNone(refs)
        self.assertEqual(report['status'],'EA_SIM_INFO_LOOKUP_UNAVAILABLE')

    def test_owner_readback_is_not_an_installer_or_native_blank_filter(self):
        with patch.dict(sys.modules,fake_ea()):
            refs,report=inspect_original_ea_bouncer_owner()
        pair,status=build_school_bouncer_pair(
            session(),refs['owner'],BLANK,refs['teen_age'],
            refs['human_species'],refs['sim_info_lookup'],
            lambda:dict(BASE_CONTEXT))
        self.assertIsNotNone(pair)
        self.assertFalse(pair.snapshot()[
            'two_reversible_stages_constructed'])
        self.assertEqual(pair.snapshot()['ea_descriptors_currently_modified'],
                         False)
        self.assertFalse(report['runtime_override_authorized'])


if __name__=='__main__':
    unittest.main()
