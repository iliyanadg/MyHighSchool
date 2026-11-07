"""Build one deduplicated Classroom Control pair from the M54/M148 sources.

This packages the existing EA integration; successful compilation is not an
in-game attendance or third-party compatibility certification.
"""
import ast
import hashlib
import importlib.util
import json
import marshal
import os
from pathlib import Path
import py_compile
import struct
import subprocess
import sys
import tempfile
import types
import xml.etree.ElementTree as ET
import zipfile
import zlib

from tooling.build_m54_human_only_staff import SCRIPTS as MENU_SOURCES
from tooling.build_m53_staff_management import package_bytes as baseline_package_bytes
from tooling.build_mhs148_verified import SOURCES as ATTENDANCE_SOURCES
from tooling.simdata_release_gate import inspect_bytes, resources
from tooling.build_m27_removal import TYPE_INTERACTION, TYPE_SNIPPET, TYPE_STBL, ENTRY
from tooling.build_m30_nested_menu import CATEGORY_IDS
from tooling.build_m41_complete_menu import CATEGORY_TYPE, SIMDATA_TYPE, SIMDATA_GROUP
from tooling.build_m55_attendance_trial import _interaction as immediate_template
from tooling import build_mhs98_roles as roles_menu

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'MHS_CLASSROOM_CONTROL.package'
SCRIPT = 'MHS_CLASSROOM_CONTROL.ts4script'
REPORT = 'CLASSROOM_CONTROL_BUILD_REPORT.json'
BUNDLE = 'MHS_CLASSROOM_CONTROL.zip'
MAGIC = bytes((66, 13, 13, 10))
# New integrated modules belong here; old controllers do not.
EXTRA_SOURCES = tuple(ROOT / path for path in (
    'src/m98_in_game_roles/mhs98_core_role_ui.py',
    'src/classroom_control/mhs_school_session.py',
    'src/classroom_control/mhs_attendance_policy.py',
    'src/classroom_control/mhs_classroom_bootstrap.py',
    'src/classroom_control/mhs_scoped_classroom.py',
    'src/classroom_control/mhs_queue_readback.py',
    'src/classroom_control/mhs_school_readback.py',
    'src/m148_clock/mhs149_lesson_audit.py',
    'src/m148_clock/mhs150_early_preparation.py',
    'src/classroom_control/mhs150_day_continuity.py',
    'src/classroom_control/mhs151_npc_school_priority.py',
    'src/classroom_control/mhs151_npc_football_bridge.py',
    'src/classroom_control/mhs152_staff_scan_policy.py',
    'src/classroom_control/mhs_native_staff_appointments.py',
    'src/classroom_control/mhs_additional_native_staff.py',
    'src/classroom_control/mhs_native_schedule_staff.py',
    'src/classroom_control/mhs_save_as_copy.py',
))
SOURCES = tuple(MENU_SOURCES) + tuple(ATTENDANCE_SOURCES) + EXTRA_SOURCES
EA_MODULES = frozenset((
    'alarms', 'clock', 'date_and_time', 'event_testing', 'filters',
    'interactions', 'services', 'sims', 'sims4', 'situations', 'ui', 'venues', 'zone',
))
STANDARD_MODULES = frozenset((
    'ast', 'collections', 'contextlib', 'copy', 'datetime', 'enum', 'functools',
    'hashlib', 'importlib', 'inspect', 'itertools', 'json', 'logging', 'marshal',
    'math', 'os', 'pathlib', 're', 'struct', 'sys', 'tempfile', 'threading',
    'time', 'traceback', 'types', 'typing', 'weakref', 'zipfile', 'zlib',
))


class BuildError(ValueError):
    pass


