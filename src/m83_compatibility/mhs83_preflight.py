"""M83: pure fail-closed school roster/capacity preflight for current Mac patch.

Not an EA runtime hook, tuning override, NPC spawner or proof of attendance.
Never imports EA modules or changes a saved game.
"""
MAC_PATCH='1.129.39.1230'
PHASES=('go_to_class_1','attend_class_1','go_to_class_2','attend_class_2')

def read_game_version(raw):
    """Accept GameVersion.txt bytes, including NUL prefix, never guess patch."""
    if isinstance(raw,bytes):
        try: raw=raw.decode('ascii')
        except UnicodeDecodeError: return None
    if not isinstance(raw,str): return None
    value=raw.strip('\x00 \n\r\t\ufeff')
    parts=value.split('.')
    if len(parts)!=4 or any(not p.isdigit() for p in parts): return None
    return value

def _ids(values):
    if values is None: return None
    try: items=tuple(values)
    except TypeError: return None
    ids=[]
    for value in items:
        if isinstance(value,bool) or not isinstance(value,(str,int)): return None
        sid=str(value)
        if not sid.isdigit() or int(sid)<=0 or str(int(sid))!=sid:
            return None
        ids.append(sid)
    return tuple(ids) if len(set(ids))==len(ids) else None

def _other_school_controller(name):
    """Known high-school controllers only: Sonozaki Elementary is different."""
    s=str(name).lower().replace(' ','').replace('_','').replace('-','')
    return ('morestudents' in s or 'highschoolmoreclassmates' in s
            or 'choosehighschoolclassmates' in s
            or ('sonozaki' in s and 'highschoolmanagement' in s))

def full_roster_preflight(game_version,class_members,verified_human_teen_ids,
                          playable_ids=(),verified_core_student_ids=None,
                          available_base_student_slots=None,verified_phase_caps=None,
                          installed_other_mods=()):
    """Offline capacity gate; requires live-version evidence for all capacities.

    EA Base Student NPC slots, core roles, playable teens, and classroom phase
    slots are different counts. Unknown evidence means BLOCKED (EA preserved).
    """
    def stop(reason,**more):
        out={'status':'BLOCKED','reason':reason,'runtime_mutations':False,
             'school_attendance_proven':False}
        out.update(more)
        return out
    if read_game_version(game_version)!=MAC_PATCH:
        return stop('unverified or different Mac game patch')
    if any(_other_school_controller(n) for n in (installed_other_mods or ())):
        return stop('competing high school controller installed')
    if not isinstance(class_members,dict) or set(class_members)!={1,2}:
        return stop('requires exactly Class 1 and Class 2')
    first=_ids(class_members[1]); second=_ids(class_members[2])
    if first is None or second is None or len(first)!=8 or len(second)!=8:
        return stop('requires eight unique students in each class')
    roster=first+second
    if len(set(roster))!=16: return stop('duplicate Sim across classes')
    eligible=_ids(verified_human_teen_ids); playable=_ids(playable_ids)
    if eligible is None or playable is None or not set(roster).issubset(eligible):
        return stop('not all registered IDs verified as living human teens')
    enrolled_playable=tuple(s for s in roster if s in playable)
    if verified_core_student_ids is None:
        return stop('EA core role identities not verified',
                    roster_ids=roster,registered_playables=enrolled_playable)
    core=_ids(verified_core_student_ids)
    if core is None or not set(core).issubset(roster) or set(core)&set(playable):
        return stop('invalid or conflicting EA core role identities')
    regular=tuple(s for s in roster if s not in playable and s not in core)
    if available_base_student_slots is None or type(available_base_student_slots) is not int:
        return stop('current EA base-student situation capacity unknown',
                    required_base_slots=len(regular))
    if available_base_student_slots<len(regular):
        return stop('insufficient verified EA base-student slots',
                    required_base_slots=len(regular),
                    available_base_slots=available_base_student_slots)
    if not isinstance(verified_phase_caps,dict) or set(verified_phase_caps)!=set(PHASES):
        return stop('current EA classroom phase capacity unknown')
    if any(type(verified_phase_caps[k]) is not int or verified_phase_caps[k]<8
           for k in PHASES):
        return stop('insufficient verified EA classroom phase capacity')
    return {'status':'OFFLINE_PLAN_ONLY',
            'reason':'capacity inputs consistent; EA runtime attendance unverified',
            'mac_patch':MAC_PATCH,'classes':{1:first,2:second},
            'registered_playables':enrolled_playable,'registered_core':core,
            'planned_base_npcs':regular,'required_base_slots':len(regular),
            'available_base_slots':available_base_student_slots,
            'runtime_mutations':False,'school_attendance_proven':False}
