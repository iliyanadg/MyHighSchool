"""M125 tightly bounded opt-in EA lesson interaction recovery.

This is an actual interaction intervention, not a seat/spawn/teleport.
Verified from EA original base_situation.py: FinishingType.SITUATIONS
and interaction.cancel(finishing_type, reason). Cancels ONLY the exact
observed non-school mirror interaction, once per enrolled nonplayable
teen per school session and only with correct native EA lesson job.
No auto-repeat, no autonomous queue manipulation, no claimed resit.
"""
from mhs122_classroom_job_readback import LESSON_SITUATIONS

OFF_TASK_ALLOWED=frozenset((
    'sims4.tuning.instances.mirror_ResearchDebateSkill_Practice',
))


def _guid(value):
    if value is None:
        return None
    for x in (value,getattr(value,'tuned_class',None),type(value)):
        guid=getattr(x,'guid64',None)
        if type(guid) is int and guid>0:
            return guid
    return None


def interaction_name(value):
    if value is None:
        return 'NONE'
    t=type(value)
    return getattr(t,'__module__','')+'.'+getattr(t,'__name__','')


def inspect_candidate(sid,klass,info,sim,situation_manager,
                      age,species,already_attempted):
    """Return (eligible,reason,interaction) without mutating Sim."""
    sid=str(sid)
    if sid in already_attempted:
        return False,'ALREADY_ATTEMPTED',None
    if (info is None or getattr(info,'age',None)!=age
            or getattr(info,'species',None)!=species):
        return False,'NOT_HUMAN_TEEN',None
    if getattr(info,'is_selectable',True) is not False:
        return False,'PLAYABLE_PROTECTED',None
    if sim is None:
        return False,'NOT_INSTANCED',None
    queue=getattr(sim,'queue',None)
    running=getattr(queue,'running',None)
    if running is None:
        return False,'NOT_RUNNING',None
    current=interaction_name(running)
    if current not in OFF_TASK_ALLOWED:
        return False,'NOT_ALLOWLISTED_'+current[-90:],None
    try:
        situation_list=tuple(
            situation_manager.get_situations_sim_is_in(sim))
        matching=[]
        for situation in situation_list:
            guid=_guid(situation)
            expected=LESSON_SITUATIONS.get(guid)
            if expected is None:
                continue
            job=_guid(situation.get_current_job_for_sim(sim))
            matching.append((expected,job))
        if (len(matching)!=1 or matching[0][0][0]!=klass
                or matching[0][0][1]!=matching[0][1]):
            return False,'NATIVE_LESSON_JOB_UNVERIFIED',None
    except Exception:
        return False,'EA_MEMBERSHIP_READ_FAILED',None
    if not callable(getattr(running,'cancel',None)):
        return False,'EA_CANCEL_API_UNAVAILABLE',None
    return True,'ELIGIBLE_OFF_TASK_MIRROR',running


def recover_one(sid,klass,info,sim,situation_manager,age,species,
                attempted,finish_type):
    eligible,reason,interaction=inspect_candidate(
        sid,klass,info,sim,situation_manager,age,species,attempted)
    if not eligible:
        return False,reason
    # A failed attempt is not retried during the same school session:
    # prevent cancellation loops and hidden interruptions.
    attempted.add(str(sid))
    try:
        interaction.cancel(
            finish_type,
            'MY HIGH SCHOOL M125: recover NPC from non-school mirror action')
        return True,'EA_MIRROR_CANCEL_CALLED_CLASS_NOT_YET_VERIFIED'
    except Exception as exc:
        return False,'EA_CANCEL_FAILED_'+type(exc).__name__
