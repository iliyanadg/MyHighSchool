"""M94: read-only live EA high-school job tuning introspection.

Do not guess Chess/Football SimFilter IDs. This module reads the exact
SituationJob objects registered by the installed The Sims 4 and writes
only job/filter configuration. Never alters filtering, invitations or saves.
"""
import json
import os

JOBS=((277894,"Base Student"),(278965,"Cheer"),(278966,"Chess"),
      (278967,"Football"),(278968,"Computer"),(303765,"Mean Sim"))
REPORT_NAME="MHS_M94_FILTRI_LICEO_EA.json"

def _guid(value):
    if value is None or isinstance(value,bool):
        return None
    for x in (value,getattr(value,"tuned_class",None),type(value)):
        if x is None:
            continue
        try:
            guid=getattr(x,"guid64",None)
            if guid is not None:
                number=int(guid)
                return number if number>0 else None
        except (AttributeError,ValueError,TypeError):
            continue
    return None

def snapshot(get_job):
    """get_job(EA job instance ID) supplied by live manager or offline test."""
    output=[]
    for iid,name in JOBS:
        item={"job_id":iid,"name":name}
        try:
            job=get_job(iid)
            if job is None:
                item["status"]="JOB_NOT_FOUND"
            elif _guid(job) not in (None,iid):
                item["status"]="JOB_ID_MISMATCH"
            else:
                filt=getattr(job,"filter",None)
                fid=_guid(filt)
                auto=getattr(job,"sim_auto_invite",None)
                lower=getattr(auto,"lower_bound",None)
                upper=getattr(auto,"upper_bound",None)
                allow=getattr(job,"sim_auto_invite_allow_instanced_sim",None)
                item.update({
                    "status":"OBSERVED",
                    "filter_guid":fid,
                    "auto_min":lower if type(lower) is int else None,
                    "auto_max":upper if type(upper) is int else None,
                    "allow_instanced":allow if type(allow) is bool else None,
                })
        except Exception as exc:
            item["status"]="ERROR_"+type(exc).__name__
        output.append(item)
    verified=sum(1 for job in output if job.get("status")=="OBSERVED"
                 and job.get("filter_guid") is not None)
    return {"kind":"LIVE_EA_SITUATION_JOB_TUNING_READ_ONLY",
            "filter_guids_observed":verified,
            "expected_jobs":len(JOBS),
            "jobs":output,
            "does_not_verify_16_student_attendance":True}

def live_snapshot():
    """Never import EA services in unit tests or before user clicks the menu."""
    import services
    from sims4.resources import Types
    manager=services.get_instance_manager(Types.SITUATION_JOB)
    if manager is None:
        return {"kind":"LIVE_EA_SITUATION_JOB_TUNING_READ_ONLY",
                "error":"EA_JOB_MANAGER_NOT_READY",
                "filter_guids_observed":0,"expected_jobs":len(JOBS),
                "jobs":[],"does_not_verify_16_student_attendance":True}
    return snapshot(manager.get)

def capture_report(folder):
    report=live_snapshot()
    if not folder:
        return report
    os.makedirs(folder,exist_ok=True)
    path=os.path.join(folder,REPORT_NAME)
    temp=path+".tmp"
    with open(temp,"w",encoding="utf-8") as f:
        json.dump(report,f,indent=2,sort_keys=True)
    os.replace(temp,path)
    return report

def summary_line(report):
    return ("M94 filtri EA: {}/{} letti; {}".format(
        report.get("filter_guids_observed",0),
        report.get("expected_jobs",len(JOBS)),
        REPORT_NAME if report.get("jobs") else
        report.get("error","lettura indisponibile")))
