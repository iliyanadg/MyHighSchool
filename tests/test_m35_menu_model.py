"""Verify desired MY HIGH SCHOOL menu visibility without touching real UI."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT/'src'/'m2_registry',ROOT/'src'/'m35_menu'):
    if str(p) not in sys.path:
        sys.path.insert(0,str(p))

from mhs34_settings import SchoolSettings
from mhs_m2_roster import SchoolRoster
from mhs35_menu_model import build_menu, can_select_class, MenuModelError


class M35VisibilityTests(unittest.TestCase):
    def setUp(self):
        self.roster=SchoolRoster('11',{
            '101':1,'102':1,'201':2,'202':2
        })

    def test_disactivated_shows_only_enable(self):
        menu=build_menu(SchoolSettings('11',False,2),self.roster)
        self.assertEqual(menu['actions'],('attiva',))
        self.assertEqual(menu['classes'],())
        self.assertFalse(can_select_class(SchoolSettings('11',False,3),1))

    def test_two_classes_only(self):
        setting=SchoolSettings('11',True,2)
        menu=build_menu(setting,self.roster)
        self.assertEqual(menu['actions'],('disattiva','impostazioni'))
        self.assertEqual(tuple(x['class_id'] for x in menu['classes']),(1,2))
        self.assertEqual(menu['classes'][0]['enrolled'],2)
        self.assertEqual(menu['classes'][0]['actions'],(
            ('iscrivi',1),('consulta',1),('rimuovi',1),
            ('trasferisci',1,2)))
        self.assertFalse(can_select_class(setting,3))

    def test_three_classes_with_two_transfer_targets(self):
        setting=SchoolSettings('11',True,3)
        menu=build_menu(setting,self.roster)
        self.assertEqual(len(menu['classes']),3)
        self.assertEqual(menu['classes'][2]['enrolled'],0)
        self.assertEqual(menu['classes'][2]['actions'],(
            ('iscrivi',3),('consulta',3),('rimuovi',3),
            ('trasferisci',3,1),('trasferisci',3,2)))
        self.assertTrue(can_select_class(setting,3))

    def test_each_submenu_contains_its_own_source_class(self):
        menu=build_menu(SchoolSettings('11',True,3),self.roster)
        for tab in menu['classes']:
            klass=tab['class_id']
            self.assertEqual(tab['capacity'],8)
            for action in tab['actions']:
                self.assertEqual(action[1],klass)

    def test_different_save_slots_fail_closed(self):
        with self.assertRaises(MenuModelError):
            build_menu(SchoolSettings('12',True,3),self.roster)

    def test_optional_third_class_can_be_enabled_later(self):
        two=build_menu(SchoolSettings('11',True,2),self.roster)
        self.assertEqual(two['settings_options'][0]['action'],
                         'abilita_classe3')
        self.assertTrue(two['settings_options'][0]['enabled'])
        self.assertEqual(len(two['classes']),2)

        three=build_menu(SchoolSettings('11',True,3),self.roster)
        self.assertEqual(three['settings_options'][0]['action'],
                         'disabilita_classe3')
        self.assertTrue(three['settings_options'][0]['enabled'])
        self.assertEqual(len(three['classes']),3)

        occupied=SchoolRoster('11',{'99':3})
        three_full=build_menu(SchoolSettings('11',True,3),occupied)
        self.assertFalse(three_full['settings_options'][0]['enabled'])

    def test_model_has_no_mutation(self):
        before=self.roster.to_json()
        build_menu(SchoolSettings('11',True,3),self.roster)
        self.assertEqual(self.roster.to_json(),before)


if __name__=='__main__':
    unittest.main()
