"""M118: admission first, lessons ONLY after independent job verification.

An OFFLINE coordination contract. The morning stage graph contains just:
- original native precreate (M112)
- school-only Bouncer filter (M114/M115)
- no-show replacement guard (M114)
- original EA post-spinup 13-NPC reader (M117)

The existing M113 graph formerly required unified_lessons before the
Bouncer could verify school arrival. M118 separates the phase graph
rather than setting 'full_16_school_day_ea_membership_verified=True'
before the original EA Bouncer has done anything.

No automatic hooks, no invented live-proof flags. The 13-NPC job report
and a separately observed same-save/day/zone 3-playable snapshot must
both match before a LESSON PREFLIGHT can begin. The actual M108
unified lesson class-1 shadow + post-phase Bouncer barriers still need
independent game verification, and no class attendance is claimed here.
"""
from mhs108_native_invitation import SchoolNativeGuestSession
from mhs114_school_bouncer_pair import M114SchoolBouncerPair
from mhs117_post_spinup_admission import M117PostSpinupAdmission

ADMISSION_STAGE_ORDER = (
    'native_precreate', 'school_filter_scope',
    'no_show_guard', 'post_bouncer_observer',
)
LESSON_STAGE_ORDER = ('unified_lessons',)


def build_morning_admission_stages(native_precreate, bouncer_pair,
                                   post_spinup):
    """Require real prepared stage dicts; never make placeholder hooks."""
    if (not isinstance(native_precreate,dict)
            or not isinstance(bouncer_pair,M114SchoolBouncerPair)
            or not isinstance(post_spinup,M117PostSpinupAdmission)):
        return None
    if (set(native_precreate) != {'install','restore'}
            or not callable(native_precreate['install'])
            or not callable(native_precreate['restore'])):
        return None
    if bouncer_pair._stages is None:
        return None
    filter_stages = {name:stage.as_stage()
                     for name,stage in bouncer_pair._stages.items()}
    if set(filter_stages) != {'school_filter_scope','no_show_guard'}:
        return None
    # An M117 staged installation is supplied externally only with
    # original-EA provenance evidence and verified native owner.
    if post_spinup.state != 'NOT_INSTALLED':
        return None
    return {'native_precreate':native_precreate,
            'school_filter_scope':filter_stages['school_filter_scope'],
            'no_show_guard':filter_stages['no_show_guard']}


def _canonical_sid(value):
    if type(value) not in (str,int):
        return None
    sid=str(value)
    if (not sid.isdigit() or int(sid)<=0
            or str(int(sid))!=sid):
        return None
    return sid


def inspect_lesson_admission_gate(session, spinup_report, playable_snapshot):
    """Read-only preflight: 13 NPC jobs plus 3 actual playable instances.

    The playable snapshot must have been generated from live SimInfo
    instances scoped to the *same* save/day/zone, not from the enrolled
    registry alone. Even on success this is NOT evidence the lesson
    situation jobs or classroom seating have been routed.
    """
    result={
        'kind':'M118_LESSON_PREFLIGHT_AFTER_NATIVE_ADMISSION',
        'status':'ADMISSION_NOT_VERIFIED',
        'game_modified':False,
        'morning_native_job_receipts_sufficient':False,
        'all_3_playables_on_school_zone_verified':False,
        'lesson_stage_install_authorized':False,
        'late_lesson_bouncer_barrier_verified':False,
        'classroom_1_and_2_job_assignment_verified':False,
        'seating_verified':False,
        'full_school_day_verified':False,
    }
    if not isinstance(session,SchoolNativeGuestSession):
        result['status']='MHS_NATIVE_INVITATION_SESSION_MISSING'
        return result
    if not isinstance(spinup_report,dict):
        result['status']='NO_ORIGINAL_EA_POST_SPINUP_REPORT'
        return result
    if (spinup_report.get('status')!='NATIVE_GUEST_JOBS_MATCH_OBSERVED'
            or spinup_report.get('native_guest_jobs_13_verified_in_snapshot')
                is not True
            or spinup_report.get('post_bouncer_callback_provenance_verified')
                is not True
            or spinup_report.get('post_bouncer_provenance_scope')
                != 'ORIGINAL_EA_ZONE_SPINUP_ONLY'
            or spinup_report.get('number_original_native_situations_found')!=9
            or spinup_report.get('enrolled_npc_job_ids_observed')!=13):
        result['status']='THIRTEEN_NPC_NATIVE_EA_JOB_RECEIPTS_MISMATCH'
        return result
    result['morning_native_job_receipts_sufficient']=True
    if type(playable_snapshot) is not dict:
        result['status']='NO_PLAYABLE_LIVE_ZONE_SNAPSHOT'
        return result
    manifest=session.manifest
    if (playable_snapshot.get('source')
            != 'EA_SIM_INFO_MANAGER_LIVE_INSTANCES'
            or str(playable_snapshot.get('save_slot'))
                != manifest['save_slot']
            or type(playable_snapshot.get('sim_day')) is not int
            or playable_snapshot.get('sim_day')!=manifest['sim_day']
            or str(playable_snapshot.get('school_zone'))
                != manifest['school_zone']):
        result['status']='PLAYABLE_ZONE_OR_SAVE_MISMATCH'
        return result
    raw=playable_snapshot.get('playable_present_ids')
    if (type(raw) not in (tuple,list)
            or len(raw)!=3
            or any(_canonical_sid(sid) is None for sid in raw)
            or set(map(str,raw))!=set(manifest['playable'])):
        result['status']='THREE_PLAYABLE_EA_ZONE_MEMBERS_MISMATCH'
        return result
    if playable_snapshot.get('all_instances_on_current_school_zone') is not True:
        result['status']='PLAYABLE_INSTANCE_ZONE_NOT_VERIFIED'
        return result
    result['status']='MORNING_ADMISSION_16_OBSERVED_LESSONS_STILL_GATED'
    result['all_3_playables_on_school_zone_verified']=True
    # M108 UnifiedLessons additionally requires independent original
    # late classroom callbacks and multiple unproven native gates.
    result['lesson_stage_install_authorized']=False
    return result
