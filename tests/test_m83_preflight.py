"""M83 offline regressions: old-mod patterns never certify EA attendance."""
import ast
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m83_compatibility'))
from mhs83_preflight import full_roster_preflight,read_game_version,MAC_PATCH

CLASSES={1:tuple(str(n) for n in range(1,9)),
         2:tuple(str(n) for n in range(9,17))}
PHASES={'go_to_class_1':8,'attend_class_1':8,
        'go_to_class_2':8,'attend_class_2':8}

def gate(**kwargs):
    values={'game_version':'1.129.39.1230','class_members':CLASSES,
            'verified_human_teen_ids':tuple(str(i) for i in range(1,17)),
            'playable_ids':('1','9','99'),'verified_core_student_ids':('2','10'),
            'available_base_student_slots':12,'verified_phase_caps':PHASES,
            'installed_other_mods':('SonozakiSisters_Elementary_School_Management_IT.package',)}
    values.update(kwargs)
    return full_roster_preflight(**values)

class M83Tests(unittest.TestCase):
    def test_gameversion_prefix_and_unsupported_builds(self):
        self.assertEqual(read_game_version(bytes((0,0,0))+b'1.129.39.1230'),MAC_PATCH)
        self.assertIsNone(read_game_version('unknown'))
        for game in ('1.128.90.1230','1.129.39.1030','',None,'1.130.0.1230'):
            self.assertEqual(gate(game_version=game)['status'],'BLOCKED')
    def test_full_two_class_offline_plan_not_attendance(self):
        out=gate()
        self.assertEqual(out['status'],'OFFLINE_PLAN_ONLY')
        self.assertEqual(out['classes'][1],CLASSES[1])
        self.assertEqual(out['classes'][2],CLASSES[2])
        self.assertEqual(len(out['planned_base_npcs']),12)
        self.assertEqual(out['registered_playables'],('1','9'))
        self.assertFalse(out['school_attendance_proven'])
        self.assertFalse(out['runtime_mutations'])
    def test_classroom_capacity_and_no_duplicate(self):
        for classes in ({1:('1',)*8,2:CLASSES[2]},
                        {1:CLASSES[1][:-1],2:CLASSES[2]},
                        {1:CLASSES[1],2:CLASSES[1]},
                        {1:CLASSES[1],2:CLASSES[2],3:()}):
            self.assertEqual(gate(class_members=classes)['status'],'BLOCKED')
    def test_eligibility_and_core_not_assumed(self):
        self.assertEqual(gate(verified_human_teen_ids=CLASSES[1])['status'],'BLOCKED')
        self.assertEqual(gate(verified_human_teen_ids=None)['status'],'BLOCKED')
        self.assertEqual(gate(verified_core_student_ids=None)['status'],'BLOCKED')
        self.assertEqual(gate(verified_core_student_ids=('1',))['status'],'BLOCKED')
    def test_six_vanilla_base_seats_not_sixteen(self):
        out=gate(available_base_student_slots=6)
        self.assertEqual(out['status'],'BLOCKED')
        self.assertEqual(out['required_base_slots'],12)
    def test_requires_both_class_phase_capacities(self):
        self.assertEqual(gate(verified_phase_caps=None)['status'],'BLOCKED')
        self.assertEqual(gate(verified_phase_caps=dict(PHASES,attend_class_2=7))['status'],'BLOCKED')
        self.assertEqual(gate(verified_phase_caps={'attend_class_1':9})['status'],'BLOCKED')
    def test_old_hs_mods_blocked_but_elementary_not_automatically(self):
        for name in ('ksuihuh_HS_MoreStudents_18.package',
                     'SonozakiSisters_High_School_Management_2.2.1.package',
                     'HighSchoolMoreClassmates.package',
                     'Rex_ChooseHighSchoolClassmates.ts4script'):
            self.assertEqual(gate(installed_other_mods=(name,))['status'],'BLOCKED')
        self.assertEqual(gate()['status'],'OFFLINE_PLAN_ONLY')
    def test_pure_not_live_ea_modifications(self):
        source=(ROOT/'src'/'m83_compatibility'/'mhs83_preflight.py').read_text()
        ast.parse(source)
        for fragment in ('import services','create_situation(', 'add_guest_info(',
                         'remove_guest_info(','set_trait(','setattr(','os.remove('):
            self.assertNotIn(fragment,source)

if __name__=='__main__':
    unittest.main()
