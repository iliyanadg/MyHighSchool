"""Read-only inventories preserve files and identify content, not file labels."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tooling.mod_inventory import inventory, main, write_report


class ModInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mods = self.root / 'Mods'
        self.mods.mkdir()
        self.data = self.root / 'MY_HIGH_SCHOOL_M25_TEST_DATA'
        self.data.mkdir()

    def archive(self, name, members):
        path = self.mods / name
        with zipfile.ZipFile(str(path), 'w') as archive:
            for member in members:
                archive.writestr(member, b'never executed')
        return path

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def test_colliding_archives_and_renamed_mhs_identified_from_members(self):
        first = self.archive('renamed.ts4script', ['mhs53_staff_ui.pyc', 'mhs_m2_roster.pyc'])
        second = self.archive('another.ts4script', ['mhs148_day_trace.pyc', 'mhs_m2_roster.pyc'])
        before = self.snapshot()
        report = inventory(self.mods)
        rows = {row['path']: row for row in report['files']}
        self.assertIn('M53-M54', rows[str(first)]['family'])
        self.assertEqual(rows[str(second)]['family'], 'M148')
        self.assertEqual(report['module_collisions'], [
            {'module': 'mhs_m2_roster', 'archives': sorted([str(first), str(second)])}])
        self.assertEqual(before, self.snapshot())

    def test_unknown_packages_and_third_party_preserved_despite_mhs_filename(self):
        package = self.mods / 'MHS_M148.package'
        package.write_bytes(b'unknown package')
        third = self.archive('Sonozaki_Elementary.ts4script', ['elementary.pyc'])
        mislabeled = self.archive('MY_HIGH_SCHOOL.ts4script', ['third_party.pyc'])
        before = self.snapshot()
        rows = {row['path']: row for row in inventory(self.mods)['files']}
        self.assertEqual(rows[str(package)]['ownership'], 'unknown')
        self.assertEqual(rows[str(package)]['action'], 'preserve_unverified_package')
        for path in (third, mislabeled):
            self.assertEqual(rows[str(path)]['ownership'], 'unknown')
            self.assertEqual(rows[str(path)]['action'], 'preserve_unknown_archive')
        self.assertEqual(before, self.snapshot())

    def test_all_data_and_saves_protected_even_unknown_names(self):
        for name in ('Registro_slot_11.json', 'Personale_slot_11.json',
                     'MHS97_RuoliSpeciali_slot_11.json', 'future_unknown.json'):
            (self.data / name).write_text('{"private": "not printed"}')
        (self.mods / 'slot.save.ver0').write_bytes(b'save')
        before = self.snapshot()
        report = inventory(self.mods)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(all(row['action'] == 'preserve_all_persistent_data'
                            for row in report['files'] if row['section'] == 'persistent_data'))
        self.assertEqual(next(row for row in report['files']
                              if row['relative_path'] == 'slot.save.ver0')['action'], 'preserve_save')
        self.assertNotIn('not printed', json.dumps(report))
        for output in (self.mods / 'report.json', self.data / 'report.json',
                       self.root / 'saves' / 'report.json', self.root / 'slot.save'):
            with self.assertRaises(ValueError):
                write_report(report, output)

    def test_symlink_outside_root_is_not_read_and_inventory_marked_incomplete(self):
        secret = self.root / 'outside.ts4script'
        secret.write_bytes(b'outside')
        (self.mods / 'escape.ts4script').symlink_to(secret)
        directory = self.root / 'outside-directory'
        directory.mkdir()
        (directory / 'other.package').write_bytes(b'outside directory')
        (self.mods / 'linked-dir').symlink_to(directory, target_is_directory=True)
        report = inventory(self.mods)
        self.assertFalse(report['complete'])
        self.assertEqual(report['files'], [])
        self.assertEqual(len(report['skipped']), 2)

    def test_release_manifest_hash_verifies_renamed_package_not_lookalike(self):
        trusted = self.mods / 'renamed.package'
        trusted.write_bytes(b'release package')
        lookalike = self.mods / 'MHS_CLASSROOM_CONTROL.package'
        lookalike.write_bytes(b'wrong release')
        digest = hashlib.sha256(trusted.read_bytes()).hexdigest()
        report = inventory(self.mods, manifest={'files': [
            {'name': 'MHS_CLASSROOM_CONTROL.package', 'sha256': digest}]})
        rows = {row['path']: row for row in report['files']}
        self.assertEqual(rows[str(trusted)]['ownership'], 'verified_release_manifest_hash')
        self.assertEqual(rows[str(lookalike)]['ownership'], 'unknown')
        self.assertEqual(report['manifest_artifacts_missing'], [])

    def test_broken_archive_preserved_and_error_not_hidden(self):
        path = self.mods / 'broken.ts4script'
        path.write_bytes(b'not a zip')
        report = inventory(self.mods)
        self.assertFalse(report['complete'])
        self.assertTrue(report['errors'])
        self.assertEqual(report['files'][0]['action'], 'preserve_unreadable_file')
        self.assertEqual(path.read_bytes(), b'not a zip')

    def test_cli_writes_only_new_output_outside_protected_paths(self):
        self.archive('harmless.ts4script', ['third_party.pyc'])
        output = self.root / 'inventory.json'
        self.assertEqual(main([str(self.mods), '--output', str(output)]), 0)
        report = json.loads(output.read_text())
        self.assertTrue(report['read_only'])
        with self.assertRaises(FileExistsError):
            write_report(report, output)


if __name__ == '__main__':
    unittest.main()