def package_resources():
    """Add M98 role management to M54, without the old M55 trial action."""
    original = resources(baseline_package_bytes())
    if len(original) != 62:
        raise BuildError('Expected M54 menu with 62 resources')
    category = next(raw for typ, _, iid, raw in original
                    if typ == CATEGORY_TYPE and iid == CATEGORY_IDS[0])
    simdata = next(raw for typ, group, iid, raw in original
                   if typ == SIMDATA_TYPE and group == SIMDATA_GROUP
                   and iid == CATEGORY_IDS[0])
    action = next(raw for typ, _, _, raw in original
                  if typ == TYPE_INTERACTION and
                  ET.fromstring(raw).get('c') == 'MHS39_MHS27RemoveClass1')
    # This is only an in-memory immediate-action template. Never include
    # MHS55TryOne, M55 controllers or the M55 menu entry in the package.
    action = immediate_template(action)
    output = []
    changed = []
    for typ, group, iid, raw in original:
        before = raw
        if typ == TYPE_SNIPPET:
            raw = roles_menu._inject(raw)
        elif typ == TYPE_STBL:
            locale = {0: 'en', 11: 'it'}.get(iid >> 56)
            if locale is None:
                raise BuildError('Unknown M54 language')
            raw = roles_menu._stbl(raw, locale)
        if raw != before:
            changed.append((typ, group, iid))
        output.append((typ, group, iid, raw))
    output.extend((
        (CATEGORY_TYPE, 0, roles_menu.CAT_ID, roles_menu._category(category)),
        (SIMDATA_TYPE, SIMDATA_GROUP, roles_menu.CAT_ID, roles_menu._simdata(simdata)),
    ))
    output.extend((TYPE_INTERACTION, 0, roles_menu.ACTION_IDS[index],
                   roles_menu._interaction(action, index))
                  for index in range(len(roles_menu.ACTIONS)))
    if len(changed) != 3 or len(output) != 75 or len({r[:3] for r in output}) != 75:
        raise BuildError('Only additive role menu changes are permitted')
    for before, after in zip(original, output):
        if before[:3] != after[:3] or (before[0] not in (TYPE_STBL, TYPE_SNIPPET)
                                     and before != after):
            raise BuildError('Unexpected change to existing M54 resources')
    return output


def package_bytes():
    original = baseline_package_bytes()
    entries = package_resources()
    header = bytearray(original[:96])
    payload = bytearray()
    index = bytearray(struct.pack('<I', 0))
    for typ, group, iid, raw in entries:
        compressed = zlib.compress(raw, 9)
        index.extend(ENTRY.pack(typ, group, iid >> 32, iid & 0xffffffff,
                     96 + len(payload), len(compressed) | 0x80000000,
                     len(raw), 0x5A42, 1))
        payload.extend(compressed)
    struct.pack_into('<I', header, 0x24, len(entries))
    struct.pack_into('<I', header, 0x2c, len(index))
    struct.pack_into('<Q', header, 0x40, 96 + len(payload))
    blob = bytes(header + payload + index)
    if resources(blob) != entries:
        raise BuildError('Package resource round-trip failed')
    return blob


def source_inventory(sources=SOURCES):
    """Deduplicate by Python import name, rejecting divergent definitions."""
    inventory = {}
    for raw in sources:
        source = Path(raw)
        if not source.is_file() or source.suffix != '.py':
            raise BuildError('Missing Python source: {}'.format(source))
        name = source.stem
        body = source.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        existing = inventory.get(name)
        if existing is not None and existing['sha256'] != digest:
            raise BuildError('Divergent module definitions: {}'.format(name))
        if existing is None:
            existing = {'path': source, 'sha256': digest, 'provenance': []}
            inventory[name] = existing
        try:
            origin = source.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            origin = str(source.resolve())
        if origin not in existing['provenance']:
            existing['provenance'].append(origin)
    return inventory


def _catches_import_error(handler):
    node = handler.type
    if isinstance(node, ast.Name):
        return node.id == 'ImportError'
    return (isinstance(node, ast.Tuple) and any(
        isinstance(item, ast.Name) and item.id == 'ImportError'
        for item in node.elts))


def source_imports(source):
    """Record lazy imports separately from explicit ImportError fallbacks."""
    records = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.lazy = 0
            self.optional = 0

        def record(self, module, node):
            records.append({
                'module': module, 'root': module.split('.')[0],
                'line': node.lineno, 'optional': bool(self.optional),
                'phase': 'lazy' if self.lazy else 'module',
            })

        def visit_Import(self, node):
            for item in node.names:
                self.record(item.name, node)

        def visit_ImportFrom(self, node):
            if node.level:
                raise BuildError('Relative imports require a package manifest')
            if node.module:
                self.record(node.module, node)

        def visit_FunctionDef(self, node):
            # Defaults/decorators execute when the function is defined.
            for item in node.decorator_list + node.args.defaults:
                self.visit(item)
            self.lazy += 1
            for item in node.body:
                self.visit(item)
            self.lazy -= 1

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Try(self, node):
            fallback = any(_catches_import_error(h) for h in node.handlers)
            self.optional += int(fallback)
            for item in node.body:
                self.visit(item)
            self.optional -= int(fallback)
            for item in node.handlers + node.orelse + node.finalbody:
                self.visit(item)

    Visitor().visit(ast.parse(Path(source).read_text(encoding='utf-8')))
    return records


