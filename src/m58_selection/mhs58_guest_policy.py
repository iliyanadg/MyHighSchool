"""M58 pure EA guest-list decision policy; no hooks or mutations."""
BASE_STUDENT=277733
CORE=298052
VENUE=298096
BASE_STUDENT_JOB=277894


def classify_situation(guid):
    try:
        key=int(guid)
    except (TypeError,ValueError):
        return None
    return {BASE_STUDENT:'student',CORE:'core',VENUE:'venue'}.get(key)


def guest_list_decision(situation_guid, job_guests, planned_ids,
                        verified_school_zone=False, active=True):
    """Read-only gate before any future live adapter.

    job_guests are (job GUID, sim id) tuples from EA SituationGuestList.
    Sim ID zero represents no explicit invitee. Never rewrite EA's core,
    staff or already-explicit invited guests.
    """
    kind=classify_situation(situation_guid)
    if not active or not verified_school_zone or kind is None:
        return {'action':'preserve','reason':'not verified active school'}
    if kind!='student':
        return {'action':'preserve','reason':'core and venue remain EA owned'}
    guests=tuple((int(job),int(sid)) for job,sid in job_guests)
    if not guests:
        return {'action':'observe','reason':'no explicit guest list'}
    if any(job!=BASE_STUDENT_JOB for job,_ in guests):
        return {'action':'preserve','reason':'unexpected job'}
    if any(sid for _,sid in guests):
        return {'action':'preserve','reason':'EA explicit guest'}
    ids=tuple(str(x) for x in planned_ids)
    if len(guests)!=1:
        return {'action':'preserve','reason':'unexpected number of base job guests'}
    if len(ids)!=1:
        return {'action':'preserve','reason':'requires exactly one verified candidate'}
    if not ids[0].isdigit() or int(ids[0])<1 or str(int(ids[0]))!=ids[0]:
        return {'action':'preserve','reason':'invalid candidate Sim ID'}
    return {'action':'candidate','candidate_count':1}
