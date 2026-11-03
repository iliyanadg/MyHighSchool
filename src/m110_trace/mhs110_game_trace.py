"""M110 opt-in native EA callback trace, Python 3.7 Sims console commands.

Manual mhs110.start BEFORE the EA school schedule. Manual mhs110.stop
restores wrappers and writes a capped, no-SimID JSON. Unlike M109, M110
TEMPORARILY wraps methods in memory (pass-through, no roster changes).
Use only on a backup test save, never alongside other MHS school controllers.
"""
import importlib
import json
import os
import sims4.commands
from mhs110_call_trace_core import M110Trace

TRACER = M110Trace()
REPORT = 'MHS_M110_NATIVE_EA_CALL_TRACE.json'
CLASS_MODULES = {
    'weekly_day': ('venues.weekly_schedule_zone_director', 'WeeklyScheduleDay'),
    'weekly_data': ('venues.weekly_schedule_zone_director', 'WeeklyScheduleSituationData'),
    'situation_manager': ('situations.situation_manager', 'SituationManager'),
}


def _classes():
    return {key: getattr(importlib.import_module(path), name, None)
            for key, (path, name) in CLASS_MODULES.items()}


def _save():
    directory = os.path.join(
        os.path.expanduser('~'), 'Documents', 'Electronic Arts',
        'The Sims 4', 'MY_HIGH_SCHOOL_M25_TEST_DATA')
    os.makedirs(directory, exist_ok=True)
    filename = os.path.join(directory, REPORT)
    temp = filename + '.tmp'
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(TRACER.report(), f, indent=2, sort_keys=True)
    os.replace(temp, filename)
    return filename


@sims4.commands.Command('mhs110.start', command_type=sims4.commands.CommandType.Live)
def _start(_connection=None):
    try:
        ok = TRACER.start(_classes())
        message = ('M110 tracing ON: 3 metodi EA osservati senza cambiare '
                   'risultati, usa mhs110.stop dopo scuola.' if ok else
                   'M110 NON attivata: owner o hook incompatibile. ')
    except Exception as exc:
        # Never claim the runtime is unmodified on an unknown exception.
        message = 'M110 ERRORE avvio: ' + type(exc).__name__
    sims4.commands.output(message, _connection)


@sims4.commands.Command('mhs110.stop', command_type=sims4.commands.CommandType.Live)
def _stop(_connection=None):
    try:
        restored = TRACER.stop()
        report_path = _save()
        message = ('M110 STOP: metodi originali ripristinati. ' if restored else
                   'M110 ATTENZIONE: ripristino non confermato. ') + REPORT
    except Exception as exc:
        message = 'M110 ERRORE stop: ' + type(exc).__name__
    sims4.commands.output(message, _connection)


@sims4.commands.Command('mhs110.status', command_type=sims4.commands.CommandType.Live)
def _status(_connection=None):
    try:
        data = TRACER.report()
        sims4.commands.output(
            'M110: {} eventi, {} conservati; stato {}.'.format(
                data['event_total'], data['events_kept'], data['status']),
            _connection)
    except Exception as exc:
        sims4.commands.output('M110 status error: ' + type(exc).__name__,
                              _connection)
