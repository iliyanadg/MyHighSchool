"""The *source* menu/STBL chain is complete; game loading is unverified."""
from pathlib import Path
import importlib.util
import json
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('m1_links', ROOT / 'tooling' / 'm1_links_and_strings.py')
m1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m1)


class MenuAndStringTests(unittest.TestCase):
    def test_native_pickers_point_to_new_menu(self):
        self.assertEqual(m1.check_links()['category_id'], m1.CATEGORY_ID)

    def test_both_picker_and_confirmation_chains_present(self):
        self.assertEqual(m1.check_links()['class_choices'], 2)

    def test_nine_localization_keys_referenced_and_defined(self):
        self.assertEqual(m1.check_links()['referenced_text_keys'], 9)

    def test_eight_students_max_for_both_pickers(self):
        self.assertEqual(m1.check_links()['max_selectable_per_picker'], 8)

    def test_italian_STBL_roundtrip(self):
        instance, raw = m1.compile_stbl('it')
        self.assertEqual(instance >> 56, 0x0B)
        table = m1.parse_stbl(raw)
        self.assertEqual(len(table), 9)
        self.assertEqual(table[0x3FCE8D06], 'MY HIGH SCHOOL (PROVA)')
        self.assertIn('Nessuna iscrizione', table[0x7FE4CEBC])

    def test_english_fallback_STBL_roundtrip(self):
        instance, raw = m1.compile_stbl('en')
        self.assertEqual(instance >> 56, 0)
        table = m1.parse_stbl(raw)
        self.assertEqual(len(table), 9)
        self.assertEqual(table[0xEA9F0D60], 'Test selecting Class 2')

    def test_classes_have_distinct_entries(self):
        self.assertNotEqual(m1.PICKER_IDS['1'], m1.PICKER_IDS['2'])
        self.assertNotEqual(m1.CONFIRM_IDS['1'], m1.CONFIRM_IDS['2'])

    def test_picker_is_no_save_test_only(self):
        doc = json.loads(m1.LOCALIZATION.read_text(encoding='utf-8'))
        self.assertIn('never saves', doc['purpose'])
        it = {x['name']: x['it'] for x in doc['entries']}
        self.assertIn('Nessuna iscrizione', it['DialogText'])

    def test_unbuilt_only_no_package_in_source_directory(self):
        self.assertFalse(list(m1.M1.glob('*.package')))
        self.assertFalse(list(m1.M1.glob('*.ts4script')))


if __name__ == '__main__':
    unittest.main()
