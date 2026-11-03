"""M113 original EA guest/job source for the 3 playable + 5 Core + 8 Base.

This is a REAL GAME SERVICE READER, with imports delayed to invocation.
Resolves six specific EA SituationJob tunings and EA SituationGuestInfo,
then hands those objects to the existing M108 immutable guest session.
Never creates a situation, changes EA tuning or writes a registry.

Real object lookup alone cannot certify the native Bouncer filter or
role acceptance; the early school callback must still be independently
verified before ANY hook is installed.
"""
from mhs108_native_invitation import (
    BASE_JOB, CORE_JOBS, SchoolNativeGuestSession, InvitationPlanError,
)

EXPECTED_JOBS = (BASE_JOB,) + CORE_JOBS


def make_native_guest_session(manifest):
    """Return (session, reason) after validating actual EA tuned job objects.

    Designed for M113EarlySchoolEntry.session_factory: the caller may
    intentionally return session and record a refusal separately.
    """
    if (not isinstance(manifest,dict) or manifest.get('status')!=
            'M108_INVITATIONS_PREPARED_NOT_GAME_AUTHORIZED'):
        return None,'UNVERIFIED_M108_MANIFEST'
    try:
        import services
        from sims4.resources import Types
        from situations.situation_guest_list import (
            SituationGuestInfo, SituationInvitationPurpose,
        )
        manager = services.get_instance_manager(Types.SITUATION_JOB)
        if manager is None:
            return None,'EA_SITUATION_JOB_MANAGER_MISSING'
        purpose=getattr(SituationInvitationPurpose,'INVITED',None)
        constructor=getattr(SituationGuestInfo,
                            'construct_from_purpose',None)
        if purpose is None or not callable(constructor):
            return None,'EA_INVITATION_CONSTRUCTOR_MISSING'
        jobs={}
        for job_id in EXPECTED_JOBS:
            job=manager.get(job_id)
            if job is None or getattr(job,'guid64',None)!=job_id:
                return None,'EA_ORIGINAL_STUDENT_JOB_MISSING_'+str(job_id)
            jobs[job_id]=job
        result=SchoolNativeGuestSession(
            manifest,SituationGuestInfo,purpose,jobs)
        return result,'EA_JOB_OBJECTS_RESOLVED_NOT_BOUNCER_VERIFIED'
    except (ImportError,AttributeError,TypeError,ValueError,
            InvitationPlanError) as exc:
        return None,'EA_JOB_READ_ERROR_'+type(exc).__name__
    except Exception as exc:
        # Unknown EA service failures are a blocked condition, never
        # an excuse to run the hook with guessed job objects.
        return None,'EA_JOB_SERVICE_FAILED_'+type(exc).__name__


def native_guest_session_factory(manifest):
    """Exact callback shape consumed by M113EarlySchoolEntry."""
    result,reason=make_native_guest_session(manifest)
    return result
