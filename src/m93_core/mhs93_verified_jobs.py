"""Verified current-EA School SituationJob tuning facts from user ZIP.

This module DOES NOT hook, edit, or override EA situations. Only 4 of 6
original SituationJob Tuning XMLs were included in MHS SCUOLA.zip.
Do not infer ChessTeam or FootballTeam filters from nearby numeric IDs.
"""
ORDINARY_JOB=277894
CORE_STUDENT_JOBS=frozenset((278965,278966,278967,278968,303765))
TEACHER_JOBS=frozenset((277895,278963))

# (EA filter GUID, automatic minimum, automatic maximum, allow instantiated Sims)
VERIFIED_SPECS={
    277894:(280516,1,1,True),   # Ordinary pupil
    278965:(276592,1,1,True),   # Cheerleader
    278968:(276595,1,1,True),   # Computer team
    303765:(303766,1,1,True),   # Mean Sim
}
PENDING_TUNING=frozenset((278966,278967))   # Chess / football

def classify_job(job_id):
    if type(job_id) is not int:
        return 'unknown'
    if job_id in TEACHER_JOBS:
        return 'staff'
    if job_id in CORE_STUDENT_JOBS:
        return 'core'
    if job_id==ORDINARY_JOB:
        return 'base'
    return 'unknown'

def core_filter_specs_ready():
    """A false result prohibits a full-coverage core filter adapter."""
    return CORE_STUDENT_JOBS.issubset(VERIFIED_SPECS)

def verify_complete_core_jobs(specs):
    """Require every EA core filter known; never fill missing ones by guess."""
    if not isinstance(specs,dict):
        return False
    if set(specs)!=set(VERIFIED_SPECS)|PENDING_TUNING:
        return False
    for job,(guid,low,high,instanced) in specs.items():
        if type(job) is not int or type(guid) is not int or guid<=0:
            return False
        if low!=1 or high!=1 or instanced is not True:
            return False
        if job in VERIFIED_SPECS and (guid,low,high,instanced)!=VERIFIED_SPECS[job]:
            return False
    return True
