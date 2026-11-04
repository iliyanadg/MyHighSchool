import unittest
from tooling.verify_ea_school_jobs import inspect_xml, REQUIRED, verify_folder
from pathlib import Path
from tempfile import TemporaryDirectory

class TestSchoolJobInputType(unittest.TestCase):
    def test_simdata_xml_with_same_job_name_is_rejected(self):
        for iid, name in REQUIRED.items():
            xml='<SimData><Instances><I name="%s" schema="SituationJob"/></Instances></SimData>' % name
            result=inspect_xml(xml,'545AC67A!000785C3!%016X.%s.SimData.xml' % (iid,name))
            self.assertEqual(result['status'],'BLOCKED')
            self.assertEqual(result['reason'],'SIMDATA_NOT_TUNING')
    def test_each_correct_job_tuning_is_recognized(self):
        for iid,name in REQUIRED.items():
            xml='<I c="SituationJob" i="situation_job" n="%s" s="%s"><V n="sim_auto_invite"/></I>'%(name,iid)
            result=inspect_xml(xml,'9C07855F!00000035!%016X.%s.xml'%(iid,name))
            self.assertEqual(result['status'],'TUNING_XML_RECEIVED_NOT_GAME_VALIDATED')
            self.assertEqual(result['instance'],iid)
            self.assertIn('sim_auto_invite',result['filter_or_invite_nodes'])
    def test_all_six_required_no_missing_roles(self):
        with TemporaryDirectory() as d:
            for iid,name in REQUIRED.items():
                Path(d,str(iid)+'.xml').write_text(
                    '<I c="SituationJob" i="situation_job" n="%s" s="%s"/>'%(name,iid))
            self.assertEqual(verify_folder(d)['status'],'SIX_JOB_TUNINGS_READY_FOR_REVIEW')
            Path(d,str(next(iter(REQUIRED)))+'.xml').unlink()
            self.assertEqual(verify_folder(d)['status'],'BLOCKED')
    def test_wrong_resource_tgi_rejected_even_if_tuning_shape(self):
        name=REQUIRED[277894]
        xml='<I c="SituationJob" i="situation_job" n="%s" s="277894"/>'%name
        r=inspect_xml(xml,'545AC67A!00000035!0000000000043D86.xml')
        self.assertEqual(r['reason'],'SIMDATA_NOT_TUNING')

if __name__ == '__main__':
    unittest.main()
