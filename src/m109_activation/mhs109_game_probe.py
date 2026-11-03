"""M109 LIVE diagnostics only: no EA gameplay mutations and no M108 hooks.

A single opt-in Sims 4 console command, mhs109.probe, captures the actual
loaded EA Python class descriptors. It never installs, changes, or removes
situations, Sims, traits, jobs, Bouncer filters, tuning or school schedule.

It runs only when the user invokes the command and writes a JSON file in
The Sims 4 MY_HIGH_SCHOOL_M25_TEST_DATA folder, without sensitive Sim IDs.
If a module name or EA API differs in the installed game, the report
describes the missing source rather than guessing success.

This is a diagnostic, not an M109 classroom controller.
"""
import importlib
import json
import os

import sims4.commands
from mhs109_readonly_ea_probe import inspect_runtime_shapes

REPORT_NAME = 'MHS_M109_NATIVE_METHODS_READ_ONLY.json'
MODULES = {
    'weekly_day': (
        'venues.weekly_schedule_zone_director', 'WeeklyScheduleDay'),
    'weekly_data': (
        'venues.weekly_schedule_zone_director',
        'WeeklyScheduleSituationData'),
    'situation_manager': (
        'situations.situation_manager', 'SituationManager'),
    'bouncer_request': (
        'situations.bouncer.bouncer_request', 'BouncerRequest'),
    'bouncer': (
        'situations.bouncer.bouncer', 'Bouncer'),
    'base_situation': (
        'situations.base_situation', 'BaseSituation'),
}


def _report_folder():
    return os.path.join(
        os.path.expanduser('~'), 'Documents', 'Electronic Arts',
        'The Sims 4', 'MY_HIGH_SCHOOL_M25_TEST_DATA')


def capture_native_shapes():
    """Import and inspect only; nothing is monkey-patched or instantiated."""
    classes = {}
    imports = {}
    for key, (path, class_name) in MODULES.items():
        try:
            module = importlib.import_module(path)
            cls = getattr(module, class_name, None)
            if not isinstance(cls, type):
                imports[key] = 'EA_CLASS_MISSING'
            else:
                classes[key] = cls
                imports[key] = 'EA_CLASS_LOADED'
        except Exception as exc:
            # Do not dump stack traces or private paths into diagnostics.
            imports[key] = 'IMPORT_' + type(exc).__name__
    report = inspect_runtime_shapes(classes)
    report['native_modules'] = imports
    report['source'] = 'LOADED_GAME_MODULES_READ_ONLY'
    report['activation_authorized_by_game'] = False
    # Absence of markers in these 15 methods is NOT proof that no old or
    # third-party controller is installed elsewhere in the game.
    marker_count = len(report['known_mhs_hook_markers_found'])
    report['known_mhs_hook_marker_count'] = marker_count
    report['known_mhs_hook_scan'] = (
        'KNOWN_MHS_MARKERS_DETECTED'
        if marker_count else 'NO_KNOWN_MARKERS_OTHER_HOOKS_UNVERIFIED')
    report['mhs108_school_hooks_installed'] = None
    report['full_16_student_attendance_verified'] = False
    report['game_modified'] = False
    return report


def save_native_report(report, folder=None):
    folder = _report_folder() if folder is None else folder
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, REPORT_NAME)
    temp_path = path + '.tmp'
    with open(temp_path, 'w', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
    os.replace(temp_path, path)
    return path


@sims4.commands.Command('mhs109.probe',
                        command_type=sims4.commands.CommandType.Live)
def _m109_probe_command(_connection=None):
    try:
        report = capture_native_shapes()
        save_native_report(report)
        message = ('M109 SOLA LETTURA: {}/{} metodi EA; '
                   '{}/{} punti di aggancio individuati (non validati); '
                   '{} marker MHS rilevati; rapporto {}. '
                   'Nessun Sim modificato.').format(
                       report['method_count_available'],
                       report['method_count_expected'],
                       report['hook_target_count_located_unverified'],
                       report['hook_target_count_expected'],
                       report['known_mhs_hook_marker_count'],
                       REPORT_NAME)
    except Exception as exc:
        message = ('M109 diagnostica non eseguita: {}. '
                   'Nessuna modifica al gioco.').format(type(exc).__name__)
    sims4.commands.output(message, _connection)
