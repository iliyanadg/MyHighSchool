"""M102 read-only, attribute-optional Bouncer probe tests."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m102_bouncer'))
from mhs102_bouncer_observer import bouncer_probe

class Requests:
    def __init__(self):
        self._requests=[
            SimpleNamespace(sim_id=55,request_priority=6,status='QUEUED'),
            SimpleNamespace(sim_id=99,request_priority=3,status='ASSIGNED')]

class Manager:
    def __init__(self,situation,bouncer=None):
        self.situation=situation
        self._bouncer=bouncer
    def get(self,situation_id):
        return self.situation if situation_id==123 else None

class Situation:
    def __init__(self):
        self._bouncer_requests=[SimpleNamespace(sim_id=55,status='PENDING')]
        self._guest_list=SimpleNamespace(
            guest_info_gen=lambda:iter([SimpleNamespace(sim_id=55)]))

class BouncerTests(unittest.TestCase):
    def test_existing_situation_and_bouncer_requests(self):
        m=Manager(Situation(),Requests())
        result=bouncer_probe(m,123)
        self.assertEqual(result['situation_lookup'],'FOUND')
        self.assertEqual(result['bouncer_owner'],'MANAGER')
        self.assertEqual(result['bouncer_requests']['availability'],
                         'ATTRIBUTES_OBSERVED')
        req=next(c for c in result['bouncer_requests']['found_containers']
                 if c['attribute']=='_requests')
        self.assertEqual(req['size'],2)
        self.assertEqual(req['sample_requests'][0]['fields']['sim_id'],55)

    def test_manager_without_bouncer_is_unknown_not_no_requests(self):
        m=Manager(Situation())
        result=bouncer_probe(m,123)
        self.assertEqual(result['situation_lookup'],'FOUND')
        self.assertEqual(result['bouncer_requests']['availability'],
                         'OBJECT_UNAVAILABLE')
        self.assertTrue(result['does_not_prove_bouncer_assignment'])

    def test_unknown_private_layout_cannot_be_claimed_unfulfilled(self):
        result=bouncer_probe(Manager(object()),123)
        self.assertEqual(result['situation_requests']['availability'],'UNKNOWN')
        self.assertEqual(result['bouncer_owner'],'UNKNOWN')

    def test_no_mutation_or_spawn_api_is_invoked(self):
        class NeverSpawn:
            def get(self,sid):
                return Situation()
            def create_situation(self,*args,**kwargs):
                self.fail()
            def fail(self):
                raise AssertionError('no mutation allowed')
        result=bouncer_probe(NeverSpawn(),123)
        self.assertEqual(result['situation_lookup'],'FOUND')

    def test_missing_and_invalid_id(self):
        self.assertEqual(bouncer_probe(Manager(None),123)['situation_lookup'],
                         'NOT_FOUND')
        self.assertEqual(bouncer_probe(Manager(Situation()),None)['situation_lookup'],
                         'INVALID_ID')

if __name__=='__main__':
    unittest.main()
