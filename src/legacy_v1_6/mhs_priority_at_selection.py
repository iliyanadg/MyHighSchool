"""MY HIGH SCHOOL v1.4 - opt-in, test-save-only MULTI-student selection priority.

EA WeeklyScheduleSituationData.try_start iterates a set of instantiated Sims.
Prioritization is per requested classroom; the underlying EA job tests, situations,
capacity and schedule remain unchanged. Temporary class-2 candidates are NOT
eligible for the Class-1 selection when the opt-in trial is armed; they remain
available to the subsequent EA 'Others' snippet. EA is free to reject any Sim
or not spawn it; this mod does not guarantee attendance or 8 physical seats.

Preserves the original set-difference contract ONLY after successful creation,
without patching unrelated EA situations. No file or persistent roster writes.
"""
CLASS1_IDS = frozenset((293642,293644,304563,304561))
CLASS2_IDS = frozenset((297773,304570))
TARGET_SITUATION_DATA_IDS = CLASS1_IDS | CLASS2_IDS
_active=False
_original_descriptor=None
_guard=None
_patched_class=None
_groups={1:tuple(),2:tuple()}
_events=[]


def _sid(sim):
    val=getattr(sim,'sim_id',None)
    if val is None:
        val=getattr(getattr(sim,'sim_info',None),'sim_id',None)
    return str(val) if val is not None else ''


class PrioritizedCandidatePool(set):
    """Set whose iteration starts with registered candidates for one group.

    The pool may contain fewer candidates than EA's full source set, exclusively
    to reserve trial Class-2 candidates from an earlier Class-1 selection.
    """
    def __init__(self, original, preferred):
        set.__init__(self,original)
        self.preferred=frozenset(str(v) for v in preferred)
    def __iter__(self):
        all_sims=list(set.__iter__(self))
        first=sorted((sim for sim in all_sims if _sid(sim) in self.preferred),key=_sid)
        rest=[sim for sim in all_sims if _sid(sim) not in self.preferred]
        return iter(first+rest)


def _record(message):
    _events.append(message)
    if len(_events)>16: del _events[:-16]


def _verified():
    if not _active or _guard is None:return False
    try:return bool(_guard())
    except Exception:return False


def _normalize(mapping):
    groups={1:[],2:[]}
    if not isinstance(mapping,dict):raise ValueError('Registro prova non valido')
    ids=set()
    for raw_id,raw_klass in mapping.items():
        sid=str(raw_id).strip()
        if not sid.isdigit() or not int(sid) or sid in ids:
            raise ValueError('ID di prova non valido o ripetuto')
        if type(raw_klass) is not int or raw_klass not in groups:
            raise ValueError('Classe di prova non valida')
        groups[raw_klass].append(sid)
        ids.add(sid)
    if len(groups[1])>8 or len(groups[2])>8:
        raise ValueError('Massimo 8 iscritti per classe')
    return {klass:tuple(sorted(ids,key=int)) for klass,ids in groups.items()}


def install(mapping, guard):
    """Install once per session, exact classmethod restoration via STOP."""
    global _active,_original_descriptor,_guard,_patched_class,_groups
    if _active:return False,'Priorita gia attiva; STOP per disattivarla'
    if not callable(guard):return False,'Controllo sessione non disponibile'
    try:groups=_normalize(mapping)
    except ValueError as exc:return False,str(exc)
    if not groups[1]:return False,'Nessun iscritto di prova per la Classe 1'
    try:
        from venues.weekly_schedule_zone_director import WeeklyScheduleSituationData
    except ImportError:
        return False,'Modulo EA non importabile'
    base=WeeklyScheduleSituationData
    desc=base.__dict__.get('try_start')
    if not isinstance(desc,classmethod):return False,'Metodo EA originale non trovato'
    original=desc.__func__

    def wrapped(cls,sims,sim_info,duration,additional_sim_ids,situation_job_count):
        try:guid=int(getattr(cls,'guid64',0) or 0)
        except (ValueError,TypeError):guid=0
        if guid not in TARGET_SITUATION_DATA_IDS or not _verified():
            return original(cls,sims,sim_info,duration,additional_sim_ids,situation_job_count)
        if not isinstance(sims,set):
            return original(cls,sims,sim_info,duration,additional_sim_ids,situation_job_count)
        if guid in CLASS1_IDS:
            # Class 2 candidates should remain free for EA's subsequent
            # 'Others' phase. Never remove them from the caller-owned pool.
            candidates=PrioritizedCandidatePool((s for s in sims if _sid(s) not in _groups[2]),_groups[1])
            klass=1
        else:
            candidates=PrioritizedCandidatePool(sims,_groups[2])
            klass=2
        before=set(candidates)
        # Never retry EA call; after a partial creation that risks duplicates.
        result=original(cls,candidates,sim_info,duration,additional_sim_ids,situation_job_count)
        if result is not None:
            selected=before.difference(candidates)
            sims.difference_update(selected)
            taken=sorted(_sid(s) for s in selected if _sid(s) in _groups[klass])
            _record('Fase {} | EA {}: gruppo {} | nostri {} / {}{}'.format(
                'aula '+str(klass),guid,len(selected),len(taken),len(_groups[klass]),
                ' | ID '+','.join(taken) if taken else ''))
        else:
            _record('Fase aula {} | EA {}: situazione non avviata'.format(klass,guid))
        return result
    try:base.try_start=classmethod(wrapped)
    except Exception as exc:return False,'Hook EA rifiutato: '+type(exc).__name__
    _original_descriptor=desc
    _patched_class=base
    _guard=guard
    _groups=groups
    _events[:]=[]
    _active=True
    return True,'Priorita gruppo attivata: Classe 1 {} iscritti, Classe 2 {} iscritti; 6 snippet EA'.format(len(groups[1]),len(groups[2]))


def uninstall():
    global _active,_original_descriptor,_guard,_patched_class,_groups
    _active=False
    if _patched_class is not None and _original_descriptor is not None:
        _patched_class.try_start=_original_descriptor
    _original_descriptor=None
    _patched_class=None
    _guard=None
    _groups={1:tuple(),2:tuple()}
    _record('Priorita gruppo disattivata')
    return True


def status():
    return bool(_active),tuple(_events)