def dependency_inventory(inventory):
    result = {}
    for name, entry in sorted(inventory.items()):
        records = source_imports(entry['path'])
        for record in records:
            root = record['root']
            if root in inventory:
                record['kind'] = 'bundled'
            elif root.startswith('mhs'):
                if not record['optional']:
                    raise BuildError('Missing local dependency: {} -> {}'.format(
                        name, root))
                record['kind'] = 'optional_local_absent'
            elif root in STANDARD_MODULES:
                record['kind'] = 'python_standard_library'
            elif root in EA_MODULES:
                record['kind'] = 'the_sims_4_runtime'
            else:
                raise BuildError('Unclassified dependency: {} -> {}'.format(
                    name, root))
        result[name] = records
    return result


def tuning_dependencies(entries, inventory):
    modules = {}
    for typ, group, iid, raw in entries:
        if typ not in (CATEGORY_TYPE, TYPE_INTERACTION, TYPE_SNIPPET):
            continue
        module = ET.fromstring(raw).get('m')
        if not module:
            continue
        root = module.split('.')[0]
        if root in inventory:
            modules[module] = 'bundled'
        elif root.startswith('mhs'):
            raise BuildError('Missing tuning dependency: ' + module)
        elif root in EA_MODULES:
            modules[module] = 'the_sims_4_runtime'
        elif root == 'xml_injector':
            modules[module] = 'required_external_xml_injector'
        else:
            raise BuildError('Unclassified tuning dependency: ' + module)
    return modules


def _archive_module(archive, name, body):
    info = zipfile.ZipInfo(name + '.pyc', date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, body, compress_type=zipfile.ZIP_DEFLATED,
                     compresslevel=9)


def verify_archive(path, inventory):
    with zipfile.ZipFile(str(path)) as archive:
        names = archive.namelist()
        expected = {name + '.pyc' for name in inventory}
        if len(names) != len(set(names)) or set(names) != expected:
            raise BuildError('Duplicate or incomplete module archive')
        if archive.testzip() is not None:
            raise BuildError('Invalid archive CRC')
        for name, source in inventory.items():
            raw = archive.read(name + '.pyc')
            if raw[:4] != MAGIC or struct.unpack('<I', raw[4:8])[0] != 0:
                raise BuildError('Incorrect Python 3.7 ZIP-loadable bytecode')
            body = source['path'].read_bytes()
            if raw[8:16] != struct.pack('<II', 0, len(body) & 0xffffffff):
                raise BuildError('Incorrect normalized bytecode timestamp/size: ' + name)
            code = marshal.loads(raw[16:])
            if not isinstance(code, types.CodeType) or code.co_filename != name + '.py':
                raise BuildError('Incorrect compiled module: ' + name)
            expected = compile(body, name + '.py', 'exec', dont_inherit=True, optimize=0)
            if code != expected:
                raise BuildError('Bytecode/source code mismatch: ' + name)


