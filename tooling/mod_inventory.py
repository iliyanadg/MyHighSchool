"""Inventory Sims 4 Mods without changing mods, saves or persistent data.

ZIP members are listed, never extracted or executed. File names are hints,
not proof of ownership. Only a supplied release manifest's SHA-256 can verify
an artifact; MHS module signatures identify older archive families for review.
Compatible with Python 3.7 and later; uses only the standard library.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import zipfile


DATA_DIRECTORY = 'MY_HIGH_SCHOOL_M25_TEST_DATA'
NEW_FILES = ('MHS_CLASSROOM_CONTROL.package',
             'MHS_CLASSROOM_CONTROL.ts4script')
FAMILIES = (
    ('M148', ('mhs148_clock_and_sampling', 'mhs148_day_trace')),
    ('M147', ('mhs147_class_timing_policy',)),
    ('M145-M146', ('mhs145_classroom_controller',
                   'mhs145_subject_picker_patch', 'mhs146_class_timing_policy')),
    ('M140-M143', ('mhs140_classroom_controller', 'mhs141_classroom_controller',
                   'mhs142_classroom_controller', 'mhs143_classroom_controller')),
    ('M128-M139', ('mhs128_classroom_controller', 'mhs130_classroom_controller',
                   'mhs131_classroom_controller', 'mhs132_classroom_controller',
                   'mhs134_classroom_controller', 'mhs136_classroom_controller',
                   'mhs137_classroom_controller', 'mhs138_classroom_controller',
                   'mhs139_classroom_controller')),
    ('M119-M127', ('mhs119_one_base_live_trial', 'mhs120_eight_base_live_trial',
                   'mhs121_thirteen_npc_trial', 'mhs122_thirteen_npc_plus_classes',
                   'mhs123_thirteen_npc_class_trial',
                   'mhs124_thirteen_npc_plus_behavior',
                   'mhs125_thirteen_npc_plus_recovery',
                   'mhs126_early_school_controller', 'mhs127_timed_school_controller')),
    ('M105-M118', ('mhs105_game_controller', 'mhs106_game_controller',
                   'mhs109_game_probe', 'mhs110_game_trace',
                   'mhs111_game_probe', 'mhs118_admission_before_lessons')),
    ('M55-M104', ('mhs55_attendance_auto', 'mhs57_filter_runtime',
                  'mhs58_situation_probe', 'mhs61_pilot_command',
                  'mhs98_core_role_ui', 'mhs101_original_slot_runtime')),
    ('M53-M54 menu/personale (versione esatta non determinabile dai nomi)',
     ('mhs53_staff_ui', 'mhs53_staff_store')),
    ('MHS registro/menu precedente', ('mhs_m2_roster', 'mhs39_visibility_ui')),
)


def _within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _module_name(member):
    # Interpret ZIP paths only. No archive member ever becomes a local path.
    path = PurePosixPath(member)
    if path.is_absolute() or '..' in path.parts or '\\' in member:
        return None
    if path.suffix not in ('.py', '.pyc'):
        return None
    parts = list(path.parts)
    leaf = path.stem.split('.cpython-', 1)[0]
    if len(parts) > 1 and parts[-2] == '__pycache__':
        parts.pop(-2)
    parts[-1] = leaf
    if leaf == '__init__':
        parts.pop()
    if not parts or not all(part.isidentifier() for part in parts):
        return None
    return '.'.join(parts)


def _archive_inventory(path):
    with zipfile.ZipFile(str(path)) as archive:
        members = archive.namelist()
        if len(members) > 100000:
            raise ValueError('Archive has over 100000 members')
        modules = {}
        for name in members:
            module = _module_name(name)
            if module:
                modules.setdefault(module, []).append(name)
        return {
            'members': members,
            'modules': sorted(modules),
            'duplicate_module_members': {
                module: names for module, names in sorted(modules.items())
                if len(names) > 1},
        }


def _manifest_artifacts(manifest):
    """Accept documented files/artifacts list or name-to-metadata mapping."""
    if manifest is None:
        return []
    if not isinstance(manifest, dict):
        raise ValueError('Manifest must be a JSON object')
    rows = manifest.get('files', manifest.get('artifacts', []))
    if isinstance(rows, dict):
        rows = [dict(value, name=name) if isinstance(value, dict)
                else {'name': name, 'sha256': value}
                for name, value in rows.items()]
    if not isinstance(rows, list):
        raise ValueError('Manifest files/artifacts must be a list or mapping')
    results = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Each manifest artifact must be an object')
        name = row.get('name', row.get('path'))
        digest = row.get('sha256')
        if (not isinstance(name, str) or not name
                or not isinstance(digest, str) or len(digest) != 64
                or any(char not in '0123456789abcdefABCDEF' for char in digest)):
            raise ValueError('Each manifest artifact needs name and SHA-256')
        results.append({'name': name, 'sha256': digest.lower(),
                        'modules': row.get('modules')})
    return results


def _walk_files(root, skipped, errors):
    def failed(exc):
        errors.append({'path': str(exc.filename), 'error': str(exc)})
    for folder, dirs, names in os.walk(str(root), followlinks=False,
                                       onerror=failed):
        parent = Path(folder)
        # Skip every symlink, including links staying inside the root. This
        # makes the read boundary predictable and avoids alias collisions.
        for name in list(dirs):
            path = parent / name
            if path.is_symlink():
                dirs.remove(name)
                skipped.append({'path': str(path), 'reason': 'symlink_not_followed'})
        dirs.sort()
        for name in sorted(names):
            path = parent / name
            if path.is_symlink():
                skipped.append({'path': str(path), 'reason': 'symlink_not_followed'})
            elif not path.is_file():
                skipped.append({'path': str(path), 'reason': 'not_a_regular_file'})
            elif not _within(path.resolve(), root):
                skipped.append({'path': str(path), 'reason': 'outside_scan_root'})
            else:
                yield path


def _is_save(name):
    return name.lower().endswith('.save') or '.save.ver' in name.lower()


def inventory(mods_directory, data_directory=None, manifest=None):
    mods_input = Path(mods_directory).expanduser()
    if mods_input.is_symlink():
        raise ValueError('Mods root must be a real directory, not a symlink')
    mods = mods_input.resolve()
    if not mods.is_dir():
        raise ValueError('Mods directory does not exist: ' + str(mods))
    data_input = (Path(data_directory).expanduser() if data_directory is not None
                  else mods.parent / DATA_DIRECTORY)
    artifacts = _manifest_artifacts(manifest)
    report = {
        'format_version': 1, 'read_only': True,
        'mods_directory': str(mods), 'data_directory': str(data_input.absolute()),
        'files': [], 'module_collisions': [], 'skipped': [], 'errors': [],
        'protected_directories': [str(mods.parent / 'saves'), str(data_input.absolute())],
        'expected_release_files': list(NEW_FILES),
        'manifest_supplied': manifest is not None,
        'manifest_artifacts_missing': [],
        'limitations': [
            'No files were removed, moved, extracted or executed.',
            'MHS family signatures do not prove an exact release or ownership.',
            'Unknown packages and third-party mods must be preserved.',
            'This inventory does not validate behavior or compatibility in game.'],
    }
    roots = [('mods', mods)]
    if data_input.is_symlink():
        report['skipped'].append({'path': str(data_input), 'reason': 'symlink_not_followed'})
    elif data_input.exists():
        if not data_input.is_dir():
            report['errors'].append({'path': str(data_input), 'error': 'Data path is not a directory'})
        elif _within(data_input.resolve(), mods) or _within(mods, data_input.resolve()):
            raise ValueError('Mods and persistent data roots must not overlap')
        else:
            roots.append(('persistent_data', data_input.resolve()))
    module_owners = {}
    matched = set()
    for section, root in roots:
        for path in _walk_files(root, report['skipped'], report['errors']):
            row = {'path': str(path), 'relative_path': path.relative_to(root).as_posix(),
                   'section': section, 'ownership': 'unknown',
                   'action': 'preserve_unknown_file'}
            try:
                row.update(size=path.stat().st_size, sha256=_sha256(path))
                if section == 'persistent_data':
                    row['action'] = 'preserve_all_persistent_data'
                elif _is_save(path.name):
                    row['action'] = 'preserve_save'
                else:
                    if path.suffix.lower() in ('.ts4script', '.zip'):
                        row['archive'] = _archive_inventory(path)
                        modules = row['archive']['modules']
                        for module in modules:
                            module_owners.setdefault(module, []).append(str(path))
                        for family, markers in FAMILIES:
                            evidence = sorted(set(modules).intersection(markers))
                            if evidence:
                                row.update(ownership='mhs_module_signature_candidate',
                                           family=family, family_evidence=evidence,
                                           action='review_mhs_archive_for_quarantine')
                                break
                        if row['ownership'] == 'unknown':
                            row['action'] = 'preserve_unknown_archive'
                    elif path.suffix.lower() == '.package':
                        row['action'] = 'preserve_unverified_package'
                    elif path.suffix.lower() == '.json':
                        row['action'] = 'preserve_data_file'
                    if 'mhs' in path.name.lower() or 'my_high_school' in path.name.lower():
                        row['filename_hint'] = 'MHS-like name, ownership not established'
                    verified = [item for item in artifacts if item['sha256'] == row['sha256']]
                    if verified:
                        row['ownership'] = 'verified_release_manifest_hash'
                        row['action'] = 'keep_verified_release_artifact'
                        row['manifest_matches'] = [item['name'] for item in verified]
                        for item in verified:
                            matched.add(item['name'])
                            if item['modules'] is not None:
                                actual = row.get('archive', {}).get('modules', [])
                                row['manifest_modules_match'] = sorted(actual) == sorted(item['modules'])
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                row['action'] = 'preserve_unreadable_file'
                row['error'] = str(exc)
                report['errors'].append({'path': str(path), 'error': str(exc)})
            report['files'].append(row)
    report['module_collisions'] = [
        {'module': module, 'archives': sorted(set(paths))}
        for module, paths in sorted(module_owners.items()) if len(set(paths)) > 1]
    report['manifest_artifacts_missing'] = [item['name'] for item in artifacts
                                              if item['name'] not in matched]
    report['complete'] = not report['errors'] and not report['skipped']
    return report


def write_report(report, output):
    destination = Path(output).expanduser().resolve()
    mods = Path(report['mods_directory']).resolve()
    protected = [mods] + [Path(path).resolve() for path in report['protected_directories']]
    if any(_within(destination, root) for root in protected) or _is_save(destination.name):
        raise ValueError('Report output must be outside Mods, saves and persistent data')
    # Refuse overwrite, including pre-existing symlinks or files.
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mods', type=Path, help='Actual Mods directory to inspect')
    parser.add_argument('--data-dir', type=Path, help='Defaults to sibling ' + DATA_DIRECTORY)
    parser.add_argument('--manifest', type=Path, help='Trusted new release SHA-256 manifest JSON')
    parser.add_argument('--output', type=Path, help='New JSON file outside Mods/data/saves; default stdout')
    args = parser.parse_args(argv)
    try:
        manifest = None
        if args.manifest is not None:
            manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        report = inventory(args.mods, args.data_dir, manifest)
        if args.output is None:
            json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write('\n')
        else:
            write_report(report, args.output)
        return 0 if report['complete'] else 1
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    sys.exit(main())
