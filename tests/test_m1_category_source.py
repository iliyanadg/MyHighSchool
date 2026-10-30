"""Source-link regression for user-exported Lot51 tuning (not game launch)."""
from pathlib import Path
import xml.etree.ElementTree as ET
import unittest

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "src" / "experiments" / "m0_failed"
NEW = ROOT / "src" / "experiments" / "m1_unbuilt"

class MenuCategorySourceTests(unittest.TestCase):
    def test_builder_source_has_correct_tuning_class(self):
        root = ET.parse(NEW / "Category_for_Tdesc.xml").getroot()
        self.assertEqual(root.attrib.get("c"), "PieMenuCategory")
        self.assertEqual(root.attrib.get("i"), "pie_menu_category")

    def test_builder_source_preserves_picker_category_refs(self):
        root = ET.parse(NEW / "Category_for_Tdesc.xml").getroot()
        category_id = root.attrib["s"]
        for number in (1, 2):
            picker = ET.parse(NEW / ("ChooseClass"+str(number)+".xml")).getroot()
            self.assertEqual(picker.find("./T[@n='category']").text.strip(), category_id)

    def test_builder_source_references_existing_display_name_key(self):
        root = ET.parse(NEW / "Category_for_Tdesc.xml").getroot()
        self.assertEqual(root.find("./T[@n='_display_name']").text, "0x3FCE8D06")

    def test_builder_source_is_not_accidentally_a_package(self):
        raw = (NEW / "Category_for_Tdesc.xml").read_bytes()
        self.assertFalse(raw.startswith(b"DBPF"))
        self.assertTrue(raw.startswith(b"<?xml"))

if __name__ == "__main__":
    unittest.main()