def installation_bundle(folder):
    """Distribute our build and public instructions; never user/EA attachments."""
    folder=Path(folder)
    payload={name:(folder/name).read_bytes() for name in (
        PACKAGE,SCRIPT,REPORT,'SHA256SUMS.txt','LEGGIMI_CLASSROOM_CONTROL.txt')}
    for source in ('docs/INSTALLAZIONE_PULITA_MAC.md','docs/PRIMO_COLLAUDO_CLASSROOM_CONTROL.md',
                   'docs/EA_CONTRATTI_CLASSROOM_CONTROL.md',
                   'docs/VERIFICHE_CLASSROOM_CONTROL.md',
                   'docs/SECONDA_GIORNATA_DIAGNOSTICA.md',
                   'docs/COLLAUDO_PERSONALE_BETA.md',
                   'docs/COLLAUDO_PERSONALE_MULTIPLO_BETA.md',
                   'docs/SALVA_CON_NOME_IMPORTAZIONE_SICURA.md',
                   'docs/FIX_PARTITA15_CLASSI_PERSONALE.md',
                   'tooling/mod_inventory.py'):
        path=ROOT/source
        payload[path.name]=path.read_bytes()
    target=folder/BUNDLE
    temporary=folder/(BUNDLE+'.tmp')
    with zipfile.ZipFile(str(temporary),'w') as archive:
        for name,body in sorted(payload.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.create_system=3
            info.external_attr=0o100644<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,body,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(str(temporary)) as archive:
        if archive.testzip() is not None or set(archive.namelist())!=set(payload):
            raise BuildError('Invalid installation bundle')
    os.replace(str(temporary),str(target))
    return target


def build(folder, sources=SOURCES):
    if sys.version_info[:2] != (3, 7) or importlib.util.MAGIC_NUMBER != MAGIC:
        raise BuildError('The Sims 4 build requires CPython 3.7 (420d0d0a)')
    inventory = source_inventory(sources)
    dependencies = dependency_inventory(inventory)
    blob = package_bytes()
    tuning_modules = tuning_dependencies(resources(blob), inventory)
    gate = inspect_bytes(blob)
    if (gate['status'] != 'STATIC_GATE_PASSED' or gate['resource_count'] != 75
            or gate['category_count'] != 11 or gate['simdata_count'] != 11):
        raise BuildError('M54 menu resource regression')
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(out), prefix='.mhs-build-') as temporary:
        temporary = Path(temporary)
        script = temporary / SCRIPT
        # CPython 3.7 marshal output can change after code objects have been
        # loaded in the build process (string interning). Compile in a fresh,
        # fixed-hash-seed interpreter so verification/tests cannot perturb it.
        compiler = '''import json, py_compile, sys
for source, destination, filename in json.loads(sys.stdin.read()):
    py_compile.compile(source, cfile=destination, dfile=filename, doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
'''
        jobs = [[str(entry['path']), str(temporary / (name + '.pyc')), name + '.py']
                for name, entry in sorted(inventory.items())]
        subprocess.run([sys.executable, '-S', '-c', compiler],
            input=json.dumps(jobs).encode('utf-8'), check=True,
            env=dict(os.environ, PYTHONHASHSEED='0', PYTHONOPTIMIZE='0'))
        with zipfile.ZipFile(str(script), 'w') as archive:
            for name, entry in sorted(inventory.items()):
                compiled = temporary / (name + '.pyc')
                raw = compiled.read_bytes()
                # CPython 3.7 zipimport cannot load PEP 552 hash-based .pyc.
                # There is no .py in this archive, so timestamp 0 is valid;
                # source SHA256 is retained independently in the manifest.
                raw = raw[:8] + struct.pack('<II', 0,
                    len(entry['path'].read_bytes()) & 0xffffffff) + raw[16:]
                _archive_module(archive, name, raw)
        verify_archive(script, inventory)
        if any(hashlib.sha256(entry['path'].read_bytes()).hexdigest() != entry['sha256']
               for entry in inventory.values()):
            raise BuildError('Source changed during build; retry after edits are complete')
        package = temporary / PACKAGE
        package.write_bytes(blob)
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (package, script)}
        report = {
            'status': 'OFFLINE_BUILD_VERIFIED_GAME_VALIDATION_REQUIRED',
            'python': sys.version.split()[0], 'magic': MAGIC.hex(),
            'bytecode_format': 'timestamp_normalized_for_python37_zipimport',
            'module_count': len(inventory), 'unique_controller': 'mhs145_classroom_controller',
            'm54_actions_preserved': True, 'manual_core_role_menu': True,
            'diagnostic_revision': 'SECOND_DAY_READ_ONLY_OBSERVATIONS',
            'staff_selection_bridge_implemented': 'EXPERIMENTAL_NATIVE_EXACT_GUESTS',
            'staff_multi_worker_supported': 'TWO_CUSTODIANS_BETA',
            'staff_two_custodians_in_game_verified': False,
            'staff_multiple_cafeteria_workers_supported': False,
            'staff_cafeteria_primary_fallback_supported': True,
            'supplemental_school_staff_native_situation_beta': True,
            'supplemental_staff_real_job_requires_game_test': True,
            'staff_cafeteria_policy': 'FIRST_REGISTERED_NATIVE_VENDOR_ONLY_EXTRAS_PENDING',
            'staff_actual_ea_job_verified_in_game': False,
            'day_rollover_owner_preserved_in_code': True,
            'school_arrival_watcher_rearmed_in_code': True,
            'native_lunch_test_scope': 'VANILLA_EA_TESTS_12_00_TO_13_24',
            'npc_lunch_behavior_in_game_verified': False,
            'resources': gate['resource_count'],
            'category_simdata_pairs': gate['category_count'],
            'sha256': hashes,
            'files': [
                {'name': PACKAGE, 'sha256': hashes[PACKAGE], 'modules': []},
                {'name': SCRIPT, 'sha256': hashes[SCRIPT],
                 'modules': sorted(inventory)},
            ],
            'modules': {name: {'sha256': entry['sha256'],
                       'sources': entry['provenance'], 'imports': dependencies[name]}
                        for name, entry in sorted(inventory.items())},
            'dependency_check': 'static imports; EA APIs require the running game',
            'tuning_modules': tuning_modules,
            'in_game_verified': False, 'mac_verified': False,
            'windows_verified': False, 'third_party_compatibility_verified': False,
        }
        # Publish only after all sources, resources and bytecode have passed.
        for p in (package, script):
            os.replace(str(p), str(out / p.name))
    (out / REPORT).write_text(json.dumps(report, indent=2, sort_keys=True),
                              encoding='utf-8')
    (out / 'SHA256SUMS.txt').write_text(''.join('{}  {}\n'.format(value, name)
        for name, value in sorted(hashes.items())), encoding='utf-8')
    (out / 'LEGGIMI_CLASSROOM_CONTROL.txt').write_text(
        'MY HIGH SCHOOL — Classroom Control\n'
        'Una sola coppia: MHS_CLASSROOM_CONTROL.package e MHS_CLASSROOM_CONTROL.ts4script.\n'
        'Include menu/registro/personale M54 e un solo controller derivato da M148.\n'
        'Beta: gli inviti esatti del personale sono collegati ai job EA nativi.\n'
        'L ingresso effettivo nel job deve ancora essere verificato nel gioco.\n'
        'Uno o due bidelli: inviti esatti per lo stesso job EA, in beta da collaudare.\n'
        'Con 2-3 addetti mensa scelti: solo il PRIMO resta al banco EA come lavoratore primario fisso; gli altri sono in attesa.\n'
        'Addetti extra in beta: richiedono un banco mensa scolastico per ciascuno.\n'
        'Secondo bidello e addetti extra usano situazioni EA separate, solo se verificate.\n'
        'Presenza e vero lavoro restano DA CONFERMARE nel gioco, mai dedotti da invito.\n'
        'Per la prova usa una copia del salvataggio e leggi COLLAUDO_PERSONALE_BETA.md.\n'
        'Nuova giornata: controller conservato e monitor arrivo riarmato (da collaudare).\n'
        'Durante il pranzo i test lavagna tornano agli originali EA; nessuno spostamento forzato.\n'
        'Addetto mensa al banco e pranzo studenti NON sono ancora verificati nel gioco.\n'
        'Conservare integralmente saves e MY_HIGH_SCHOOL_M25_TEST_DATA.\n'
        'Prima di installare, inventariare e spostare le vecchie versioni MHS fuori Mods.\n'
        'Non rimuovere automaticamente altre mod o XML Injector.\n'
        'La compilazione e i controlli offline non certificano 8/8 in aula,\n'
        'completamento delle lezioni o compatibilita con mod terze.\n'
        'Consultare la documentazione di installazione e il rapporto di audit.\n',
        encoding='utf-8')
    installation_bundle(out)
    return report


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m tooling.build_classroom_control OUTDIR')
    result = build(sys.argv[1])
    print(json.dumps({key: result[key] for key in (
        'status', 'python', 'module_count', 'sha256', 'in_game_verified')}, indent=2))
