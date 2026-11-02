"""M104 tests the native EA filter path, not explicit guest lists."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m104_native'))
from mhs104_native_policy import eligible_npcs,native_base_arguments
CLASSES=(tuple(range(1,9)),tuple(range(9,17)))
class NativeSchoolFilterTests(unittest.TestCase):
    def test_16_with_three_playables_keeps_exact_13(self):
        result=eligible_npcs(CLASSES,(1,9,10),())
        self.assertEqual(len(result),13)
        self.assertEqual(set(result),set(range(1,17))-{1,9,10})
    def test_present_npc_excluded(self):
        result=eligible_npcs(CLASSES,(1,9,10),(3,14))
        self.assertNotIn(3,result)
        self.assertNotIn(14,result)
        self.assertEqual(len(result),11)
    def test_bad_cohort_fails_without_random_fallback(self):
        for roster in ((CLASSES[0],CLASSES[1][:-1]),
                       (CLASSES[0],CLASSES[0]),()):
            self.assertIsNone(eligible_npcs(roster,(1,9,10),()))
        self.assertIsNone(eligible_npcs(CLASSES,(99,),()))
        self.assertIsNone(eligible_npcs(CLASSES,(1,9,10),(0,)))
    def test_one_original_matching_request_only(self):
        ids=eligible_npcs(CLASSES,(1,9,10),())
        args=(1,object())
        action,a,kw,reason=native_base_arguments(
            'matching',args,{'allow_yielding':False},280516,ids)
        self.assertEqual(action,'constrain')
        self.assertEqual(a,args)
        self.assertEqual(tuple(kw['sim_constraints']),ids)
        self.assertIs(kw['continue_if_constraints_fail'],False)
        self.assertIs(kw['conform_if_constraints_fail'],False)
        self.assertEqual(kw['allow_yielding'],False)
    def test_matching_explicit_constraint_preserved(self):
        args=(1,'tuning',None,None,(77,))
        action,new,kw,_=native_base_arguments(
            'matching',args,{'allow_yielding':True},280516,(2,3))
        self.assertEqual(action,'preserve')
        self.assertEqual(new,args)
        self.assertEqual(kw,{'allow_yielding':True})
    def test_no_staff_core_or_late_submit_filter(self):
        for mode,guid in (('filter',280516),('matching',276592),
                          ('matching',296396),('matching',9999)):
            action,a,kw,_=native_base_arguments(
                mode,(1,'tuning'),{'other':17},guid,(2,3))
            self.assertEqual(action,'preserve')
            self.assertEqual(kw['other'],17)
    def test_positional_matching_flags_not_broken(self):
        args=(1,'tuning',None,None,None,None,None,None,True,True)
        action,modified,kw,_=native_base_arguments(
            'matching',args,{},280516,(2,3))
        self.assertEqual(action,'constrain')
        self.assertEqual(modified[4],(2,3))
        self.assertIs(modified[8],False)
        self.assertIs(modified[9],False)
    def test_unknown_candidates_do_not_enable_random_ones(self):
        self.assertEqual(native_base_arguments(
            'matching',(1,'tuning'),{},280516,())[0],'block')
        self.assertEqual(native_base_arguments(
            'matching',(1,'tuning'),{},280516,None)[0],'block')

if __name__=='__main__':
    unittest.main()
