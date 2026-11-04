"""One installable pair, source closure and real Sims 4 bytecode checks."""
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import zipfile

from tooling import build_classroom_control as builder


class SourceInventoryTests(unittest.TestCase):
    def test_xml_only_dependencies_cannot_be_silently_omitted(self):
        def row(module):
            return (builder.TYPE_INTERACTION,0,1,
                    ('<I m="'+module+'" />').encode('utf-8'))
        with self.assertRaisesRegex(builder.BuildError,'Missing tuning dependency'):
            builder.tuning_dependencies([row('mhs_missing_menu')],{})
        result=builder.tuning_dependencies([row('xml_injector.snippet'),
                                            row('interactions.pie_menu_category')],{})
        self.assertEqual(result['xml_injector.snippet'],'required_external_xml_injector')
        self.assertEqual(result['interactions.pie_menu_category'],'the_sims_4_runtime')

    def test_menu_and_attendance_sources_share_one_definition(self):
        inventory = builder.source_inventory()
        expected = {p.stem for p in builder.SOURCES}
        self.assertEqual(set(inventory), expected)
        self.assertGreaterEqual(len(inventory), 43)
        self.assertIn('mhs53_staff_ui', inventory)
        self.assertIn('mhs34_runtime_gate', inventory)
        self.assertIn('mhs148_clock_and_sampling', inventory)
        controllers = [name for name in inventory if name.endswith('classroom_controller')]
        self.assertEqual(controllers, ['mhs145_classroom_controller'])

    def test_divergent_flat_module_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'one').mkdir()
            (root / 'two').mkdir()
            first, second = root / 'one' / 'mhs_shared.py', root / 'two' / 'mhs_shared.py'
            first.write_text('VALUE = 1\n')
            second.write_text('VALUE = 2\n')
            with self.assertRaisesRegex(builder.BuildError, 'Divergent module'):
                builder.source_inventory((first, second))
            second.write_text(first.read_text())
            inventory = builder.source_inventory((first, second))
            self.assertEqual(len(inventory), 1)
            self.assertEqual(len(inventory['mhs_shared']['provenance']), 2)

    def test_missing_required_local_and_unknown_external_dependency_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'mhs_test.py'
            for body, message in (
                    ('import mhs_missing\n', 'Missing local dependency'),
                    ('import imaginary_third_party\n', 'Unclassified dependency')):
                source.write_text(body)
                with self.assertRaisesRegex(builder.BuildError, message):
                    builder.dependency_inventory(builder.source_inventory((source,)))

    def test_optional_and_lazy_imports_are_distinct(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'mhs_test.py'
            source.write_text('try:\n import mhs_optional\nexcept ImportError:\n pass\n'
                              'def later():\n import services\n')
            records = builder.dependency_inventory(
                builder.source_inventory((source,)))['mhs_test']
            optional = next(row for row in records if row['root'] == 'mhs_optional')
            lazy = next(row for row in records if row['root'] == 'services')
            self.assertTrue(optional['optional'])
            self.assertEqual(optional['kind'], 'optional_local_absent')
            self.assertEqual(lazy['phase'], 'lazy')
            self.assertFalse(lazy['optional'])
            self.assertEqual(lazy['kind'], 'the_sims_4_runtime')

    def test_all_bundled_imports_are_classified(self):
        dependencies = builder.dependency_inventory(builder.source_inventory())
        self.assertTrue(any(row['kind'] == 'the_sims_4_runtime'
            for rows in dependencies.values() for row in rows))
        self.assertFalse(any(row['kind'] == 'optional_local_absent'
            for rows in dependencies.values() for row in rows))
        guard = next(row for row in dependencies['mhs_m2_store']
                     if row['root'] == 'mhs34_runtime_gate')
        self.assertTrue(guard['optional'])
        self.assertEqual(guard['kind'], 'bundled')

    def test_wrong_compiler_cannot_publish_game_archive(self):
        if sys.version_info[:2] == (3, 7):
            self.skipTest('Actual supported build tested below')
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(builder.BuildError, 'CPython 3.7'):
                builder.build(temporary)
            self.assertEqual(list(Path(temporary).iterdir()), [])


@unittest.skipUnless(sys.version_info[:2] == (3, 7),
                     'Installable bytecode must be built and read with CPython 3.7')
class Python37ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temporary.name)
        cls.report = builder.build(cls.folder)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_zip_loadable_bytecode_and_unique_names_match_actual_sources(self):
        inventory = builder.source_inventory()
        builder.verify_archive(self.folder / builder.SCRIPT, inventory)
        with zipfile.ZipFile(str(self.folder / builder.SCRIPT)) as archive:
            self.assertEqual(len(archive.namelist()), len(inventory))
            self.assertIn('mhs53_staff_ui.pyc', archive.namelist())
            self.assertIn('mhs145_classroom_controller.pyc', archive.namelist())
            self.assertNotIn('mhs143_classroom_controller.pyc', archive.namelist())

    def test_real_python37_zipimport_loads_sourceless_runtime_modules(self):
        code = '''import sys
sys.path.insert(0, sys.argv[1])
import mhs_school_session, mhs_attendance_policy, mhs_classroom_bootstrap
import mhs_scoped_classroom, mhs_queue_readback
for module in (mhs_school_session, mhs_attendance_policy, mhs_classroom_bootstrap,
               mhs_scoped_classroom, mhs_queue_readback):
    assert '.ts4script/' in module.__file__, module.__file__
assert mhs_school_session.school_day_key('11',2160000)==('11',1)
'''
        with tempfile.TemporaryDirectory() as empty:
            result = subprocess.run([sys.executable, '-S', '-c', code,
                str(self.folder / builder.SCRIPT)], cwd=empty,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_package_menu_is_byte_identical_and_results_are_not_game_claims(self):
        self.assertEqual((self.folder / builder.PACKAGE).read_bytes(),
                         builder.package_bytes())
        self.assertFalse(self.report['in_game_verified'])
        self.assertFalse(self.report['third_party_compatibility_verified'])
        persisted = json.loads((self.folder / builder.REPORT).read_text())
        self.assertEqual(persisted, self.report)
        for name, digest in persisted['sha256'].items():
            self.assertEqual(hashlib.sha256((self.folder / name).read_bytes()).hexdigest(), digest)

    def test_two_builds_are_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as second:
            builder.build(second)
            for name in (builder.PACKAGE, builder.SCRIPT,builder.BUNDLE):
                self.assertEqual((self.folder / name).read_bytes(),
                                 (Path(second) / name).read_bytes())

    def test_download_bundle_has_instructions_and_no_ea_or_private_inputs(self):
        with zipfile.ZipFile(str(self.folder/builder.BUNDLE)) as archive:
            names=set(archive.namelist())
            self.assertIn(builder.PACKAGE,names)
            self.assertIn(builder.SCRIPT,names)
            self.assertIn('PRIMO_COLLAUDO_CLASSROOM_CONTROL.md',names)
            self.assertIn('INSTALLAZIONE_PULITA_MAC.md',names)
            self.assertNotIn('MHS-inventario.json',names)
            self.assertFalse(any(name.endswith('.pyc') for name in names))
            self.assertIsNone(archive.testzip())

    def test_changed_archive_module_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            corrupt = Path(temporary) / builder.SCRIPT
            with zipfile.ZipFile(str(self.folder / builder.SCRIPT)) as source:
                with zipfile.ZipFile(str(corrupt), 'w') as destination:
                    for name in source.namelist():
                        body = source.read(name)
                        if name == 'mhs_m2_roster.pyc':
                            body = b'WRNG' + body[4:]
                        destination.writestr(name, body)
            with self.assertRaisesRegex(builder.BuildError, 'Incorrect Python'):
                builder.verify_archive(corrupt, builder.source_inventory())


if __name__ == '__main__':
    unittest.main()
