"""Six offline regressions for M0 and unbuilt notification corrections."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("m0_checker",ROOT/"tooling"/"m0_tuning_audit.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
F=ROOT/"src"/"experiments"/"m0_failed"
C=ROOT/"src"/"experiments"/"m1_unbuilt"

class M0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((F/"resource_inventory.json").read_text(encoding="utf-8"))
        cls.issues=mod.audit(F,cls.manifest)

    def test_missing_simdata_is_not_ignored(self):
        self.assertIn("MISSING_CATEGORY_SIMDATA",self.issues)

    def test_original_notification_placement_is_flagged(self):
        for n in (1,2):
            self.assertIn("CONFIRM_EXTRAS_AT_ROOT:"+str(n),self.issues)
            self.assertIn("CONFIRM_NOTIFICATION_NOT_IN_OUTCOME:"+str(n),self.issues)

    def test_original_links_are_intact(self):
        self.assertFalse([x for x in self.issues if "LINK" in x])

    def test_broken_continuation_detected(self):
        raw=(F/"ChooseClass1.xml").read_text(encoding="utf-8").replace("13813934116852558422","9999999999999999999")
        problems=mod.audit(F,self.manifest,{"ChooseClass1":raw})
        self.assertIn("PICKER_CONTINUATION_LINK:1",problems)

    def test_corrected_notification_xml_is_well_formed(self):
        alternatives={name:(C/(name+".xml")).read_bytes() for name in ("ConfirmClass1","ConfirmClass2")}
        problems=mod.audit(F,self.manifest,alternatives)
        self.assertFalse([x for x in problems if x.startswith(("CONFIRM_EXTRAS_AT_ROOT","CONFIRM_NOTIFICATION_NOT_IN_OUTCOME"))])
        self.assertIn("MISSING_CATEGORY_SIMDATA",problems)

    def test_all_source_xml_files_are_well_formed(self):
        import xml.etree.ElementTree as ET
        for name in mod.NAMES:
            ET.parse(F / (name + ".xml"))

    def test_manifest_matches_8_resource_M0_inventory(self):
        self.assertEqual(self.manifest["resource_count"],8)
        self.assertEqual(self.manifest["simdata_instances"],[])
        self.assertEqual(self.manifest["category_instances"],["7064630105397426819"])

if __name__ == "__main__":
    unittest.main()
