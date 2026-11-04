"""New game save / different registered teens must not require code edits."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m131_playable'))
sys.path.insert(0,str(ROOT/'src'/'m147_integrated'))
sys.path.insert(0,str(ROOT/'src'/'m128_alignment'))
from mhs131_native_playable_class import find_playable_entry
from mhs147_class_timing_policy import can_early_request
from mhs128_ea_class_trait_alignment import planned_changes

class Info(object):
    def __init__(self, sim_id, has_class1=False):
        self.sim_id=sim_id
        self.is_selectable=True
        self.age='TEEN'
        self.species='HUMAN'
        self._trait=has_class1
        self.trait_tracker=self
    def has_trait(self, trait):
        return self._trait

class Home(object):
    def __init__(self, infos):
        self.infos=infos
    def sim_info_gen(self):
        return iter(self.infos)

class Manager(object):
    def __init__(self, infos):
        self.infos={x.sim_id:x for x in infos}
    def get(self, sid):
        return self.infos.get(sid)

def groups(start):
    return (tuple(str(start+i) for i in range(8)),
            tuple(str(start+i) for i in range(8,16)))

class SwappableRosterTests(unittest.TestCase):
    def test_two_unrelated_saves_have_no_embedded_student_ids(self):
        role1=[{'situation_guid':293815,'job_guid':277919,
                'is_preparation':True}]
        role2=[{'situation_guid':297774,'job_guid':277919,
                'is_preparation':True}]
        for start in (1000,900000):
            enrolled=groups(start)
            # Any registered teens can be played, not just named actors.
            infos=[Info(start),Info(start+9),Info(start+15)]
            rows=find_playable_entry(enrolled,None,Home(infos))
            self.assertEqual([r['registered_class'] for r in rows],[1,2,2])
            for row in rows:
                role=role1 if row['registered_class']==1 else role2
                allowed,_=can_early_request(
                    row['registered_class'],role,
                    {'hour':9,'minute':36},'',False)
                self.assertTrue(allowed)
    def test_class_transfer_uses_new_register_mapping(self):
        start=700
        before=groups(start)
        after=(before[0][1:]+(before[1][0],),
               (before[0][0],)+before[1][1:])
        info=Info(start)
        self.assertEqual(
            find_playable_entry(before,None,Home([info]))[0]['registered_class'],1)
        self.assertEqual(
            find_playable_entry(after,None,Home([info]))[0]['registered_class'],2)
        # Trait alignment is computed against the NEW registered class.
        everyone=[Info(int(sid)) for g in after for sid in g]
        plan=planned_changes(after,Manager(everyone),'EA_CLASS1','TEEN','HUMAN')
        chosen=next(p for p in plan if p['sim_id']==str(start))
        self.assertFalse(chosen['ea_class1_trait_expected'])
    def test_replace_npc_preserves_8_per_class_without_new_controller(self):
        before=groups(800)
        after=(before[0][:7]+('60000',),before[1])
        self.assertEqual(len(set(after[0]+after[1])),16)
        people=[Info(800),Info(808),Info(815)]
        rows=find_playable_entry(after,None,Home(people))
        self.assertEqual([r['sim_id'] for r in rows],['800','808','815'])
        self.assertEqual([r['registered_class'] for r in rows],[1,2,2])

if __name__=='__main__':
    unittest.main()
