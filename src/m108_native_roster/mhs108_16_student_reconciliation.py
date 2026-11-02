"""M108: reconcile all 16 school teens from REAL post-Bouncer EA job evidence.

An invitation is not a native role; a native school role is not a seat.
The two Class1 With/NoTrait situations form ONE MHS class. The Class2
prepare job ID overlaps Class1 job ID. Route by EA situation GUID and
original phase clock, never job number alone.

No gameplay hook or Sim mutation. This is an offline diagnostic contract.
"""
from mhs108_native_invitation import prepare_fixed_manifest, InvitationPlanError
from mhs108_post_bouncer_audit import (
    NativeJobAudit, EA_PHASE_BY_SITUATION,
)

WINDOWS={'09:30':'prepare','10:00':'lesson',
         '13:30':'prepare','14:00':'lesson'}


def _set_of_ids(seq):
    if not isinstance(seq,(list,tuple,set,frozenset)):
        return None
    out=set()
    for value in seq:
        if (type(value) not in (int,str) or not str(value).isdigit()
                or int(value)<1 or str(int(value))!=str(value)
                or str(value) in out):
            return None
        out.add(str(value))
    return out


def _blocked(status,reason='',**details):
    result={
        'status':status,'reason':reason,
        'game_modified':False,
        'native_ea_16_student_membership_verified':False,
        'exact_class_ea_jobs_verified':False,
        'class_8_plus_8_seating_verified':False,
        'full_school_day_verified':False,
    }
    result.update(details)
    return result


