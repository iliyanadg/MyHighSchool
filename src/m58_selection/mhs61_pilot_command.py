"""M61 one-student opt-in pilot via Sims 4 command console.

No automatic invitation. Command is explicit: mhs61.pilot
Operates only after verifying the saved roster and EA school situations.
Records at most ONE attempted invitation for a live zone/day, no retries.
"""
import services
from sims.sim_info_types import Age, Species
from mhs_m2_game_bridge import current_slot
from mhs_m2_store import RosterStore
from mhs34_settings import SettingsStore
from mhs55_attendance_core import (
    valid_student, school_running, already_in_base_student)
from mhs61_guest_adapter import create_one_existing_student

import os
ROOT=os.path.join(os.path.expanduser('~'),'Documents','Electronic Arts',
                  'The Sims 4','MY_HIGH_SCHOOL_M25_TEST_DATA')
_ATTEMPTED=set()
_LAST='non eseguito'

def pilot():
    """Explicit trial with fail-closed checks. Returns diagnostic string."""
    global _LAST
    try:
        zone=services.current_zone()
        mgr=services.get_zone_situation_manager()
        sims=services.sim_info_manager()
        if zone is None or mgr is None or sims is None:
            return 'BLOCCATO: zona o gestore EA non pronto'
        slot=current_slot(allow_travel=True)
        settings=SettingsStore(ROOT).load(slot)
        if not settings.active:
            return 'BLOCCATO: gestione MY HIGH SCHOOL non attiva'
        if not school_running(mgr,sims.get_all(),Age.TEEN):
            return 'BLOCCATO: situazione scolastica EA non verificata'
        roster=RosterStore(ROOT).load(slot)
        from date_and_time import sim_ticks_per_day
        now=services.time_service().sim_now
        day=int(now.absolute_ticks())//int(sim_ticks_per_day())
        key=(str(slot),str(getattr(zone,'id',None)),day)
        if key in _ATTEMPTED:
            return 'BLOCCATO: prova gia eseguita in questa giornata'
        if not callable(getattr(mgr,'get_situations_sim_is_in',None)):
            return 'BLOCCATO: verifica duplicati EA assente'
        household=services.active_household()
        home=set(str(s.sim_id) for s in household.sim_info_gen()) if household else set()
        candidate=None
        for klass in range(1,settings.class_count+1):
            for sid in roster.class_members(klass):
                info=sims.get(int(sid))
                if str(sid) in home or not valid_student(info,Age.TEEN,Species.HUMAN):
                    continue
                if info.get_sim_instance() is not None:
                    continue
                candidate=info
                break
            if candidate is not None:
                break
        if candidate is None:
            return 'BLOCCATO: nessun adolescente idoneo da convocare'
        from sims4.resources import Types
        from situations.situation_guest_list import (
            SituationGuestList,SituationGuestInfo,SituationInvitationPurpose)
        sit=services.get_instance_manager(Types.SITUATION).get(277733)
        job=services.get_instance_manager(Types.SITUATION_JOB).get(277894)
        if sit is None or job is None:
            return 'BLOCCATO: tuning EA assente'
        # Mark BEFORE creating: never retry a failed or delayed EA request.
        _ATTEMPTED.add(key)
        result=create_one_existing_student(
            mgr,sit,job,candidate.sim_id,
            SituationGuestList,SituationGuestInfo,
            SituationInvitationPurpose.INVITED)
        _LAST='Richiesta EA emessa, non presenza confermata: {}'.format(bool(result))
        return _LAST
    except Exception as exc:
        _LAST='ERRORE '+type(exc).__name__
        return _LAST

def last_status():
    return _LAST

def install_command():
    try:
        import sims4.commands
        @sims4.commands.Command('mhs61.pilot',
                                command_type=sims4.commands.CommandType.Live)
        def _command(_connection=None):
            sims4.commands.output(pilot(),_connection)
        return True
    except Exception:
        return False

install_command()
