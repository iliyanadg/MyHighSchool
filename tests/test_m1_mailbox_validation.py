"""No EA mod installed or run; checks the source wiring only."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mailbox_check',ROOT/'tooling'/'m1_mailbox_validation.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MailboxWiringTests(unittest.TestCase):
    def test_validated_source_matches_official_injector_shape(self):
        result=mod.validate_injector()
        self.assertEqual(result['status'],'STATIC_SCHEMA_SHAPE_ONLY')

    def test_standard_and_wall_mailboxes_are_selected(self):
        self.assertEqual(mod.validate_injector()['mailbox_object_ids'],['14940','133176'])

    def test_injects_two_known_picker_interactions(self):
        self.assertEqual(mod.validate_injector()['affordance_ids'],list(mod.VALID_IDS))

    def test_uses_single_xml_injector_not_both_frameworks(self):
        root=mod.ET.parse(str(mod.INJECTOR)).getroot()
        self.assertEqual(root.attrib['m'],'xml_injector.snippet')
        self.assertEqual(root.attrib['c'],'XmlInjector')

    def test_custom_snippet_id_has_high_bit(self):
        root = mod.ET.parse(str(mod.INJECTOR)).getroot()
        self.assertTrue(int(root.attrib['s']) & (1 << 63))

    def test_snippet_id_matches_fnv64_highbit_of_name(self):
        root = mod.ET.parse(str(mod.INJECTOR)).getroot()
        self.assertEqual(int(root.attrib['s']), mod.fnv64_highbit(root.attrib['n']))
        self.assertEqual(int(root.attrib['s']), 11407916219541495957)

    def test_previous_low_bit_snippet_id_rejected(self):
        original = mod.INJECTOR.read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'old.xml'
            path.write_text(original.replace('11407916219541495957',
                                            '2184544182686720149'), encoding='utf-8')
            with self.assertRaises(mod.MailboxValidationError):
                mod.validate_injector(path)

    def test_bad_object_tuning_is_rejected(self):
        original=mod.INJECTOR.read_text(encoding='utf-8')
        self.assertIn('14940',original)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'broken.xml'
            path.write_text(original.replace('<T>14940</T>','<T>99999</T>'),encoding='utf-8')
            with self.assertRaises(mod.MailboxValidationError):
                mod.validate_injector(path)

    def test_bad_picker_reference_is_rejected(self):
        original=mod.INJECTOR.read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'broken.xml'
            path.write_text(original.replace('10604127343160706865','99999'),encoding='utf-8')
            with self.assertRaises(mod.MailboxValidationError):
                mod.validate_injector(path)


if __name__=='__main__': unittest.main()
