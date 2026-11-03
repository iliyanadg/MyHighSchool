"""M122 one-controller Mac runtime command wiring, synthetic EA services."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m122_classrooms'))
from tests.test_m121_thirteen_npc_trial import environment
from tests.test_m122_classroom_job_readback import (
    CLASS1,CLASS2,Job,SimManager,SituationManager
)


def load():
    modules,state,blank,base,day=environment()
    source=modules['mhs_m2_store'].RosterStore
    sim_info=SimManager()
    sim_info.infos[1].is_selectable=True
    sim_info.infos[9].is_selectable=True
    sim_info.infos[16].is_selectable=True
    for info in sim_info.infos.values():
        info.is_selectable=getattr(info,'is_selectable',False)
    # Keep the existing M121 household/config fixture; only replace
    # live read-only situation membership with native fake situation jobs.
    module_services=modules['services']
    original_zone_manager=module_services.get_zone_situation_manager
    module_services.get_zone_situation_manager=lambda:SituationManager()
    # The parent EA class is unchanged and no new situation spawned.
    spec=importlib.util.spec_from_file_location(
        'mhs122_experimental_game_test',
        str(ROOT/'src'/'m122_classrooms'/
            'mhs122_thirteen_npc_plus_classes.py'))
    instance=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,modules):
        spec.loader.exec_module(instance)
    native_arm=instance.arm_m122
    def arm():
        with patch.dict(sys.modules,modules):
            return native_arm()
    instance.arm_m122=arm
    return instance,modules,state,day,module_services,original_zone_manager


class M122LiveCommandsTests(unittest.TestCase):
    def test_m122_has_five_real_registered_commands(self):
        obj,modules,state,day,services,original=load()
        self.assertTrue(callable(obj.m122arm))
        self.assertTrue(callable(obj.m122status))
        self.assertTrue(callable(obj.m122stop))
        self.assertTrue(callable(obj.m122classi))
        self.assertTrue(callable(obj.m122prepara))

    def test_does_not_claim_class_seating_or_jobs_when_at_home(self):
        obj,modules,state,day,services,original=load()
        self.assertIn('non sei al liceo',
                      obj._snapshot_classes('lesson'))
        # Registered 13 NPCs remain under M121 EA intervention module.
        self.assertTrue(hasattr(obj,'ThirteenNPCController'))
        self.assertTrue(callable(obj.arm_m122))

    def test_classroom_command_requires_single_active_controller(self):
        obj,modules,state,day,services,original=load()
        self.assertIn('attivare da casa',
                      obj._snapshot_classes('lesson'))
        self.assertIn('attivare da casa',
                      obj._snapshot_classes('prepare'))


if __name__=='__main__':
    unittest.main()
