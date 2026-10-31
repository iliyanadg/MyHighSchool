"""M57 pre-spawn EA filter tests: preserve calls, restrict exact IDs."""
import ast
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for path in ('src/m57_selection','src/m2_registry','src/m53_staff'):
    sys.path.insert(0,str(ROOT/path))

from mhs_m2_roster import SchoolRoster
from mhs53_staff_store import StaffRoster
from mhs57_school_manifest import make_manifest
from mhs57_filter_policy import (
    STUDENT_FILTER, STAFF_FILTERS, CORE_FILTERS, SCHOOL_FILTERS,
    guid_for_filter, choose_constraints, apply_constraints,
    is_competing_high_school_mod)


def manifest():
    roster=SchoolRoster(11, {str(i):1 if i<=8 else 2 for i in range(1,17)})
    roles={'principal':'201','teacher1':'202','teacher2':'203','teacher3':None,
           'cafeteria':['204','205','206'],'custodians':['207','208']}
    staff=StaffRoster(11,roles)
    return make_manifest(roster,staff,2,('1','2','17','18','19'))


class M57EAFilterTests(unittest.TestCase):
    def test_known_ep12_guids(self):
        self.assertEqual(STUDENT_FILTER,280516)
        self.assertEqual(STAFF_FILTERS[300742],'principal')
        self.assertEqual(STAFF_FILTERS[296396],'teacher1')
        self.assertEqual(STAFF_FILTERS[300741],'teacher2')
        self.assertEqual(STAFF_FILTERS[300744],'custodians')
        self.assertEqual(STAFF_FILTERS[300743],'cafeteria')
        self.assertIn(303766,CORE_FILTERS)
        self.assertNotIn(280756,SCHOOL_FILTERS) # Prom unrelated to school day
        obj=type('FilterTuning',(),{'guid64':280516})
        self.assertEqual(guid_for_filter(obj),280516)

    def test_student_filter_uses_only_registry_nonplayables(self):
        m=manifest()
        action,ids,role=choose_constraints(m,280516)
        self.assertEqual(action,'constrain')
        self.assertEqual(ids,tuple(range(3,17)))
        self.assertEqual(role,'student')

    def test_explicit_ea_constraints_intersect_not_overwrite(self):
        m=manifest()
        action,ids,note=choose_constraints(m,280516,[4,7,999])
        self.assertEqual(action,'constrain')
        self.assertEqual(ids,(4,7))
        self.assertEqual(choose_constraints(m,280516,[999])[0],'bypass')
        self.assertEqual(choose_constraints(m,280516,[])[0],'bypass')

    def test_staff_exact_roles_and_no_nonregistered(self):
        m=manifest()
        self.assertEqual(choose_constraints(m,300742)[1],(201,))
        self.assertEqual(choose_constraints(m,296396)[1],(202,))
        self.assertEqual(choose_constraints(m,300741)[1],(203,))
        self.assertEqual(choose_constraints(m,300743)[1],(204,205,206))
        self.assertEqual(choose_constraints(m,300744)[1],(207,208))

    def test_core_roles_vanilla_until_explicit_mhs_core_roles(self):
        m=manifest()
        for guid in CORE_FILTERS:
            self.assertEqual(choose_constraints(m,guid)[0],'preserve')
        self.assertEqual(choose_constraints(m,999999)[0],'bypass')

    def test_matching_kwargs_and_original_not_mutated(self):
        m=manifest()
        kw={'sim_filter':type('SchoolFilter',(),{'guid64':STUDENT_FILTER}),
            'allow_yielding':False, 'number_of_sims_to_find':2}
        args=()
        newa,newkw,info=apply_constraints(args,kw,'matching',m)
        self.assertEqual(args,())
        self.assertNotIn('sim_constraints',kw)
        self.assertEqual(newkw['sim_constraints'],tuple(range(3,17)))
        self.assertIs(newkw['continue_if_constraints_fail'],False)
        self.assertIs(newkw['conform_if_constraints_fail'],False)
        self.assertEqual(info[0],'constrain')

    def test_matching_positional_args_and_kwargs(self):
        m=manifest()
        obj=type('TeacherFilter',(),{'guid64':296396})
        original=(1,obj,None,None,None,None,None,None,True,True)
        newa,newkw,report=apply_constraints(original,{},'matching',m)
        self.assertEqual(newa[4],(202,))
        self.assertEqual(newa[8:10],(False,False))
        self.assertEqual(original[4],None)
        self.assertEqual(original[8:10],(True,True))
        self.assertEqual(newkw,{})
        self.assertEqual(report[2],'teacher1')

    def test_submit_filter_has_different_positions(self):
        m=manifest()
        obj=type('PrincipalFilter',(),{'guid64':300742})
        original=(obj,None,None,None,'other')
        newa,kw,report=apply_constraints(original,{},'filter',m)
        self.assertEqual(newa[3],(201,))
        self.assertEqual(newa[4],'other')
        self.assertEqual(report[0],'constrain')

    def test_non_school_filter_unchanged(self):
        m=manifest()
        obj=type('UnrelatedFilter',(),{'guid64':280756})
        args=(1,obj)
        kw={'callback':lambda:None}
        a,b,report=apply_constraints(args,kw,'matching',m)
        self.assertEqual(a,args)
        self.assertEqual(b,kw)
        self.assertEqual(report[0],'bypass')

    def test_filter_adapter_can_call_exact_original_unchanged_on_failure(self):
        src=(ROOT/'src'/'m57_selection'/'mhs57_filter_runtime.py').read_text()
        f=next(n for n in ast.parse(src).body
               if isinstance(n,ast.FunctionDef) and n.name=='_filtered')
        events=[]
        def original(self,*args,**kw):
            events.append((args,kw))
            return 'EA success'
        fake=type('Svc',(),{})()
        ctx={'guid_for_filter':guid_for_filter,'SCHOOL_FILTERS':SCHOOL_FILTERS,
             '_CONFLICTS':(),
             '_manifest':lambda:manifest(),
             'apply_constraints':apply_constraints,
             '_log':lambda *items:events.append(items)}
        exec(compile(ast.Module(body=[f],type_ignores=[]),'adapter_test','exec'),ctx)
        obj=type('filter_Student',(),{'guid64':280516})
        result=ctx['_filtered'](original,fake,(1,obj),{},'matching')
        self.assertEqual(result,'EA success')
        self.assertEqual(events[-1][1]['sim_constraints'],tuple(range(3,17)))
        events[:]=[]
        ctx['_manifest']=lambda:1/0
        self.assertEqual(ctx['_filtered'](original,fake,(1,obj),{},'matching'),
                         'EA success')
        self.assertEqual(events[-1],((1,obj),{}))

    def test_physical_status_counts_selected_not_entire_lot(self):
        source=(ROOT/'src'/'m57_selection'/'mhs57_filter_runtime.py').read_text()
        tree=ast.parse(source)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                and n.name=='physical_status')
        m=manifest()
        from types import SimpleNamespace
        people=[]
        for sid in (3,4,9,17,18,201,202,301):
            age=1 if sid<200 else 2
            people.append(SimpleNamespace(sim_id=sid,age=age,species=10,
                          get_sim_instance=lambda:object()))
        ctx={
            '_manifest':lambda:m,
            'services':SimpleNamespace(sim_info_manager=lambda:
                         SimpleNamespace(get_all=lambda:people)),
        }
        import types
        fake=types.ModuleType('sims')
        fake_types=types.ModuleType('sims.sim_info_types')
        fake_types.Age=SimpleNamespace(TEEN=1)
        fake_types.Species=SimpleNamespace(HUMAN=10)
        import sys
        old=sys.modules.get('sims')
        old_types=sys.modules.get('sims.sim_info_types')
        sys.modules['sims']=fake
        sys.modules['sims.sim_info_types']=fake_types
        try:
            exec(compile(ast.Module(body=[fn],type_ignores=[]),
                         '<m57 physical_status>','exec'),ctx)
            text=ctx['physical_status']()
        finally:
            if old is None:
                sys.modules.pop('sims',None)
            else:
                sys.modules['sims']=old
            if old_types is None:
                sys.modules.pop('sims.sim_info_types',None)
            else:
                sys.modules['sims.sim_info_types']=old_types
        self.assertIn('iscritti 3/16',text)
        self.assertIn('altri adolescenti 2',text)
        self.assertIn('personale scelto 2/8',text)

    def test_conflict_guard_blocks_only_actual_high_school_controllers(self):
        src=(ROOT/'src'/'m57_selection'/'mhs57_filter_runtime.py').read_text()
        self.assertIn("_CONFLICTS=_find_conflicting_school_mods()",src)
        self.assertIn("if _CONFLICTS:",src)
        self.assertIn("is_competing_high_school_mod(name)",src)
        self.assertNotIn("os.remove(",src)
        self.assertNotIn("os.unlink(",src)
        ast.parse(src)

        # These are the EXACT filenames shown by the user in game (M57).
        unrelated=[
            '!_SonozakiSisters_KatieMods_MegaInteractions_ALLMERGED_Traduzione_ITA_[bySha_Tsita].package',
            'SonozakiSisters_Elementary_School_Management_IT.package',
            'SonozakiSisters_MegaInteractions.ts4script',
            'Sims4_Drama_Translation_ITA.package',
            'Zerbu_Go_To_School_v5.ts4script',
            'SonozakiSisters_High_School_Management_TRADUZIONE_ITA.package',
        ]
        actual=[
            'SonozakiSisters_High_School_Management_2.2.1.package',
            'SonozakiSisters_High_School_Management_2.2.1.ts4script',
            'MoreStudents18.package',
            'ksuihuh_More_Students.package',
            'Choose_Your_High_School_Classmates.package',
            'Rex_ChooseHighSchoolClassmates.ts4script',
            'HighSchoolMoreClassmates.package',
        ]
        self.assertTrue(all(not is_competing_high_school_mod(s) for s in unrelated))
        self.assertTrue(all(is_competing_high_school_mod(s) for s in actual))
        self.assertFalse(is_competing_high_school_mod('readme.md'))
        self.assertFalse(is_competing_high_school_mod(None))

    def test_does_not_copy_or_modify_game_tunings(self):
        runtime=(ROOT/'src'/'m57_selection'/'mhs57_filter_runtime.py').read_text()
        self.assertIn("('submit_matching_filter','submit_filter')",runtime)
        self.assertIn("current_slot(allow_travel=True)",runtime)
        self.assertNotIn("set_trait(",runtime)
        self.assertNotIn("create_situation(",runtime)
        self.assertNotIn("remove_sim_from_situation(",runtime)
        ast.parse(runtime)


if __name__=='__main__':
    unittest.main()
