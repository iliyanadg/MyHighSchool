"""M152: reduce repeated EA staff/venue scans without changing school work.

MHS lesson alarms keep their established three-minute cadence. Staff
reconciliation scans are expensive: selected staff situation memberships and
up to 2000 school objects/cafeteria station tunings are examined. This helper
throttles only that read-heavy scan, never the initial EA invitation schedule,
native class activity, cap guard, school-day resets or staff projections.
Python 3.7, pure, deterministic, no game imports.
"""
SIM_TICKS_PER_MINUTE=1500
STAFF_RESCAN_SIM_MINUTES=12


def should_scan_supplemental_staff(now_ticks,last_scan_ticks,minutes=STAFF_RESCAN_SIM_MINUTES):
    """True for first eligible time or >=interval since the prior full scan.

    This function is called only after the existing 09:40--11:30 EA staff
    window check. Bad clocks don't authorize expensive or unsafe work.
    A time rewind is allowed to scan; runtime's day-reset also clears the
    prior marker. Does not depend on displayed UI time.
    """
    if type(now_ticks) is not int or now_ticks<0:
        return False
    if last_scan_ticks is None:
        return True
    if type(last_scan_ticks) is not int or last_scan_ticks<0:
        return False
    if now_ticks<last_scan_ticks:
        return True
    if type(minutes) is not int or minutes<1:
        return False
    return now_ticks-last_scan_ticks>=minutes*SIM_TICKS_PER_MINUTE
