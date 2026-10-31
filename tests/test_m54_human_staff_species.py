"""M54: real in-game bug: dogs with Age.ADULT appeared in staff picker.

Test the actual source functions through AST to avoid EA imports offline.
A picker must ONLY list Species.HUMAN at YA/ADULT/ELDER; server callback
must check species again. Already assigned pets should still be removable.
"""
import ast
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tooling.build_m54_human_only_staff import package_bytes,SCRIPTS
from tooling.build_m53_staff_management import package_bytes as m53_package

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'src'/'m53_staff'/'mhs53_staff_ui.py'


class M54HumanTests(unittest.TestCase):
    def _environment(self):
        src=FILE.read_text()
        tree=ast.parse(src)
        names=('_eligible_human_adult','_adult_infos','_still_adult')
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        species=SimpleNamespace(HUMAN=1,DOG=2,CAT=3,HORSE=4,FOX=5)
        age=SimpleNamespace(TEEN=15,YOUNGADULT=20,ADULT=30,ELDER=40)
        humans=[
            SimpleNamespace(sim_id=101,age=age.YOUNGADULT,
                            species=species.HUMAN,first_name='Jules',last_name='Green'),
            SimpleNamespace(sim_id=102,age=age.ADULT,
                            species=species.HUMAN,first_name='Bella',last_name='Goth'),
            SimpleNamespace(sim_id=103,age=age.ELDER,
                            species=species.HUMAN,first_name='Mortimer',last_name='Goth')]
        animals=[
            SimpleNamespace(sim_id=201,age=age.ADULT,
                            species=species.DOG,first_name='Buddy',last_name='Dog'),
            SimpleNamespace(sim_id=202,age=age.ADULT,
                            species=species.CAT,first_name='Mimi',last_name='Cat'),
            SimpleNamespace(sim_id=203,age=age.ELDER,
                            species=species.HORSE,first_name='Spirit',last_name='Horse'),
            SimpleNamespace(sim_id=204,age=age.ADULT,
                            species=species.FOX,first_name='Fox',last_name='Fox')]
        others=[
            SimpleNamespace(sim_id=300,age=age.TEEN,
                            species=species.HUMAN,first_name='Blair',last_name='Bass'),
            SimpleNamespace(sim_id=301,age=age.ADULT,
                            first_name='Unknown',last_name='Species')]
        all_sims=humans+animals+others
        mgr=SimpleNamespace(
            get_all=lambda:list(all_sims),
            get=lambda sid:next((s for s in all_sims if s.sim_id==sid),None))
        ns={
            'Species':species,
            '_ADULT_AGES':(age.YOUNGADULT,age.ADULT,age.ELDER),
            'services':SimpleNamespace(sim_info_manager=lambda:mgr),
            'canonical_sim_id':lambda sid:str(int(sid)),
            'StaffError':ValueError,
        }
        exec(compile(ast.Module(body=nodes,type_ignores=[]),
                     '<M54 real staff filter>',mode='exec'),ns)
        return ns,mgr,humans,animals,others

    def test_adults_humans_only_in_picker(self):
        ns,_,humans,animals,others=self._environment()
        selected=ns['_adult_infos']()
        self.assertEqual({s.sim_id for s in selected},{101,102,103})
        self.assertTrue(all(ns['_eligible_human_adult'](s) for s in humans))
        self.assertTrue(all(not ns['_eligible_human_adult'](s) for s in animals+others))

    def test_commit_rejects_dog_cat_horse_fox_and_unknown_species(self):
        ns,_,humans,animals,others=self._environment()
        self.assertTrue(all(ns['_still_adult'](str(s.sim_id)) for s in humans))
        self.assertFalse(any(ns['_still_adult'](str(s.sim_id))
                             for s in animals+others))
        self.assertFalse(ns['_still_adult']('999999'))
        self.assertFalse(ns['_still_adult']('not-a-sim'))

    def test_m53_in_game_menu_package_unchanged(self):
        self.assertEqual(package_bytes(),m53_package())
        self.assertEqual(len(SCRIPTS),19)
        self.assertIn('mhs53_staff_ui.py',[p.name for p in SCRIPTS])

    def test_legacy_pet_can_be_removed_not_appointed(self):
        source=FILE.read_text()
        tree=ast.parse(source)
        ui=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                and n.name=='open_staff')
        fragment=source.split('def open_staff(',1)[1].split('class _StaffAction(',1)[0]
        # Clean-up list uses actual assigned SimInfos, not only new human filter.
        self.assertIn('mgr.get(int(sid))',fragment)
        self.assertIn("if mode=='assign' and not all(_still_adult(sid)",fragment)
        self.assertIn("candidates=[info for info in _adult_infos()",fragment)
        self.assertIn('stats=_STAFF.apply',fragment)

    def test_no_data_or_staff_role_limit_changes(self):
        from tooling.build_m53_staff_management import ACTIONS
        self.assertEqual(len(ACTIONS),17)
        self.assertEqual(
            [item[0] for item in ACTIONS][:3],
            ['PrincipalChoose','PrincipalRemove','PrincipalView'])


if __name__=='__main__':
    unittest.main()
