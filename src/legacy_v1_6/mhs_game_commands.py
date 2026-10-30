"""MY HIGH SCHOOL v0.9 — school invite + experimental class routing.

Read-only diagnostics and persistent external JSON roster. This build adds only an explicitly confirmed invitation experiment.
Never use it in a valuable save. No game-save synchronization.
"""
import services
import sims4.commands
from sims.sim_info_types import Age

from mhs_registry import SchoolRoster, RosterError
from mhs_persistence import RosterStore, SaveDataError, current_slot
from mhs_situation_invite import check_invitation, InvitationCheckError, invite_once, TEST_SIM_ID, inspect_student_situations
from mhs_class_route import ClassRouteError, fetch_class1_trait, set_ae_class_trait, restore_trait_state

_store = RosterStore()
_active_slot = None
_roster = None
_active_household_id = None


def _household_identity():
    """Conservative identity guard for a zone-travel-only read fallback.

    A valid positive household id is required; it is NOT a substitute for
    identifying the save slot when writing to storage.
    """
    try:
        household = services.active_household()
        household_id = int(getattr(household, 'id', 0))
    except Exception:
        return None
    return household_id if household_id > 0 else None


def _current():
    global _active_slot, _roster, _active_household_id
    slot = current_slot()
    if _active_slot != slot or _roster is None:
        loaded = _store.load(slot)
        _active_slot, _roster = slot, loaded
    _active_household_id = _household_identity()
    return slot, _roster


def _scan_readonly_roster():
    """Use the last verified slot ONLY for a read-only zone diagnostic.

    After travel, get_save_slot_proto_buff().slot_id can be zero. If this
    Python session previously verified a nonzero save slot AND the active
    household identity still matches, allow scanning its JSON, but never
    allow enrollment/withdraw/reset with a zero slot.

    If a save or household changed, fail closed: even this fallback would
    otherwise risk displaying another save's roster.
    """
    try:
        return _current() + (False,)
    except SaveDataError as exc:
        if (not _active_slot or _active_household_id is None or
                _household_identity() != _active_household_id):
            raise SaveDataError(
                '{} Per mhs.scan: torna alla famiglia, esegui mhs.slot, '
                'poi raggiungi il liceo nella STESSA sessione.'.format(exc))
        roster = _store.load(_active_slot)
        return _active_slot, roster, True


def _commit(slot, proposed):
    global _roster
    _store.save(slot, proposed)
    _roster = proposed


def _teen_records():
    manager = services.sim_info_manager()
    if manager is None:
        raise RuntimeError('SimInfo manager non disponibile')
    teens = []
    for info in manager.get_all():
        if info is None or info.age != Age.TEEN:
            continue
        sid = getattr(info, 'sim_id', None)
        if sid is None:
            sid = getattr(info, 'id', None)
        if sid is None:
            continue
        name = '{} {}'.format(str(getattr(info, 'first_name', '') or ''),
                              str(getattr(info, 'last_name', '') or '')).strip()
        teens.append((name or '(senza nome)', str(sid)))
    return sorted(teens, key=lambda row: (row[0].casefold(), int(row[1])))


def _get_teen(sim_id):
    sid = str(sim_id).strip()
    if not sid.isdigit() or not int(sid) or sid != str(int(sid)):
        raise RosterError('ID non valido. Copia il numero mostrato da mhs.teens.')
    manager = services.sim_info_manager()
    if manager is None:
        raise RuntimeError('SimInfo manager non disponibile')
    for info in manager.get_all():
        if info is None:
            continue
        found = getattr(info, 'sim_id', None)
        if found is None:
            found = getattr(info, 'id', None)
        if found is not None and str(found) == sid:
            if info.age != Age.TEEN:
                raise RosterError('Questo Sim non e piu adolescente.')
            return info
    raise RosterError('Sim non trovato. Riesegui mhs.teens.')


def _name(info):
    return '{} {}'.format(str(getattr(info, 'first_name', '') or ''),
                          str(getattr(info, 'last_name', '') or '')).strip() or '(senza nome)'


@sims4.commands.Command('mhs.status', command_type=sims4.commands.CommandType.Live)
def mhs_status(_connection=None):
    out = sims4.commands.CheatOutput(_connection)
    try:
        slot, roster = _current()
        out('MY HIGH SCHOOL v0.9: REGISTRO ESTERNO attivo! Partita ID {}'.format(slot))
        out('Classe 1: {}/8 | Classe 2: {}/8'.format(len(roster.list_class(1)), len(roster.list_class(2))))
        out('Dati JSON separati: NON modificano la scuola ne il file .save.')
        out('ATTENZIONE: non segue automaticamente Salva/Carica una partita precedente.')
    except (SaveDataError, RosterError) as exc:
        out('MY HIGH SCHOOL v0.9: {}'.format(exc))


@sims4.commands.Command('mhs.slot', command_type=sims4.commands.CommandType.Live)
def mhs_slot(_connection=None):
    out = sims4.commands.CheatOutput(_connection)
    try:
        slot, roster = _current()
        out('ID partita: {} | Iscritti totali: {}'.format(slot, len(roster.assignments)))
        out('File dati: {}'.format(_store.path(slot)))
    except SaveDataError as exc:
        out('MY HIGH SCHOOL: {}'.format(exc))


