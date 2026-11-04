"""Six school SituationJob tunings observed in a real The Sims 4 Mac run.

Source: user-provided MHS_M94_FILTRI_LICEO_EA.json (2026-11-01).
This is verified EA metadata, NOT proof of 16 physical school attendees.
Never treat M94 observed filter GUIDs as proof that core school NPCs are
already the registered students. No EA hooks or changes are made here.
"""
ORDINARY_JOB=277894
CORE_STUDENT_JOBS=frozenset((278965,278966,278967,278968,303765))
TEACHER_JOBS=frozenset((277895,278963))

# EA SituationJob GUID -> (EA SimFilter GUID, min auto, max auto, allow instanced)
# Chess (278966) and Football (278967) come from the ACTUAL M94 report,
# not inferred from adjacent resources. Earlier test mocks had these reversed.
VERIFIED_SPECS={
    277894:(280516,1,1,True),   # Ordinary student
    278965:(276592,1,1,True),   # Cheerleader
    278966:(276596,1,1,True),   # Chess team
    278967:(276594,1,1,True),   # Football team
    278968:(276595,1,1,True),   # Computer team
    303765:(303766,1,1,True),   # Mean Sim
}
PENDING_TUNING=frozenset()  # The actual game has now verified all six.

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
    """True means metadata known; NOT permission to activate M89."""
    return CORE_STUDENT_JOBS.issubset(VERIFIED_SPECS)

def verify_complete_core_jobs(specs):
    """Six identical EA tuning specs, fail closed if one is changed."""
    if not isinstance(specs,dict) or set(specs)!=set(VERIFIED_SPECS):
        return False
    for job,expected in VERIFIED_SPECS.items():
        values=specs[job]
        if not isinstance(values,(tuple,list)) or len(values)!=4:
            return False
        if any(type(values[n]) is not int for n in range(3)):
            return False
        if type(values[3]) is not bool:
            return False
        if tuple(values)!=expected:
            return False
    return True

def verify_m94_snapshot(report):
    """Validate every observed field in the user's live game report.

    Useful for checking a changed game patch before enabling any future
    high-school selector. It is NOT an active attendance or seat audit.
    """
    if not isinstance(report,dict):
        return False
    if (report.get('kind')!='LIVE_EA_SITUATION_JOB_TUNING_READ_ONLY'
            or report.get('filter_guids_observed')!=6
            or report.get('expected_jobs')!=6):
        return False
    rows=report.get('jobs')
    if not isinstance(rows,list) or len(rows)!=6:
        return False
    actual={}
    for row in rows:
        if not isinstance(row,dict) or row.get('status')!='OBSERVED':
            return False
        job=row.get('job_id')
        if type(job) is not int or job in actual:
            return False
        actual[job]=(row.get('filter_guid'),row.get('auto_min'),
                     row.get('auto_max'),row.get('allow_instanced'))
    return verify_complete_core_jobs(actual)
