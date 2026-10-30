"""MHS M24 read-only PickedSim diagnostic; Sims 4 / Python 3.7.

No file I/O, no registration, no persistent roster, no school changes.
Replaces ONLY the confirmation classes in a separately named test package.
"""
from interactions import ParticipantType
from interactions.base.immediate_interaction import ImmediateSuperInteraction
import sims4.commands

_SESSION = []
_MAX_EVENTS = 32


def _participant_id(participant):
    if participant is None:
        return "NONE"
    info = getattr(participant, "sim_info", None)
    if info is None:
        info = participant
    value = getattr(info, "sim_id", None)
    if value is None:
        value = getattr(info, "id", None)
    if isinstance(value, bool) or value is None:
        return "UNKNOWN"
    try:
        sid = int(value)
    except (ValueError, TypeError, OverflowError):
        return "UNKNOWN"
    return str(sid) if sid > 0 else "UNKNOWN"


def probe_event(class_number, interaction):
    """Record ONE confirmation invocation; do not assume full selection."""
    row = {"class": class_number, "ids": (), "error": None}
    try:
        picked = interaction.get_participants(ParticipantType.PickedSim)
        if picked is None:
            row["error"] = "PickedSim NONE"
        else:
            ids = tuple(sorted((_participant_id(x) for x in picked)))
            row["ids"] = ids
            if not ids:
                row["error"] = "PickedSim vuoto"
            elif any(x in ("UNKNOWN", "NONE") for x in ids):
                row["error"] = "Uno o piu ID non identificabili"
    except Exception as exc:
        # Never allow the diagnostic to stop the ordinary notification.
        row["error"] = "get_participants: " + type(exc).__name__
    _SESSION.append(row)
    if len(_SESSION) > _MAX_EVENTS:
        del _SESSION[:-_MAX_EVENTS]
    return row


class MHS24ProbeConfirmClass1(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        probe_event(1, self)
        # Preserve the normal confirmation notification via its original tuning.
        return super()._run_interaction_gen(timeline)


class MHS24ProbeConfirmClass2(ImmediateSuperInteraction):
    def _run_interaction_gen(self, timeline):
        probe_event(2, self)
        return super()._run_interaction_gen(timeline)


@sims4.commands.Command("mhs24.report", command_type=sims4.commands.CommandType.Live)
def mhs24_report(_connection=None):
    out = sims4.commands.CheatOutput(_connection)
    out("MHS24 DIAGNOSI - SOLO LETTURA | conferme osservate: {}".format(len(_SESSION)))
    if not _SESSION:
        out("Nessuna conferma registrata. Apri il picker e premi la spunta.")
    for n, item in enumerate(_SESSION[-16:], 1):
        out("#{} classe {} | ID PickedSim: {} | errore: {}".format(
            n, item["class"], ",".join(item["ids"]) or "(nessuno)",
            item["error"] or "(nessuno)"))
    out("Non sono state salvate iscrizioni o modificati Sim.")


@sims4.commands.Command("mhs24.clear", command_type=sims4.commands.CommandType.Live)
def mhs24_clear(_connection=None):
    del _SESSION[:]
    sims4.commands.CheatOutput(_connection)("MHS24: risultati in memoria azzerati.")