def reconcile_16_school_members(manifest,job_audit,phase_key,
                                observed_zone_teen_ids,
                                observed_player_school_job_ids,
                                context):
    """Confirm a single exact native school phase, NOT the full day.

    Caller must obtain player job members from ORIGINAL EA situations,
    not just the household list or planned class. NPC members must come
    from NativeJobAudit.observe after actual Bouncer assignment.
    """
    try:
        canonical=prepare_fixed_manifest(
            manifest['classes'],manifest['playable'],
            dict(manifest['core_assignments']),manifest['save_slot'],
            manifest['sim_day'],manifest['school_zone'])
        if any(manifest.get(k)!=canonical[k] for k in (
                'classes','playable','all_16','core_assignments',
                'base_ids','save_slot','sim_day','school_zone')):
            return _blocked('INVALID_MANIFEST')
        if not isinstance(job_audit,NativeJobAudit):
            return _blocked('UNVERIFIED_EA_JOB_OBSERVER')
        if job_audit.manifest!=canonical:
            return _blocked('WRONG_EA_JOB_OBSERVER_SAVE')
        if (not isinstance(phase_key,tuple) or len(phase_key)!=4
                or phase_key[0]!=canonical['save_slot']
                or type(phase_key[1]) is not int
                or phase_key[1]!=canonical['sim_day']
                or phase_key[2]!=canonical['school_zone']
                or phase_key[3] not in WINDOWS):
            return _blocked('UNVERIFIED_PHASE')
        if (not isinstance(context,dict)
                or context.get('observed_player_ea_job_verified') is not True
                or context.get('observed_zone_teens_verified') is not True
                or context.get('post_bouncer_phase_verified') is not True
                or context.get('ea_all_classroom_phase_situations_verified')
                   is not True
                or context.get('zone_id')!=canonical['school_zone']
                or context.get('time_window')!=phase_key[3]):
            return _blocked('UNVERIFIED_LIVE_OBSERVATIONS')
        zone=_set_of_ids(observed_zone_teen_ids)
        player=_set_of_ids(observed_player_school_job_ids)
        if zone is None or player is None:
            return _blocked('INVALID_OBSERVATION_IDS')
        if player!=set(canonical['playable']):
            return _blocked('PLAYABLE_SCHOOL_JOB_MISMATCH',
                            missing_playables=tuple(sorted(
                                set(canonical['playable'])-player)),
                            extraneous_playables=tuple(sorted(
                                player-set(canonical['playable']))))
        if not set(canonical['all_16']) <= zone:
            return _blocked('REGISTERED_STUDENT_NOT_ON_LOT',
                            missing_students=tuple(sorted(
                                set(canonical['all_16'])-zone)))
        # Additional teenagers might exist on the zone as invited guests;
        # report them, but don't silently call them MHS enrollees.
        seen={1:set(),2:set()}
        statuses=[]
        for situation_id,data in job_audit._pending.items():
            if data['phase']==phase_key:
                statuses.append(('pending',situation_id))
        for situation_id,data in job_audit._failed.items():
            if data.get('phase_key')==phase_key:
                statuses.append(('rejected',situation_id))
        for sid,result in job_audit._verified.items():
            if result.get('phase_key')!=phase_key:
                continue
            situation_guid=result['situation_guid']
            stage,index,job,staff=EA_PHASE_BY_SITUATION[situation_guid]
            if stage!=WINDOWS[phase_key[3]]:
                return _blocked('EA_PHASE_TYPE_MISMATCH')
            student_ids=set(result['actual_ids_by_job'][job])
            if seen[index] & student_ids:
                return _blocked('DUPLICATE_SCHOOL_CLASS_MEMBERSHIP')
            seen[index].update(student_ids)
            statuses.append(('verified',sid))
        native_phase_ids=_set_of_ids(
            context.get('observed_ea_classroom_phase_situation_ids'))
        if native_phase_ids is None:
            return _blocked('NATIVE_SITUATION_ENUMERATION_UNVERIFIED')
        recorded_phase_ids=set(str(sid) for _,sid in statuses)
        if native_phase_ids!=recorded_phase_ids:
            return _blocked('UNTRACKED_NATIVE_CLASSROOM_SITUATIONS',
                            untracked_situation_ids=tuple(sorted(
                                native_phase_ids-recorded_phase_ids)),
                            missing_situation_ids=tuple(sorted(
                                recorded_phase_ids-native_phase_ids)))
        if any(status!='verified' for status,_ in statuses):
            return _blocked('NATIVE_EA_JOBS_PENDING_OR_REJECTED',
                            phase_situation_states=tuple(statuses))
        if not statuses:
            return _blocked('NO_NATIVE_EA_LESSON_SITUATIONS')
        actual_all=seen[1]|seen[2]|player
        expected1=set(canonical['classes'][0])-player
        expected2=set(canonical['classes'][1])-player
        if (seen[1]!=expected1 or seen[2]!=expected2
                or seen[1]&seen[2] or actual_all!=set(canonical['all_16'])):
            return _blocked(
                'CLASS_JOB_DISTRIBUTION_MISMATCH',
                class1_npcs_matched=len(seen[1]&expected1),
                class2_npcs_matched=len(seen[2]&expected2),
                missing_enrolled_ids=tuple(sorted(
                    set(canonical['all_16'])-actual_all)))
        return {
            'status':'EXACT_NATIVE_16_STUDENTS_ASSIGNED_NOT_SEATED',
            'phase_key':phase_key,
            'native_school_phase':WINDOWS[phase_key[3]],
            'actual_students':16,
            'class1_registered':8,
            'class2_registered':8,
            'class1_native_npc_members':len(seen[1]),
            'class2_native_npc_members':len(seen[2]),
            'registered_playables_in_ea_school_jobs':3,
            'additional_zone_teens_not_enrolled':tuple(
                sorted(zone-set(canonical['all_16']))),
            'native_ea_16_student_membership_verified':True,
            'exact_class_ea_jobs_verified':True,
            'class_8_plus_8_seating_verified':False,
            'full_school_day_verified':False,
            'game_modified':False,
        }
    except (ValueError,TypeError,KeyError,AttributeError,InvitationPlanError):
        return _blocked('NATIVE_SCHOOL_OBSERVATION_UNAVAILABLE')
