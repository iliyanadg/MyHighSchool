"""Structural invariants for M85+EA capacity pilot; NOT in-game attendance."""
import unittest
import xml.etree.ElementTree as ET
from tooling.build_mhs_capacity_beta import (capacity_resources,
    combined_package,SCHEDULES,PHASES,_value,_original)
from tooling.simdata_release_gate import resources
from tooling.build_m55_attendance_trial import package_bytes

class TestCapacityBeta(unittest.TestCase):
    def test_exact_six_ea_tunings(self):
        rec=capacity_resources()
        self.assertEqual(len(rec),6)
        self.assertEqual(set(r[2] for r in rec),set(SCHEDULES+PHASES))
        self.assertTrue(all(r[0]==0x7DF2169C and r[1]==0x35 for r in rec))

    def test_schedule_min_is_still_six_max_sixteen(self):
        for typ,group,iid,raw in capacity_resources():
            if iid not in SCHEDULES:
                continue
            tuned=ET.fromstring(raw)
            schedules=[item for item in tuned.findall(
                './L[@n="long_term_situations"]/U')
                if _value(item.find('./T[@n="situation"]'))=='277733']
            self.assertEqual(len(schedules),1)
            count=schedules[0].find('./U[@n="count"]')
            self.assertEqual(_value(count.find('./T[@n="lower_bound"]')),'6')
            self.assertEqual(_value(count.find('./T[@n="upper_bound"]')),'16')
            original=_original(iid,'WeeklyScheduleDay')
            original_count=[x for x in original.findall(
                './L[@n="long_term_situations"]/U')
                if _value(x.find('./T[@n="situation"]'))=='277733'][0]
            original_count.find('./U[@n="count"]/T[@n="upper_bound"]').text='16'
            self.assertEqual(ET.tostring(tuned),ET.tostring(original))

    def test_classroom_four_upgraded_to_eight_only(self):
        for typ,group,iid,raw in capacity_resources():
            if iid not in PHASES:
                continue
            tuned=ET.fromstring(raw)
            jobs=tuned.findall('./L[@n="job_assignments"]/U')
            self.assertEqual(len(jobs),1)
            self.assertEqual(_value(jobs[0].find(
                './U[@n="sim_count"]/T[@n="upper_bound"]')),'8')
            original=_original(iid,'WeeklyScheduleSituationData')
            original.find(
                './L[@n="job_assignments"]/U/U[@n="sim_count"]/T[@n="upper_bound"]').text='8'
            self.assertEqual(ET.tostring(tuned),ET.tostring(original))

    def test_full_package_keeps_m85_byte_for_byte_resources(self):
        base=resources(package_bytes())
        merged=resources(combined_package())
        self.assertEqual(merged[:63],base)
        self.assertEqual(len(merged),69)
        self.assertEqual(merged[63:],capacity_resources())
        self.assertEqual(len(set(x[:3] for x in merged)),69)

if __name__=='__main__':
    unittest.main()
