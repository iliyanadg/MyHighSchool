"""The unified day journal must leave previous M148 reports untouched."""
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/m148_clock'))
from mhs148_day_trace import DayJournal

class JournalPreservationTests(unittest.TestCase):
    def test_unified_report_preserves_old_reports_and_register(self):
        groups=(tuple(str(i) for i in range(1,9)),tuple(str(i) for i in range(9,17)))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            old=root/'MHS_M148_GIORNATA_LEZIONI_MENSA.json'
            registry=root/'Registro_slot_11.json'
            old.write_text('old report sentinel');registry.write_text('saved roster sentinel')
            journal=DayJournal(folder,'11',groups,
                output='MHS_CLASSROOM_CONTROL_GIORNATA_LEZIONI_MENSA.json')
            self.assertTrue(journal.flush())
            self.assertEqual(old.read_text(),'old report sentinel')
            self.assertEqual(registry.read_text(),'saved roster sentinel')
            self.assertTrue((root/journal.output).is_file())

    def test_arbitrary_data_file_or_parent_path_is_refused(self):
        groups=(tuple(str(i) for i in range(1,9)),tuple(str(i) for i in range(9,17)))
        for name in ('../MHS_report.json','Registro_slot_11.json','Impostazioni_slot_11.json'):
            with self.assertRaises(ValueError):DayJournal('/tmp','11',groups,output=name)

if __name__=='__main__':unittest.main()