@sims4.commands.Command('mhs.teens', command_type=sims4.commands.CommandType.Live)
def mhs_teens(page: int=1, _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    try:
        if page < 1:
            out('Pagina non valida. Usa mhs.teens 1')
            return
        rows = _teen_records()
        pages = max(1, (len(rows) + 9) // 10)
        if page > pages:
            out('Pagina inesistente: 1-{}'.format(pages))
            return
        out('Adolescenti: {} (pagina {}/{})'.format(len(rows), page, pages))
        for name, sid in rows[(page - 1) * 10:page * 10]:
            out('{} | ID {}'.format(name, sid))
        if page < pages:
            out('Altri: mhs.teens {}'.format(page + 1))
        out('NPC speciali ancora visibili: iscrivi soltanto Sim ordinari.')
    except Exception as exc:
        out('mhs.teens: {}'.format(type(exc).__name__))


@sims4.commands.Command('mhs.find', command_type=sims4.commands.CommandType.Live)
def mhs_find(name: str='', _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    if not name:
        out('Uso: mhs.find Amarachi')
        return
    try:
        matches = [(n, sid) for n, sid in _teen_records() if name.casefold() in n.casefold()]
        out('Corrispondenze: {}'.format(len(matches)))
        for n, sid in matches[:20]:
            out('{} | ID {}'.format(n, sid))
    except Exception as exc:
        out('mhs.find: {}'.format(type(exc).__name__))


@sims4.commands.Command('mhs.enroll', command_type=sims4.commands.CommandType.Live)
def mhs_enroll(sim_id: str='', klass: int=0, _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    if not sim_id or klass not in (1, 2):
        out('Uso: mhs.enroll ID 1 oppure mhs.enroll ID 2')
        return
    try:
        info = _get_teen(sim_id)
        slot, roster = _current()
        changed_roster = SchoolRoster.from_json(roster.to_json())
        changed = changed_roster.enroll(sim_id, klass, True)
        if changed:
            _commit(slot, changed_roster)
        out('{}: {}'.format('ISCRITTO nel REGISTRO PERSISTENTE' if changed else 'Gia iscritto', _name(info)))
        out('Classe {} | {} / 8'.format(klass, len(changed_roster.list_class(klass))))
        out('Solo registro JSON: nessuna convocazione scolastica.')
    except (SaveDataError, RosterError, ValueError) as exc:
        out('Iscrizione rifiutata: {}'.format(exc))
    except Exception as exc:
        out('Errore mhs.enroll: {}'.format(type(exc).__name__))


@sims4.commands.Command('mhs.roster', command_type=sims4.commands.CommandType.Live)
def mhs_roster(klass: int=0, _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    if klass not in (1, 2):
        out('Uso: mhs.roster 1 oppure mhs.roster 2')
        return
    try:
        slot, roster = _current()
        enrolled = roster.list_class(klass)
        out('MY HIGH SCHOOL - Partita {} - Classe {}: {}/8'.format(slot, klass, len(enrolled)))
        for sid in enrolled:
            try:
                out('{} | ID {}'.format(_name(_get_teen(sid)), sid))
            except RosterError:
                out('(Sim non trovato / non adolescente) | ID {}'.format(sid))
        if not enrolled:
            out('Nessuno studente iscritto nel registro.')
        out('Dati salvati in JSON separato, non nel .save di The Sims 4.')
    except (SaveDataError, RosterError) as exc:
        out('Errore mhs.roster: {}'.format(exc))


@sims4.commands.Command('mhs.withdraw', command_type=sims4.commands.CommandType.Live)
def mhs_withdraw(sim_id: str='', _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    if not sim_id:
        out('Uso: mhs.withdraw ID')
        return
    try:
        slot, roster = _current()
        proposed = SchoolRoster.from_json(roster.to_json())
        removed = proposed.withdraw(sim_id)
        if removed:
            _commit(slot, proposed)
        out('Rimosso dal registro JSON.' if removed else 'Non presente nel registro.')
        out('Il Sim rimane nel gioco.')
    except (SaveDataError, RosterError) as exc:
        out('Errore mhs.withdraw: {}'.format(exc))


@sims4.commands.Command('mhs.reset', command_type=sims4.commands.CommandType.Live)
def mhs_reset(confirmation: str='', _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    if confirmation != 'CONFERMA':
        out('ATTENZIONE: azzera il registro persistente! Per confermare: mhs.reset CONFERMA')
        return
    try:
        slot, _ = _current()
        _commit(slot, SchoolRoster(slot, {1: 8, 2: 8}))
        out('Registro JSON della partita {} AZZERATO.'.format(slot))
    except SaveDataError as exc:
        out('Errore mhs.reset: {}'.format(exc))


@sims4.commands.Command('mhs.scan', command_type=sims4.commands.CommandType.Live)
def mhs_scan(_connection=None):
    """Read-only diagnostic: loaded students on the current lot, not attendance."""
    out = sims4.commands.CheatOutput(_connection)
    try:
        slot, roster, used_last_valid = _scan_readonly_roster()
        out('MY HIGH SCHOOL v0.9 - SCANSIONE LOTTO - partita {}'.format(slot))
        if used_last_valid:
            out('ATTENZIONE: il gioco segnala ID 0. Uso l ultimo ID verificato')
            out('nella STESSA sessione e famiglia, SOLO IN LETTURA; non e una prova')
            out('definitiva della partita corrente. NON usare comandi di iscrizione qui.')
        out('Solo lettura: nessuna convocazione, nessun registro assenze.')
        for klass in (1, 2):
            enrolled = roster.list_class(klass)
            out('CLASSE {} - {} iscritti nel registro'.format(klass, len(enrolled)))
            if not enrolled:
                out('(Nessuno studente iscritto)')
            for sid in enrolled:
                try:
                    info = _get_teen(sid)
                except RosterError:
                    out('ID {} - Sim non trovato o non piu adolescente'.format(sid))
                    continue
                try:
                    get_instance = getattr(info, 'get_sim_instance', None)
                    if not callable(get_instance):
                        status = 'NON VERIFICABILE (API Sim non disponibile)'
                    elif get_instance() is not None:
                        status = 'CARICATO (presente nella zona, non prova frequenza lezione)'
                    else:
                        status = 'NON CARICATO nella zona attuale'
                except Exception as exc:
                    status = 'NON VERIFICABILE ({})'.format(type(exc).__name__)
                out('{} | ID {} | {}'.format(_name(info), sid, status))
        out('Esegui sul lotto liceo durante la giornata: NON dice quale aula frequenta.')
    except (SaveDataError, RosterError) as exc:
        out('mhs.scan: {}'.format(exc))
    except Exception as exc:
        out('mhs.scan: errore {}'.format(type(exc).__name__))


@sims4.commands.Command('mhs.school', command_type=sims4.commands.CommandType.Live)
def mhs_school(_connection=None):
    """Diagnostic ONLY: what school situations are running for loaded teens."""
    out = sims4.commands.CheatOutput(_connection)
    try:
        slot, roster, fallback = _scan_readonly_roster()
        from mhs_school_diagnostics import zone_scan
        manager = services.sim_info_manager()
        if manager is None:
            out('mhs.school: SimInfoManager non disponibile.')
            return
        enrolled = set(roster.assignments.keys())
        records = []
        for info in manager.get_all():
            if info is None or getattr(info, 'age', None) != Age.TEEN:
                continue
            sid = getattr(info, 'sim_id', None)
            if sid is None:
                sid = getattr(info, 'id', None)
            if sid is None:
                continue
            records.append((_name(info), str(sid), info))
        situation_manager = services.get_zone_situation_manager()
        result = zone_scan(situation_manager, records, enrolled)
        out('MY HIGH SCHOOL v0.9 - DIAGNOSI SITUAZIONI (SOLO LETTURA)')
        out('Registro della partita {} - {}'.format(slot,
            'ID 0, recuperato SOLO per lettura' if fallback else 'ID verificato'))
        out('Adolescenti caricati nella zona: {}'.format(result['loaded_teens']))
        out('Iscritti nel registro: Classe 1={} Classe 2={}'.format(
            len(roster.list_class(1)), len(roster.list_class(2))))
        counts = result['school_counts']
        out('Situazioni del liceo riconosciute sugli adolescenti: {}'.format(len(counts)))
        for name, count in sorted(counts.items(), key=lambda p: (-p[1], p[0]))[:8]:
            out('{}: {} adolescenti'.format(name, count))
        if len(counts) > 8:
            out('... e altre {} situazioni'.format(len(counts) - 8))
        for error in result['errors'][:2]:
            out('DIAGNOSTICA NON COMPLETA: {}'.format(error))
        out('Esempi di adolescenti sul lotto (max 8):')
        for name, sid, school, enrolled_flag, total in result['rows'][:8]:
            label = 'SCUOLA' if school else 'situazione scolastica NON rilevata'
            reg = 'ISCRITTO' if enrolled_flag else 'non iscritto'
            out('{} | ID {} | {} | {}'.format(name, sid, reg, label))
        if not counts:
            out('Nessuna situazione liceale rilevata: non prova che il liceo sia vuoto.')
        out('NON convoca, non aggiunge tratti, non modifica i dati.')
    except (SaveDataError, RosterError) as exc:
        out('mhs.school: {}'.format(exc))
    except Exception as exc:
        out('mhs.school: errore {}'.format(type(exc).__name__))


@sims4.commands.Command('mhs.joincheck', command_type=sims4.commands.CommandType.Live)
def mhs_joincheck(_connection=None):
    """Read-only enumeration of Base Student instances; NO selection, NO invite.

    Does not consult save-slot identity or JSON. Multiple instances are not
    automatically a problem; we need to see their actual running IDs and
    which LOADED teen Sims the inspection sees in each.
    """
    out = sims4.commands.CheatOutput(_connection)
    try:
        rows = inspect_student_situations(services.get_zone_situation_manager(),
                                          services.sim_info_manager(), Age.TEEN)
        out('MY HIGH SCHOOL v0.7.3 - ISTANZE NPC_Base_Student (SOLO LETTURA)')
        out('Situazioni distinte viste sugli adolescenti caricati: {}'.format(len(rows)))
        for index, row in enumerate(rows[:10], 1):
            out('#{} | ID istanza: {} | adolescenti rilevati: {}'.format(
                index, row['run_id'], len(row['members'])))
            out('Ruolo EA trovato: {} | API invito presente: {}'.format(
                'SI' if row['job_available'] else 'NO',
                'SI' if row['api_available'] else 'NO'))
            members = sorted(row['members'].values())
            if members:
                out('Esempi Sims: {}'.format(', '.join(members[:4])))
        if len(rows) > 10:
            out('... altre {} istanze non mostrate'.format(len(rows)-10))
        if not rows:
            out('Nessuna istanza trovata su adolescenti caricati; NON prova che non esista.')
        out('NON scegliere l istanza in base al numero: nessun invito eseguito.')
        out('mhs.tryjoin resta DISABILITATO. Nessuna modifica a salvataggio/lezioni.')
    except InvitationCheckError as exc:
        out('mhs.joincheck: {}'.format(exc))
    except Exception as exc:
        out('mhs.joincheck: errore {}'.format(type(exc).__name__))


_invite_attempted = False


@sims4.commands.Command('mhs.tryjoin', command_type=sims4.commands.CommandType.Live)
def mhs_tryjoin(confirmation: str='', _connection=None):
    """Safety disabled in v0.8: no live situation mutation."""
    out = sims4.commands.CheatOutput(_connection)
    out('mhs.tryjoin DISABILITATO in v0.7.3: situazione scolastica NON modificata.')
    out('Prima verifichiamo mhs.joincheck e un identificativo affidabile della partita.')


# v0.7.4: Single explicit school invite experiment; never automatic.
# Unlike v0.7.3 it does not pick an existing Base_Student instance arbitrarily.
_call_attempted_this_session = False


@sims4.commands.Command('mhs.amarachi', command_type=sims4.commands.CommandType.Live)
def mhs_amarachi(confirmation: str='', _connection=None):
    global _call_attempted_this_session
    out = sims4.commands.CheatOutput(_connection)
    # The Sims 4 console passes text arguments in lowercase even if typed uppercase.
    if str(confirmation or '').strip().casefold() != 'conferma':
        out('Test SOLO nella partita di prova 3: mhs.amarachi CONFERMA')
        out('Crea UNA situazione scolastica EA per Amarachi. Non garantisce la frequenza.')
        return
    if _call_attempted_this_session:
        out('Tentativo gia eseguito in questa sessione. NON duplicare: riavvia solo se necessario.')
        return
    from mhs_direct_call import (CallError, TARGET_SIM_ID, TEST_SAVE_SLOT,
                                 preflight, check_school_is_running, create_for_am,
                                 BASE_SITUATION_GUID)
    from mhs_school_diagnostics import situation_guid
    try:
        sim_mgr = services.sim_info_manager()
        zone_mgr = services.get_zone_situation_manager()
        if sim_mgr is None:
            raise CallError('SimInfo manager non disponibile')
        info = sim_mgr.get(TARGET_SIM_ID)
        try:
            valid_slot = current_slot()
        except SaveDataError:
            valid_slot = None  # During school game may report 0; ID + name still checked.
        # If THIS session explicitly bound the user's current test copy 11
        # at home, reuse the existing preflight's 'unverified-at-school' path.
        # Do not change the v0.9's blanket slot guard in normal sessions.
        if valid_slot == '11' and _test11_verified_session():
            valid_slot = None
        # Read-only use of TEST slot 3, NEVER write to any roster here.
        roster = _store.load(str(TEST_SAVE_SLOT))
        # Read the class from the existing registry. Never hardcode 'Class 1'
        # and never modify the JSON here.
        enrolled_class = roster.assignments.get(str(TARGET_SIM_ID))
        registered = enrolled_class in (1, 2)
        school_is_running = check_school_is_running(
            zone_mgr, sim_mgr.get_all(), Age.TEEN, situation_guid)
        preflight(info, Age.TEEN, zone_mgr, school_is_running, registered, valid_slot)
        if getattr(info, 'get_sim_instance', None) is not None:
            sim = info.get_sim_instance()
            if sim is not None:
                get_situations = getattr(zone_mgr, 'get_situations_sim_is_in', None)
                if callable(get_situations):
                    for situation in tuple(get_situations(sim) or ()):
                        if situation_guid(situation) == BASE_SITUATION_GUID:
                            out('Amarachi e gia nella situazione EA Base_Student. Nessun duplicato.')
                            return
        from sims4.resources import Types
        from situations.situation_guest_list import (SituationGuestList,
                        SituationGuestInfo, SituationInvitationPurpose)
        tuning_mgr = services.get_instance_manager(Types.SITUATION)
        tuning = tuning_mgr.get(BASE_SITUATION_GUID) if tuning_mgr is not None else None
        # Job 277894 is explicitly assigned by EA to situation 277733 in the
        # user's exported XML. Do not equate this with default_job().
        from mhs_direct_call import BASE_JOB_GUID
        job_type = getattr(Types, 'SITUATION_JOB', None)
        if job_type is None:
            raise CallError('Tipo EA SITUATION_JOB non disponibile: nessuna modifica.')
        job_mgr = services.get_instance_manager(job_type)
        job = job_mgr.get(BASE_JOB_GUID) if job_mgr is not None else None
        if job is None or int(getattr(job, 'guid64', -1)) != BASE_JOB_GUID:
            raise CallError('Ruolo EA 277894 non recuperabile: nessuna modifica.')
        # The trait is original EA tuning; the game can change it again via its
        # own school role buffs. Do NOT override/disable those EA systems.
        trait_mgr = services.get_instance_manager(Types.TRAIT)
        class1_trait = fetch_class1_trait(trait_mgr)
        original_state = bool(info.has_trait(class1_trait))
        # Only one call to create_situation, no retries. On failure we attempt
        # to restore the trait as it was before this command.
        _call_attempted_this_session = True
        try:
            set_ae_class_trait(info, enrolled_class, class1_trait)
            result = create_for_am(info, zone_mgr, tuning, job, SituationGuestList,
                                   SituationGuestInfo, SituationInvitationPurpose.INVITED)
        except Exception:
            restored = restore_trait_state(info, class1_trait, original_state)
            if not restored:
                out('ATTENZIONE: non sono riuscito a ripristinare il tratto Classe 1.')
                out('NON SALVARE questa partita di prova.')
            raise
        out('MY HIGH SCHOOL v0.9: richiesta scolastica EA inviata per Amarachi.')
        out('ID situazione: {} | Classe registro: {}'.format(result, enrolled_class))
        out('Tratto EA Classe 1: {}'.format('PRESENTE' if info.has_trait(class1_trait) else 'ASSENTE'))
        out('Controlla quale aula frequenta durante la lezione: EA puo cambiare il tratto.')
        out('Un solo Sim invitato; registro JSON NON modificato.')
    except (CallError, SaveDataError, RosterError, ClassRouteError) as exc:
        out('MY HIGH SCHOOL: {}'.format(exc))
    except Exception as exc:
        out('MY HIGH SCHOOL: test non riuscito ({}). Nessun secondo tentativo automatico.'.format(type(exc).__name__))


@sims4.commands.Command('mhs.classphase', command_type=sims4.commands.CommandType.Live)
def mhs_classphase(_connection=None):
    """Single read-only check of EA's classroom-phase assignments for Amarachi.

    An earlier v0.8 applied the class1 trait at invite time, but EA can change
    it later through GoToClass2. This command helps distinguish that from a
    full/class-priority phase without attempting any potentially disruptive
    job reassignment.
    """
    out = sims4.commands.CheatOutput(_connection)
    try:
        from mhs_class_phases import inspect_phase, EA_CLASS1_TRAIT
        from mhs_school_diagnostics import situation_guid
        from mhs_direct_call import TARGET_SIM_ID
        from sims4.resources import Types
        manager = services.sim_info_manager()
        info = manager.get(TARGET_SIM_ID) if manager is not None else None
        if info is None:
            out('Amarachi non trovata nel salvataggio corrente: nessuna azione.')
            return
        trait_manager = services.get_instance_manager(Types.TRAIT)
        trait = trait_manager.get(EA_CLASS1_TRAIT) if trait_manager is not None else None
        result = inspect_phase(info, services.get_zone_situation_manager(), trait,
                               situation_guid)
        out('MY HIGH SCHOOL v0.9 - SOLO LETTURA: fase di Amarachi')
        out('Sim caricato: {}'.format('SI' if result['loaded'] else 'NO'))
        flag = result['class1_trait']
        out('Tratto EA Classe 1: {}'.format('SI' if flag else ('NO' if flag is False else 'NON DISPONIBILE')))
        if not result['phases']:
            out('Fasi aula EA: nessuna tra quelle note, in questo momento.')
        for phase in result['phases']:
            out('Fase EA: {}'.format(phase))
        if result.get('warning'):
            out(result['warning'])
        out('NON modifica ruolo, aula, tratto, registro o situazione.')
    except Exception as exc:
        out('mhs.classphase: diagnosi non disponibile ({}); nessuna modifica.'.format(type(exc).__name__))


def _report_seats(out, slot, roster, source):
    """Read-only view of observed NPC situation membership.

    This is not a physical desk counter; playable teens are not necessarily
    represented by NPC class-phase situation membership.
    """
    from mhs_live_seat_adapter import plan_live
    manager = services.sim_info_manager()
    if manager is None:
        out('mhs.seats: SimInfoManager non disponibile.')
        return
    teens = [info for info in manager.get_all()
             if info is not None and getattr(info, 'age', None) == Age.TEEN]
    result = plan_live(roster.assignments, services.get_zone_situation_manager(), teens)
    observation = result['observation']
    out('MY HIGH SCHOOL v1.1.1 - POSTI IN SITUAZIONI EA (SOLO LETTURA)')
    out('Registro partita {} | {} | fase: {}'.format(slot, source, observation['phase']))
    out('Adolescenti caricati esaminati: {}'.format(observation['loaded']))
    if result['plan'] is None:
        out('Impossibile pianificare: fase non rilevata o situazioni ambigue.')
        if observation['ambiguous']:
            out('Sim in DUE gruppi: {}'.format(', '.join(observation['ambiguous'][:4])))
        if observation['errors']:
            out('Errori lettura: {}'.format(len(observation['errors'])))
        out('Nessuna modifica effettuata.')
        return
    for klass in (1, 2):
        state = result['plan'][klass]
        observed = observation['members'][klass]
        out('CLASSE {}: {} Sims nelle situazioni NPC EA | {} iscritti nel registro'.format(
            klass, len(observed), len(state['desired'])))
        if state['missing']:
            for sid in state['missing'][:4]:
                try:
                    name = _name(_get_teen(sid))
                except Exception:
                    name = '(Sim non trovato)'
                out('DA ASSEGNARE: {} (ID {})'.format(name, sid))
        else:
            out('Iscritti osservabili nel gruppo NPC EA atteso.')
        if state['unregistered_occupants']:
            out('Altri Sims in situazione EA: {}'.format(len(state['unregistered_occupants'])))
        if state['status'] in ('NEEDS_SAFE_REPLACEMENT', 'OVER_CAPACITY'):
            out('GRUPPO EA PIENO: nessuno studente spostato.')
    out('ATTENZIONE: sono situazioni NPC EA, NON tutti i banchi fisici o i Sim giocabili.')
    out('Diagnosi soltanto: nessun Sim, tratto, file o salvataggio modificato.')


def _test3_readonly_roster():
    """Explicit test-slot3 readonly override when EA yields zero at school.

    Never store this identity as a verified session slot, and never enable
    roster mutation based on it. A clone of slot3 may be indistinguishable
    at school: informational warning is mandatory.
    """
    from mhs_direct_call import TEST_SAVE_SLOT, TARGET_SIM_ID
    try:
        detected = current_slot()
    except SaveDataError:
        detected = None
    if detected is not None and detected != str(TEST_SAVE_SLOT):
        raise SaveDataError('Partita attuale ID {} non e la prova 3.'.format(detected))
    manager = services.sim_info_manager()
    info = manager.get(TARGET_SIM_ID) if manager is not None else None
    if info is None or getattr(info, 'age', None) != Age.TEEN:
        raise SaveDataError('Amarachi non trovata come adolescente: diagnosi annullata.')
    fullname = _name(info).casefold()
    if 'amarachi' not in fullname or 'darong' not in fullname:
        raise SaveDataError('Nome di Amarachi non corrisponde: diagnosi annullata.')
    roster = _store.load(str(TEST_SAVE_SLOT))
    if roster.assignments.get(str(TARGET_SIM_ID)) != 1:
        raise SaveDataError('Amarachi non e nella Classe 1 del registro di prova 3.')
    return str(TEST_SAVE_SLOT), roster, (detected is None)


@sims4.commands.Command('mhs.seats', command_type=sims4.commands.CommandType.Live)
def mhs_seats(_connection=None):
    """Read-only diagnostic using a verified slot or safe session fallback."""
    out = sims4.commands.CheatOutput(_connection)
    try:
        slot, roster, fallback = _scan_readonly_roster()
        source = 'ID 0, sessione verificata' if fallback else 'ID verificato'
        _report_seats(out, slot, roster, source)
    except (SaveDataError, RosterError, ValueError, RuntimeError) as exc:
        out('mhs.seats: {}'.format(exc))
    except Exception as exc:
        out('mhs.seats: errore {}. Nessuna modifica.'.format(type(exc).__name__))


@sims4.commands.Command('mhs.seats3', command_type=sims4.commands.CommandType.Live)
def mhs_seats3(_connection=None):
    """Read-only diagnosis explicitly tied to test slot 3; no mutations.

    Allows school diagnosis even when EA reports slot_id=0 and mhs.slot was
    not called at home. Does NOT claim to verify the save slot in this case.
    """
    out = sims4.commands.CheatOutput(_connection)
    try:
        slot, roster, unverified = _test3_readonly_roster()
        source = ('PROVA 3 ESPLICITA; slot reale NON verificabile in zona' if unverified
                  else 'ID 3 verificato')
        _report_seats(out, slot, roster, source)
    except (SaveDataError, RosterError, ValueError, RuntimeError) as exc:
        out('mhs.seats3: {}'.format(exc))
    except Exception as exc:
        out('mhs.seats3: errore {}. Nessuna modifica.'.format(type(exc).__name__))


# v1.2: One explicit test-only controlled transfer. NOT automatic.
_v12_transfer_attempted = False


def _v12_verified_session():
    """Require mhs.slot run at home in THIS session before any mutation.

    EA can return slot_id=0 at school. A same-session identity guard is
    stronger than a blind slot3 override, but is NOT cryptographic proof.
    """
    from mhs_direct_call import TEST_SAVE_SLOT
    if str(_active_slot) != str(TEST_SAVE_SLOT) or _active_household_id is None:
        return False
    if _household_identity() != _active_household_id:
        return False
    try:
        observed = current_slot()
    except SaveDataError:
        observed = None
    return observed is None or str(observed) == str(TEST_SAVE_SLOT)


@sims4.commands.Command('mhs.move3', command_type=sims4.commands.CommandType.Live)
def mhs_move3(confirmation: str='', _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    out('DISATTIVATO in v1.3: il trasferimento durante la lezione ha fallito. Usa solo la nuova priorita preventiva.')
    return
    """ONE Amarachi only, conditional class2 -> class1; never other Sims."""
    global _v12_transfer_attempted
    out = sims4.commands.CheatOutput(_connection)
    if str(confirmation or '').strip().casefold() != 'conferma':
        out('TEST SOLO PARTITA 3: mhs.move3 CONFERMA')
        out('Tenta di cambiare il gruppo EA di Amarachi SOLO se e in Classe 2 durante la lezione.')
        out('Prima esegui mhs.slot a casa nella stessa sessione; non salvare se fallisce.')
        return
    if _v12_transfer_attempted:
        out('Test gia tentato in questa sessione. NON ripetere.')
        return
    try:
        if not _v12_verified_session():
            out('BLOCCATO: devi prima eseguire mhs.slot A CASA nella partita di prova 3,')
            out('poi andare a scuola nella STESSA sessione. Nessuna modifica.')
            return
        from mhs_direct_call import TARGET_SIM_ID, TEST_SAVE_SLOT
        from mhs_transfer import prepare_one_transfer, execute_one_transfer, TransferError
        info = services.sim_info_manager().get(TARGET_SIM_ID)
        if info is None or info.age != Age.TEEN or 'amarachi' not in _name(info).casefold() or 'darong' not in _name(info).casefold():
            out('BLOCCATO: identificazione Amarachi fallita.')
            return
        roster = _store.load(str(TEST_SAVE_SLOT))  # READ only
        if roster.assignments.get(str(TARGET_SIM_ID)) != 1:
            out('BLOCCATO: Amarachi non e iscritta alla Classe 1 del registro prova 3.')
            return
        teen_infos = [s for s in services.sim_info_manager().get_all()
                      if s is not None and getattr(s, 'age', None) == Age.TEEN]
        household = services.active_household()
        members = getattr(household, 'sim_info_gen', None)
        if not callable(members):
            out('BLOCCATO: impossibile contare gli studenti giocabili nella zona.')
            return
        playable_teens = 0
        for playable in members():
            if getattr(playable, 'age', None) == Age.TEEN:
                instance = getattr(playable, 'get_sim_instance', None)
                if callable(instance) and instance() is not None:
                    playable_teens += 1
        prepared = prepare_one_transfer(services.get_zone_situation_manager(), teen_infos,
                                         info, True, playable_teens)
        if prepared['status'] == 'ALREADY_CORRECT':
            out('Amarachi e GIA nella situazione EA della Classe 1. NON tocco nulla.')
            return
        _v12_transfer_attempted = True
        out('MY HIGH SCHOOL v1.2: un tentativo di spostamento SOLO per Amarachi.')
        result = execute_one_transfer(prepared)
        if result == 'TRANSFER_OBSERVED':
            out('EA mostra Amarachi in Classe 1, ma verifica se si siede e segue la lezione.')
        else:
            out('Esito: {}. Verifica in gioco.'.format(result))
        out('Non modifica altri Sim o registro JSON. Se noti bug, esci SENZA SALVARE.')
    except (SaveDataError, RosterError, RuntimeError, ValueError) as exc:
        out('mhs.move3: {}'.format(str(exc)))
    except Exception as exc:
        out('mhs.move3: errore {}. Non salvare se ci sono comportamenti anomali.'.format(type(exc).__name__))


# v1.2.1 -- separate, explicit, TEST ONLY binding for the current copy
# identified by the game at HOME as slot 11. This never rewrites or migrates
# Registro_slot_3.json and never widens the old mhs.move3 safety guard.
_test11_binding = None
_test11_transfer_attempted = False
# v1.4: additions are MEMORY ONLY; never save into Registro_slot_3.json.
_v14_trial_assignments = {}
_v14_invited_this_session = set()


def _test11_household_members():
    house = services.active_household()
    getter = getattr(house, 'sim_info_gen', None)
    if not callable(getter):
        raise SaveDataError('Membri della famiglia attiva non disponibili.')
    ids = []
    for info in getter():
        sid = getattr(info, 'sim_id', None)
        if sid is None:
            sid = getattr(info, 'id', None)
        if sid is not None:
            ids.append(str(sid))
    ids.sort()
    return tuple(ids)


def _test11_identity():
    """Never accept only slot number: also check original roster and Sim ID/name."""
    from mhs_direct_call import TARGET_SIM_ID, TEST_SAVE_SLOT
    mgr = services.sim_info_manager()
    info = mgr.get(TARGET_SIM_ID) if mgr is not None else None
    if info is None or info.age != Age.TEEN:
        raise SaveDataError('Amarachi non e adolescente in questo salvataggio.')
    fullname = _name(info).casefold()
    if not ('amarachi' in fullname and 'darong' in fullname):
        raise SaveDataError('Identita di Amarachi diversa da quella della partita di prova.')
    roster = _store.load(str(TEST_SAVE_SLOT))   # READ ONLY -- no migration
    if roster.assignments.get(str(TARGET_SIM_ID)) != 1:
        raise SaveDataError('Registro originale prova 3 non contiene Amarachi in Classe 1.')
    return info, roster


@sims4.commands.Command('mhs.test11', command_type=sims4.commands.CommandType.Live)
def mhs_test11(confirmation: str='', _connection=None):
    """Explicit permission to test slot 11 only, for this live game process."""
    global _test11_binding
    out = sims4.commands.CheatOutput(_connection)
    if str(confirmation or '').strip().casefold() != 'conferma':
        out('SOLO nella partita di PROVA attuale, a CASA: mhs.test11 CONFERMA')
        out('Non altera i file. Abilita test SOLO se EA rileva ID 11.')
        return
    try:
        slot, _ = _current()
        if slot != '11':
            raise SaveDataError('ID partita {} non e 11: nessun test abilitato.'.format(slot))
        hid = _household_identity()
        members = _test11_household_members()
        if hid is None or len(members) == 0:
            raise SaveDataError('Famiglia di prova non verificabile.')
        info, registry = _test11_identity()
        _test11_binding = (slot, hid, members)
        out('PROVA 11 ABILITATA SOLO IN QUESTA SESSIONE: ID 11 e famiglia verificati.')
        out('Amarachi: {} | ID {} | nel registro prova 3: Classe 1.'.format(_name(info), info.sim_id))
        out('Nessun file modificato. Ora puoi andare al liceo nella stessa sessione.')
        out('Non usare questo comando in altre partite, neanche copie del salvataggio.')
    except (SaveDataError, RosterError) as exc:
        _test11_binding = None
        out('BLOCCATO mhs.test11: {}'.format(exc))
    except Exception as exc:
        _test11_binding = None
        out('BLOCCATO mhs.test11: {}. Nessuna modifica.'.format(type(exc).__name__))


def _test11_verified_session():
    if _test11_binding is None:
        return False
    slot, hid, member_ids = _test11_binding
    if slot != '11' or hid is None or _household_identity() != hid:
        return False
    if _test11_household_members() != member_ids:
        return False
    try:
        observed = current_slot()
    except SaveDataError:
        observed = None  # EA sometimes reports zero on the high-school lot
    return observed is None or observed == '11'


@sims4.commands.Command('mhs.seats11', command_type=sims4.commands.CommandType.Live)
def mhs_seats11(_connection=None):
    """Read-only diagnostic of current test slot 11 using old roster 3."""
    out = sims4.commands.CheatOutput(_connection)
    try:
        if not _test11_verified_session():
            raise SaveDataError('Esegui mhs.test11 CONFERMA a casa prima del liceo.')
        _, roster = _test11_identity()
        _report_seats(out, '3', roster, 'PROVA ATTUALE 11 verificata, registro 3 SOLO LETTURA')
    except (SaveDataError, RosterError) as exc:
        out('mhs.seats11: {}'.format(exc))
    except Exception as exc:
        out('mhs.seats11: errore {}. Nessuna modifica.'.format(type(exc).__name__))


@sims4.commands.Command('mhs.move11', command_type=sims4.commands.CommandType.Live)
def mhs_move11(confirmation: str='', _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    out('DISATTIVATO in v1.3: il trasferimento durante la lezione ha fallito. Usa solo la nuova priorita preventiva.')
    return
    """ONE Sim class2 -> class1, ONLY after explicit same-session test binding."""
    global _test11_transfer_attempted
    out = sims4.commands.CheatOutput(_connection)
    if str(confirmation or '').strip().casefold() != 'conferma':
        out('SOLO TEST 11: mhs.move11 CONFERMA, durante la lezione, se Amarachi e in Classe 2.')
        out('Prima mhs.test11 CONFERMA a casa, nella stessa sessione.')
        return
    if _test11_transfer_attempted:
        out('Test gia tentato questa sessione. Non ripetere.')
        return
    try:
        if not _test11_verified_session():
            raise SaveDataError('Sessione/prova 11 NON verificata: NESSUN trasferimento.')
        info, _ = _test11_identity()
        from mhs_transfer import prepare_one_transfer, execute_one_transfer
        mgr = services.sim_info_manager()
        teens = [i for i in mgr.get_all() if i is not None and getattr(i, 'age', None) == Age.TEEN]
        household = services.active_household()
        playable_teens = 0
        for played in household.sim_info_gen():
            if getattr(played, 'age', None) == Age.TEEN:
                inst_getter = getattr(played, 'get_sim_instance', None)
                if callable(inst_getter) and inst_getter() is not None:
                    playable_teens += 1
        # The preflight is strictly read-only and cannot remove/invite Sims.
        try:
            prepared = prepare_one_transfer(services.get_zone_situation_manager(), teens,
                                            info, True, playable_teens)
        except RuntimeError as preflight_error:
            out('mhs.move11 BLOCCO PRIMA DEL TRASFERIMENTO: {}.'.format(preflight_error))
            out('NON e stato spostato alcun Sim. Per sicurezza non salvare questa prova.')
            return
        if prepared['status'] == 'ALREADY_CORRECT':
            out('Amarachi e GIA nella Classe 1. Nessuna modifica.')
            return
        _test11_transfer_attempted = True
        out('UN SOLO tentativo sperimentale per Amarachi (prova 11).')
        outcome = execute_one_transfer(prepared)
        out('Risultato: {}. Verifica la frequenza reale. ESCI SENZA SALVARE.'.format(outcome))
    except (SaveDataError, RosterError, ValueError) as exc:
        out('mhs.move11 BLOCCATO PRIMA DEL TRASFERIMENTO: {}. Nessun Sim spostato.'.format(exc))
    except RuntimeError as exc:
        out('mhs.move11 TENTATIVO NON CONFERMATO: {}. ESCI SENZA SALVARE.'.format(exc))
    except Exception as exc:
        out('mhs.move11: errore {}. ESCI SENZA SALVARE se il test era iniziato.'.format(type(exc).__name__))


# v1.4: Optional trial roster. The original one-student JSON is READ ONLY.
@sims4.commands.Command('mhs.prova11', command_type=sims4.commands.CommandType.Live)
def mhs_prova11(sim_id: str='', klass: int=0, _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    from mhs_priority_at_selection import status
    if not _test11_verified_session():
        out('BLOCCATO: prima mhs.test11 CONFERMA a casa, nella stessa partita.')
        return
    try:
        _, persistent = _test11_identity()
        active, _ = status()
        current = dict(persistent.assignments)
        current.update(_v14_trial_assignments)
        mode = str(sim_id).strip().casefold()
        if not mode:
            out('PROVA v1.4 - SOLO MEMORIA. Non cambia Registro_slot_3.json.')
            for k in (1, 2):
                ids = sorted((sid for sid,c in current.items() if c == k), key=int)
                out('Classe {}: {}/8'.format(k,len(ids)))
                for sid in ids:
                    try:out('{} | {}'.format(_name(_get_teen(sid)),sid))
                    except Exception:out('ID {} (non caricato)'.format(sid))
            out('Aggiungi: mhs.prova11 ID 1 oppure mhs.prova11 ID 2')
            out('RESET senza scritture: mhs.prova11 RESET')
            return
        if active:
            out('BLOCCATO: priorita attiva. Non aggiungere o cambiare studenti durante la giornata.')
            return
        if mode == 'reset':
            _v14_trial_assignments.clear()
            out('Iscrizioni TEMPORANEE azzerate. Registro originale invariato.')
            return
        if klass not in (1,2):
            out('Uso: mhs.prova11 ID 1 oppure mhs.prova11 ID 2')
            return
        info = _get_teen(sim_id)
        sid = str(info.sim_id)
        if sid in persistent.assignments:
            out('Gia presente nel registro originale, Classe {}: non modificabile in prova.'.format(persistent.assignments[sid]))
            return
        proposed = dict(current)
        proposed[sid] = klass
        if sum(1 for c in proposed.values() if c == klass) > persistent.capacities[klass]:
            out('BLOCCATO: Classe {} piena (8 iscritti max).'.format(klass))
            return
        _v14_trial_assignments[sid] = klass
        out('SOLO PROVA: {} | ID {} | Classe {} | non salvato.'.format(_name(info),sid,klass))
        out('Attiva prima di andare a scuola: mhs.priorita11 CONFERMA')
    except (SaveDataError,RosterError) as exc:
        out('mhs.prova11: {}'.format(exc))
    except Exception as exc:
        out('mhs.prova11: errore {}. Nessuna scrittura.'.format(type(exc).__name__))


@sims4.commands.Command('mhs.priorita11', command_type=sims4.commands.CommandType.Live)
def mhs_priorita11(action: str='', _connection=None):
    out=sims4.commands.CheatOutput(_connection)
    from mhs_priority_at_selection import install,uninstall,status
    act=str(action or '').strip().casefold()
    if act=='stop':
        uninstall()
        out('Priorita disattivata. Metodo EA originale ripristinato.')
        return
    if act!='conferma':
        active,logs=status()
        out('PRIORITA v1.4: {}'.format('ATTIVA' if active else 'SPENTA'))
        out('Per attivare a casa: mhs.test11 CONFERMA, mhs.prova11 ID CLASSE, mhs.priorita11 CONFERMA')
        out('Per STOP: mhs.priorita11 STOP')
        for line in logs[-10:]:out(line)
        return
    if not _test11_verified_session():
        out('BLOCCATO: prima mhs.test11 CONFERMA a casa nella stessa sessione.')
        return
    try:
        _,roster=_test11_identity()
        combined=dict(roster.assignments)
        combined.update(_v14_trial_assignments)
        success,msg=install(combined,_test11_verified_session)
        out(('PRIORITA: ' if success else 'BLOCCATO: ')+msg)
        out('Solo candidature EA caricate; non convoca automaticamente e non cambia registro, tratti o capienza.')
        out('Se chiudi il gioco, le aggiunte temporanee scompaiono. Esci senza salvare.')
    except Exception as exc:
        out('BLOCCATO: {}. Nessuna installazione confermata.'.format(type(exc).__name__))


@sims4.commands.Command('mhs.convoca11', command_type=sims4.commands.CommandType.Live)
def mhs_convoca11(sim_id: str='', confirmation: str='', _connection=None):
    """One explicit EA Base Student situation for a chosen TEMP test NPC."""
    out=sims4.commands.CheatOutput(_connection)
    if str(confirmation or '').strip().casefold()!='conferma':
        out('SOLO PROVA 11: mhs.convoca11 ID CONFERMA (soltanto nuovi NPC della lista temporanea)')
        return
    if not _test11_verified_session():
        out('BLOCCATO: prima mhs.test11 CONFERMA a casa nella stessa sessione.')
        return
    from mhs_priority_at_selection import status
    active,_=status()
    if not active:
        out('BLOCCATO: prima mhs.priorita11 CONFERMA a casa.')
        return
    try:
        sid=str(int(sim_id))
        if sid not in _v14_trial_assignments:
            out('BLOCCATO: ID non presente nella lista TEMPORANEA. Nessuna convocazione.')
            return
        if sid in _v14_invited_this_session:
            out('BLOCCATO: gia tentata convocazione di questo ID in questa sessione.')
            return
        if len(_v14_invited_this_session)>=3:
            out('BLOCCATO: limite di tre nuove convocazioni per prova.')
            return
        info=_get_teen(sid)
        if bool(getattr(info,'is_selectable',False)):
            out('BLOCCATO: Sim giocabile, non creare una situazione NPC per lui.')
            return
        from mhs_direct_call import BASE_SITUATION_GUID,BASE_JOB_GUID
        from mhs_school_diagnostics import situation_guid
        from mhs_direct_call import check_school_is_running
        from sims4.resources import Types
        from situations.situation_guest_list import SituationGuestList,SituationGuestInfo,SituationInvitationPurpose
        sim_mgr=services.sim_info_manager()
        manager=services.get_zone_situation_manager()
        if manager is None or not check_school_is_running(manager,sim_mgr.get_all(),Age.TEEN,situation_guid):
            out('BLOCCATO: scuola EA attiva non rilevata.')
            return
        sim=info.get_sim_instance() if callable(getattr(info,'get_sim_instance',None)) else None
        get_for_sim=getattr(manager,'get_situations_sim_is_in',None)
        if sim is not None and callable(get_for_sim):
            if any(situation_guid(s)==BASE_SITUATION_GUID for s in tuple(get_for_sim(sim) or ())):
                out('Gia studente EA: non creare un doppione.')
                return
        situation_mgr=services.get_instance_manager(Types.SITUATION)
        job_mgr=services.get_instance_manager(Types.SITUATION_JOB)
        tuning=situation_mgr.get(BASE_SITUATION_GUID) if situation_mgr is not None else None
        job=job_mgr.get(BASE_JOB_GUID) if job_mgr is not None else None
        if tuning is None or job is None or int(getattr(job,'guid64',0))!=BASE_JOB_GUID:
            out('BLOCCATO: tuning/ruolo EA non recuperabile.')
            return
        trait_mgr=services.get_instance_manager(Types.TRAIT)
        trait=fetch_class1_trait(trait_mgr)
        original_state=bool(info.has_trait(trait))
        _v14_invited_this_session.add(sid)  # limit even when API fails
        try:
            set_ae_class_trait(info,_v14_trial_assignments[sid],trait)
            guests=SituationGuestList(invite_only=True)
            guests.add_guest_info(SituationGuestInfo.construct_from_purpose(int(sid),job,SituationInvitationPurpose.INVITED))
            result=manager.create_situation(tuning,guest_list=guests,user_facing=False,
                creation_source='MY HIGH SCHOOL v1.4 TEST 11')
            if not result:
                raise RuntimeError('EA non ha avviato la situazione')
        except Exception:
            if not restore_trait_state(info,trait,original_state):
                out('ATTENZIONE: non si e potuto ripristinare il tratto iniziale.')
            raise
        out('Richiesta EA per {} | Classe prova {} | ID situazione {}.'.format(_name(info),_v14_trial_assignments[sid],result))
        out('Controlla presenza e aula, non garantite. ESCI SENZA SALVARE.')
    except Exception as exc:
        out('mhs.convoca11: {}. Nessun secondo tentativo in questa sessione.'.format(type(exc).__name__))
        out('ESCI SENZA SALVARE se il tentativo era iniziato.')

# v1.5 - capacity observation. NO physical placement or NPC fill.
@sims4.commands.Command('mhs.posti11', command_type=sims4.commands.CommandType.Live)
def mhs_posti11(giocabili_1: int=-1, giocabili_2: int=-1, _connection=None):
    """Read EA class phase members and optionally add visually confirmed playable pupils.

    mhs.posti11       -> verified situation memberships + unknown played count.
    mhs.posti11 3 0   -> manual observation of the three PLAYED teens in class 1.
    NEVER writes to JSON; excludes school staff; no situation changes.
    """
    out=sims4.commands.CheatOutput(_connection)
    if not _test11_verified_session():
        out('mhs.posti11 BLOCCATO: prima mhs.test11 CONFERMA a casa, stessa sessione.')
        return
    if (giocabili_1 == -1) != (giocabili_2 == -1):
        out('Uso: mhs.posti11 oppure mhs.posti11 3 0 (giocabili visti in ciascuna aula).')
        return
    declared = None
    if giocabili_1 != -1:
        if giocabili_1 < 0 or giocabili_2 < 0 or giocabili_1 > 8 or giocabili_2 > 8:
            out('BLOCCATO: conteggi giocabili fuori intervallo 0-8.')
            return
        declared=(giocabili_1,giocabili_2)
    try:
        from mhs_capacity_observer import observe_school,CapacityObservationError
        mgr=services.sim_info_manager()
        if mgr is None:raise CapacityObservationError('Gestione adolescenti non disponibile')
        teen_infos=[i for i in mgr.get_all() if i is not None and getattr(i,'age',None)==Age.TEEN]
        household=services.active_household()
        member_gen=getattr(household,'sim_info_gen',None)
        if not callable(member_gen):raise CapacityObservationError('Membri famiglia non disponibili')
        played_ids=[]
        for info in member_gen():
            if getattr(info,'age',None) != Age.TEEN:continue
            getter=getattr(info,'get_sim_instance',None)
            if not callable(getter):continue
            try:inst=getter()
            except Exception:continue
            if inst is None:continue
            sid=getattr(info,'sim_id',None)
            if sid is None:sid=getattr(info,'id',None)
            if sid is not None:played_ids.append(str(sid))
        audit=observe_school(services.get_zone_situation_manager(), teen_infos, played_ids, declared)
        out('MY HIGH SCHOOL v1.5 - CAPIENZA 8 per aula (SOLO LETTURA)')
        out('Fase EA: {} | giocabili adolescenti caricati: {}'.format(audit['phase'],audit['played_loaded']))
        for klass in (1,2):
            out('AULA {}: NPC nelle situazioni EA {} | giocabili riconosciuti nelle stesse situazioni {}'.format(klass,audit['npc'][klass],audit['played_in_ea'][klass]))
        out('Giocabili caricati senza aula NPC riconoscibile: {}.'.format(audit['played_unknown']))
        if audit['estimated'] is None:
            out('Non posso attribuirli automaticamente a una aula con certezza.')
            out('Se li vedi fisicamente seduti: mhs.posti11 3 0 (esempio: 3 in aula 1, 0 in aula 2).')
        else:
            for klass in (1,2):
                total=audit['estimated'][klass]
                free=audit['free'][klass]
                out('AULA {}: stimati {}/8 studenti complessivi | posti {}.'.format(klass,total,
                    'liberi '+str(free) if free >= 0 else 'OLTRE LIMITE DI '+str(-free)))
            out('I conteggi dei giocabili sono dichiarati da te, non verificati dalla posizione dei banchi.')
        out('Personale scolastico NON contato. Nessuna modifica al gioco o al registro.')
        out('La priorita v1.4 resta attiva; questo comando NON impone la capienza.')
    except (ValueError, RuntimeError) as exc:
        out('mhs.posti11 NON VERIFICABILE: {}. Nessuna modifica.'.format(exc))
    except Exception as exc:
        out('mhs.posti11 ERRORE {}. Nessuna modifica.'.format(type(exc).__name__))


# v1.6 — free manual classroom choice for active-household playable teen Sims.
# Trial-only: first two EA classrooms may be nudged via original hidden trait;
# classroom three is a planned room, not yet a created EA class situation.
_v16_playable_plan = {}
_v16_trait_backup = {}


def _v16_playable_household():
    house=services.active_household()
    gen=getattr(house,'sim_info_gen',None)
    if not callable(gen):raise SaveDataError('Famiglia attiva non disponibile')
    result={}
    for info in gen():
        if getattr(info,'age',None)!=Age.TEEN:continue
        getter=getattr(info,'get_sim_instance',None)
        if not callable(getter):continue
        try:inst=getter()
        except Exception:continue
        if inst is None:continue
        result[str(info.sim_id)]=info
    return result


@sims4.commands.Command('mhs.aula11',command_type=sims4.commands.CommandType.Live)
def mhs_aula11(sim_id: str='', room: int=0, _connection=None):
    """Temporary teen-player classroom plan for 3 rooms, no persistent writes.

    mhs.aula11 -> status, mhs.aula11 ID 1/2/3 -> select; RESET, APPLICA, RIPRISTINA.
    APPLY is an explicit experimental EA Class1 hidden-trait hint for rooms 1/2
    only, before class. It does NOT route seats or create the third classroom.
    """
    out=sims4.commands.CheatOutput(_connection)
    if not _test11_verified_session():
        out('BLOCCATO: verifica PRIMA questa partita di prova con mhs.test11 CONFERMA a casa.')
        return
    from mhs_playable_rooms import reserve_playable,occupancy,apply_original_ea_marker,PlayablePlanError
    action=str(sim_id or '').strip().casefold()
    try:
        playable=_v16_playable_household()
        _,roster=_test11_identity()
        npc=dict(roster.assignments)
        npc.update(_v14_trial_assignments)
        if not action:
            out('MY HIGH SCHOOL v1.6 | PROGETTO 3 AULE x 8 | GIOCABILI (SOLO SESSIONE)')
            for sid,info in sorted(playable.items(),key=lambda x:_name(x[1])):
                planned=_v16_playable_plan.get(sid)
                out('{} | ID {} | {}'.format(_name(info),sid,'Aula '+str(planned) if planned else 'aula non scelta'))
            for k,v in occupancy(npc,_v16_playable_plan).items():
                out('AULA {}: {} NPC scelti + {} giocabili scelti = {}/8 previsti{}'.format(k,v['npc'],v['giocabili'],v['npc']+v['giocabili'], ' | SOLO PROGETTO (aula EA 3 non esiste)' if k==3 else ''))
            out('Seleziona: mhs.aula11 ID 1 (o 2 o 3); ripristina piano: mhs.aula11 RESET')
            out('PER PROVA CLASSI EA 1/2 (non garantita): a scuola PRIMA delle lezioni mhs.aula11 APPLICA')
            out('L aula 3 non e ancora utilizzabile per la lezione. Nessuna scrittura su JSON.')
            return
        if action=='reset':
            if _v16_trait_backup:
                out('BLOCCATO: prima RIPRISTINA i tratti sperimentali e poi RESET.')
                return
            try:slot=current_slot()
            except Exception:slot=None
            if slot!='11':
                out('RESET consentito soltanto a casa con ID partita 11 confermato.')
                return
            _v16_playable_plan.clear()
            out('Piano giocabili della SESSIONE azzerato. Nessun file modificato.')
            return
        if action=='ripristina':
            if not _v16_trait_backup:
                out('Nessun tratto applicato tramite questa prova.')
                return
            trait_mgr=services.get_instance_manager(__import__('sims4.resources',fromlist=['Types']).Types.TRAIT)
            trait=fetch_class1_trait(trait_mgr)
            for sid,before in tuple(_v16_trait_backup.items()):
                info=playable.get(sid)
                if info is None:
                    out('ATTENZIONE: {} non caricato; esci senza salvare.'.format(sid))
                    continue
                if restore_trait_state(info,trait,before):del _v16_trait_backup[sid]
            out('Ripristino richiesto; tratti rimasti in sospeso: {}. ESCI SENZA SALVARE.'.format(len(_v16_trait_backup)))
            return
        if action=='applica':
            if _v16_trait_backup:
                out('BLOCCATO: tratti gia applicati. RIPRISTINA e ricomincia senza salvare.')
                return
            if room!=0:
                out('Uso: mhs.aula11 APPLICA (senza numero)')
                return
            if not _v16_playable_plan:
                out('Nessuna aula scelta: prima mhs.aula11 ID 1/2 per i giocabili.')
                return
            if any(k==3 for k in _v16_playable_plan.values()):
                out('BLOCCATO: Aula 3 non esiste ancora come classe EA. Nessun tratto modificato.')
                return
            from mhs_school_diagnostics import situation_guid
            from mhs_direct_call import check_school_is_running
            mgr=services.get_zone_situation_manager()
            if mgr is None or not check_school_is_running(mgr,services.sim_info_manager().get_all(),Age.TEEN,situation_guid):
                out('BLOCCATO: devi essere al liceo EA attivo, prima delle lezioni.')
                return
            from mhs_live_seat_adapter import read_assignments
            observed=read_assignments(mgr,[i for i in services.sim_info_manager().get_all() if getattr(i,'age',None)==Age.TEEN])
            if observed['phase']!='non rilevata':
                out('BLOCCATO: preparazione/lezione gia avviata; prova PRIMA dell orario delle lezioni.')
                return
            trait_mgr=services.get_instance_manager(__import__('sims4.resources',fromlist=['Types']).Types.TRAIT)
            trait=fetch_class1_trait(trait_mgr)
            previous=apply_original_ea_marker(_v16_playable_plan,playable,trait,set_ae_class_trait,restore_trait_state)
            _v16_trait_backup.update(previous)
            out('PROVA SEGNALINI EA: applicati {} adolescenti giocabili, Classi 1/2.'.format(len(previous)))
            out('ATTENZIONE: e solo un suggerimento EA: NON assicura la classe e puo essere sovrascritto.')
            out('Il motore delle aule e la terza aula non sono ancora implementati. ESCI SENZA SALVARE.')
            return
        if room not in (1,2,3):
            out('Uso: mhs.aula11 ID 1 (oppure 2, 3).')
            return
        if _v16_trait_backup:
            out('BLOCCATO: scelta durante test attivo. Prima RIPRISTINA e torna a casa.')
            return
        try:slot=current_slot()
        except Exception:slot=None
        if slot!='11':
            out('Scelta consentita SOLO a casa nella partita di prova 11.')
            return
        plan=reserve_playable(_v16_playable_plan,npc,sim_id,room,playable.keys())
        _v16_playable_plan.clear()
        _v16_playable_plan.update(plan)
        out('SCELTA PROVA: {} -> Aula {} | non salvata.'.format(_name(playable[str(sim_id)]),room))
        if room==3:out('Aula 3: scelta progettuale registrata, MA non esiste ancora una lezione EA per aula 3.')
        else:out('Prima delle lezioni, sul lotto liceo, puoi tentare mhs.aula11 APPLICA.')
    except (PlayablePlanError,SaveDataError,RosterError,ClassRouteError) as exc:
        out('mhs.aula11 BLOCCATO: {}. Nessun salvataggio scritto.'.format(exc))
    except Exception as exc:
        out('mhs.aula11 ERRORE: {}. Non salvare questa giornata di test.'.format(type(exc).__name__))
