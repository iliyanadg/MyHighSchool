"""v1.6. Only in-memory, three 8-seat target classrooms; EA only has 2 real classrooms.

Playable selections DO NOT equal physical placement. The optional test applies only
EA's original 293779 Class1 marker to 1/2; class 3 has NO EA situation.
"""
CAPACITY=8
ROOMS=(1,2,3)

class PlayablePlanError(ValueError):pass

def _sid(value):
    s=str(value).strip()
    if not s.isdigit() or not int(s) or str(int(s))!=s:
        raise PlayablePlanError('ID Sim non valido')
    return s

def reserve_playable(current, npc_mapping, playable_id, room, eligible_ids):
    if type(room) is not int or room not in ROOMS:
        raise PlayablePlanError('Aula valida: 1, 2 oppure 3')
    sid=_sid(playable_id)
    allowed=set(_sid(v) for v in eligible_ids)
    if sid not in allowed:
        raise PlayablePlanError('Puoi scegliere solo un adolescente giocabile della famiglia attiva')
    others={_sid(i):int(k) for i,k in npc_mapping.items()}
    if sid in others:
        raise PlayablePlanError('Sim gia presente nel registro NPC: non duplicarlo')
    plan={_sid(i):int(k) for i,k in current.items()}
    plan[sid]=room
    counts={k:0 for k in ROOMS}
    for s,k in list(others.items())+list(plan.items()):
        if k not in ROOMS:raise PlayablePlanError('Assegnazione di aula non valida')
        counts[k]+=1
        if counts[k]>CAPACITY:
            raise PlayablePlanError('Aula {}: massimo 8 iscritti previsti (NPC + giocabili)'.format(k))
    return plan

def occupancy(npc_mapping, playable_mapping):
    counts={k:{'npc':0,'giocabili':0} for k in ROOMS}
    for sid,room in npc_mapping.items():
        if room in counts:counts[room]['npc']+=1
    for sid,room in playable_mapping.items():
        if room in counts:counts[room]['giocabili']+=1
    return counts


def apply_original_ea_marker(plan, infos_by_id, trait, setter, restore):
    """Test-only pre-lesson marker 1/2. Atomic best-effort rollback on failure.

    Never claim this enforces seating; EA may remove marker before class.
    """
    if not plan:raise PlayablePlanError('Nessuna aula giocabile assegnata')
    if any(k==3 for k in plan.values()):
        raise PlayablePlanError('Aula 3 non supportata dalle lezioni EA: nessun tratto modificato')
    before={}
    try:
        for sid,room in sorted(plan.items(),key=lambda item:int(item[0])):
            if room not in (1,2):raise PlayablePlanError('Classe non applicabile nel gioco EA')
            info=infos_by_id.get(sid)
            if info is None:raise PlayablePlanError('Sim giocabile non caricato: '+sid)
            previous=bool(info.has_trait(trait))
            before[sid]=previous
            setter(info,room,trait)
        return before
    except Exception:
        for sid,previous in before.items():
            try:restore(infos_by_id[sid],trait,previous)
            except Exception:pass
        raise
