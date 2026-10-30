"""Reference-shape test: passing does not certify runtime."""
import importlib.util
from pathlib import Path
import unittest
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("m1audit",root/"tooling"/"m1_schema_review.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=m.inspect()
    def test_native_picker_structure(self):self.assertIn("Native picker",self.x["matched"])
    def test_both_classes_reported(self):
        self.assertEqual({x["class"] for x in self.x["review_items"]},{1,2})
    def test_candidate_test_is_not_assumed_valid(self):
        self.assertEqual(sum(x["code"]=="PICKEDSIM_AGE_TEST_UNVERIFIED" for x in self.x["review_items"]),2)
    def test_title_needs_review(self):
        self.assertEqual(sum(x["code"]=="NOTIFICATION_TITLE_UNVERIFIED" for x in self.x["review_items"]),2)
    def test_timing_needs_review(self):
        self.assertEqual(sum(x["code"]=="NOTIFICATION_TIMING_UNVERIFIED" for x in self.x["review_items"]),2)
    def test_version_gap_explicit(self):
        self.assertNotEqual(self.x["ea_version"],self.x["lot51_tdesc_version"])
    def test_unverified_not_declared_ready(self):
        self.assertEqual(self.x["status"],"NOT_READY_FOR_GAME")
        self.assertIs(self.x["release_ready"],False)
    def test_two_distinct_picker_sources(self):
        a=m.ET.parse(m.F/"ChooseClass1.xml").getroot()
        b=m.ET.parse(m.F/"ChooseClass2.xml").getroot()
        self.assertNotEqual(a.get("s"),b.get("s"))
if __name__=="__main__":unittest.main()
