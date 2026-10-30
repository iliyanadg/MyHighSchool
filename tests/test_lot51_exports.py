"""Regressions for user-exported Lot51 XML sources (not game compatibility)."""
from pathlib import Path
import importlib.util
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pair', ROOT/'tooling'/'lot51_source_pair.py')
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)
M1 = ROOT/'src'/'experiments'/'m1_unbuilt'
OLD = ROOT/'src'/'experiments'/'m0_failed'


class ExportedPairTests(unittest.TestCase):
    def test_two_exports_match(self):
        self.assertEqual(pair.check_pair()['status'], 'XML_SOURCES_MATCH_ONLY')

    def test_two_picker_links_use_the_new_instance(self):
        for n in (1,2):
            root=ET.parse(M1/('ChooseClass'+str(n)+'.xml')).getroot()
            self.assertEqual(root.find('./T[@n="category"]').text, str(pair.CATEGORY_ID))

    def test_original_failed_m0_preserved(self):
        root=ET.parse(OLD/'Category.xml').getroot()
        self.assertNotEqual(root.attrib['s'], str(pair.CATEGORY_ID))

    def test_simdata_is_xml_not_binary(self):
        self.assertTrue(pair.SIMDATA.read_bytes().startswith(b'<?xml'))
        self.assertFalse(pair.SIMDATA.read_bytes().startswith(b'DATA'))

    def test_invalid_tgi_filename_rejected(self):
        with self.assertRaises(pair.PairError):
            pair.check_pair(pair.SIMDATA,pair.TUNING)


if __name__=='__main__':
    unittest.main()
