"""M89 integration seam: prove EA gets modified list on same request."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in ('src/m89_selection','src/m88_selection','src/m58_selection'):
    sys.path.insert(0,str(ROOT/p))
from mhs89_precreate_hook import install
from tests.test_m88_replace_guest import Job,Guest,List,GuestInfo,EmptyEAList
class Situation:
    guid64=277733
class Other:
    guid64=298052

def manager():
    class Manager:
        def __init__(self):
            self.requests=[]
        def create_situation(self,kind,guest_list=None,user_facing=True):
            self.requests.append((kind,guest_list,user_facing))
            return 42
    return Manager

class M89Tests(unittest.TestCase):
    def test_same_call_receives_enrolled_id_without_extra_situation(self):
        Manager=manager()
        self.assertTrue(install(Manager,lambda *args:(555,True,True),Job(),GuestInfo,1))
        instance=Manager()
        original=List([Guest(0)])
        self.assertEqual(instance.create_situation(Situation(),guest_list=original,user_facing=False),42)
        self.assertEqual(len(instance.requests),1)
        self.assertEqual([x.sim_id for x in instance.requests[0][1].items],[555])
        self.assertEqual([x.sim_id for x in original.items],[0])
        self.assertFalse(instance.requests[0][2])
    def test_original_ea_request_keeps_spinup_flags_and_observes_real_id(self):
        class OriginalManager:
            def __init__(self):
                self.calls=[]
            def create_situation(self,kind,guest_list=None,
                                 spawn_sims_during_zone_spin_up=False,
                                 user_facing=True,duration_override=None,
                                 creation_source=None):
                self.calls.append((
                    kind,guest_list,spawn_sims_during_zone_spin_up,
                    user_facing,duration_override,creation_source))
                return 123456
        acknowledgements=[]
        def gate(manager,kind,guests,args,kwargs):
            return (kwargs.get('spawn_sims_during_zone_spin_up') is True
                    and kwargs.get('creation_source')=='EA weekly')
        self.assertTrue(install(
            OriginalManager,lambda *_:(555,True,True),
            Job(),GuestInfo,1,context_checker=gate,
            on_created=lambda sid,created:acknowledgements.append(
                (sid,created))))
        manager=OriginalManager()
        result=manager.create_situation(
            Situation(),guest_list=EmptyEAList(),
            spawn_sims_during_zone_spin_up=True,
            user_facing=False,duration_override=34,
            creation_source='EA weekly')
        self.assertEqual(result,123456)
        self.assertEqual(len(manager.calls),1)
        self.assertEqual(acknowledgements,[(555,123456)])
        _,guests,spin,user,duration,source=manager.calls[0]
        self.assertEqual([x.sim_id for x in guests.items],[555])
        self.assertTrue(spin)
        self.assertFalse(user)
        self.assertEqual(duration,34)
        self.assertEqual(source,'EA weekly')

    def test_unverified_origin_never_rewrites_ea(self):
        class OriginalManager:
            def create_situation(self,kind,guest_list=None,**kwargs):
                self.received=guest_list
                return 42
        self.assertTrue(install(
            OriginalManager,lambda *_:(555,True,True),
            Job(),GuestInfo,1,
            context_checker=lambda *_:False))
        manager=OriginalManager()
        original=EmptyEAList()
        manager.create_situation(Situation(),guest_list=original)
        self.assertIs(manager.received,original)

    def test_outside_school_never_changes(self):
        Manager=manager()
        self.assertTrue(install(Manager,lambda *args:(555,True,True),Job(),GuestInfo,1))
        instance=Manager()
        initial=List([Guest(0)])
        instance.create_situation(Other(),guest_list=initial)
        self.assertIs(instance.requests[0][1],initial)
    def test_explicit_ea_guest_preserved(self):
        Manager=manager()
        self.assertTrue(install(Manager,lambda *args:(555,True,True),Job(),GuestInfo,1))
        instance=Manager()
        instance.create_situation(Situation(),guest_list=List([Guest(77)]))
        self.assertEqual(instance.requests[0][1].items[0].sim_id,77)
    def test_verified_ea_random_replaced_in_same_original_request(self):
        Manager=manager()
        provenance={'ea_auto_generated':True,'registered_ids':('555','777')}
        self.assertTrue(install(Manager,lambda *args:(555,True,True,provenance),
                                Job(),GuestInfo,1))
        instance=Manager()
        original=List([Guest(99)])
        instance.create_situation(Situation(),guest_list=original)
        self.assertEqual(len(instance.requests),1)
        self.assertEqual(instance.requests[0][1].items[0].sim_id,555)
        self.assertEqual(original.items[0].sim_id,99)
    def test_unverified_ea_random_is_never_replaced(self):
        Manager=manager()
        self.assertTrue(install(Manager,lambda *args:(555,True,True),
                                Job(),GuestInfo,1))
        instance=Manager()
        instance.create_situation(Situation(),guest_list=List([Guest(99)]))
        self.assertEqual(instance.requests[0][1].items[0].sim_id,99)
    def test_failing_acknowledgement_never_creates_duplicate(self):
        Manager=manager()
        def failed(_sid):
            raise RuntimeError('ack failed')
        self.assertTrue(install(Manager,lambda *args:(555,True,True),
                                Job(),GuestInfo,1,on_applied=failed))
        instance=Manager()
        self.assertEqual(instance.create_situation(
            Situation(),guest_list=List([Guest(0)])),42)
        self.assertEqual(len(instance.requests),1)
        self.assertEqual(instance.requests[0][1].items[0].sim_id,555)
    def test_ea_exception_must_not_retry_school_creation(self):
        class RejectManager:
            calls=0
            def create_situation(self,kind,guest_list=None,user_facing=True):
                self.calls+=1
                raise RuntimeError('EA rejected request')
        self.assertTrue(install(RejectManager,lambda *args:(555,True,True),
                                Job(),GuestInfo,1))
        instance=RejectManager()
        with self.assertRaises(RuntimeError):
            instance.create_situation(Situation(),guest_list=List([Guest(0)]))
        self.assertEqual(instance.calls,1)

    def test_fail_closed_resolver(self):
        Manager=manager()
        def broken(*args):raise RuntimeError('unavailable')
        self.assertTrue(install(Manager,broken,Job(),GuestInfo,1))
        instance=Manager()
        instance.create_situation(Situation(),guest_list=List([Guest(0)]))
        self.assertEqual(instance.requests[0][1].items[0].sim_id,0)
if __name__=='__main__':
    unittest.main()
