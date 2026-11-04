"""Verify six EA school SituationJob TUNING XMLs, not their SimData exports.

This tool only validates the source type and ID before further review.
A valid EA XML still does not imply compatibility or a safe 16-student build.

Run: python -m tooling.verify_ea_school_jobs /path/to/exported_xml_folder
"""
from pathlib import Path
import argparse
import json
import re
import xml.etree.ElementTree as ET

REQUIRED = {
    277894: "job_HighSchool_Active_Base_NPC_Student",
    278965: "job_HighSchool_Active_Base_NPC_Student_CheerTeam",
    278966: "job_HighSchool_Active_Base_NPC_Student_ChessTeam",
    278967: "job_HighSchool_Active_Base_NPC_Student_FootballTeam",
    278968: "job_HighSchool_Active_Base_NPC_Student_ComputerTeam",
    303765: "job_HighSchool_Active_Base_NPC_Student_MeanSim",
}
TUNING_TYPE = "9C07855F"
SIMDATA_TYPE = "545AC67A"

def inspect_xml(text, filename=""):
    try:
        root = ET.fromstring(text)
    except (ET.ParseError, TypeError):
        return {"status":"BLOCKED","reason":"INVALID_XML","filename":filename}
    if root.tag == "SimData" or SIMDATA_TYPE in filename.upper():
        return {"status":"BLOCKED","reason":"SIMDATA_NOT_TUNING","filename":filename}
    if root.tag != "I":
        return {"status":"BLOCKED","reason":"NOT_EA_TUNING","filename":filename}
    try:
        iid = int(root.get("s", ""))
    except ValueError:
        return {"status":"BLOCKED","reason":"MISSING_INSTANCE_ID","filename":filename}
    if iid not in REQUIRED or root.get("n") != REQUIRED[iid]:
        return {"status":"BLOCKED","reason":"WRONG_SCHOOL_JOB","filename":filename}
    # A filename beginning with a resource key must name a SituationJob.
    prefix = filename.split("!",1)[0].upper() if "!" in filename else ""
    if prefix and prefix != TUNING_TYPE:
        return {"status":"BLOCKED","reason":"WRONG_TGI_TYPE","filename":filename}
    # Filter and invitation fields will be reviewed against each original file;
    # do NOT invent missing values or assume these are present in SimData.
    filter_names = sorted(set(e.attrib.get("n","")
        for e in root.iter()
        if ("filter" in e.attrib.get("n","").lower()
            or "sim_auto_invite" in e.attrib.get("n","").lower())))
    return {"status":"TUNING_XML_RECEIVED_NOT_GAME_VALIDATED","instance":iid,
            "name":root.get("n"),"filter_or_invite_nodes":filter_names,
            "filename":filename}

def verify_folder(folder):
    reports=[]
    for path in sorted(Path(folder).glob("*.xml")):
        reports.append(inspect_xml(path.read_text(encoding="utf-8-sig"),
                                   path.name))
    seen = [r.get("instance") for r in reports if r["status"].startswith("TUNING_")]
    status=("SIX_JOB_TUNINGS_READY_FOR_REVIEW"
            if len(reports)==6 and set(seen)==set(REQUIRED) and len(set(seen))==6
            else "BLOCKED")
    return {"status":status,"reports":reports}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder")
    args=ap.parse_args()
    result=verify_folder(args.folder)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result["status"]=="SIX_JOB_TUNINGS_READY_FOR_REVIEW" else 1

if __name__ == "__main__":
    raise SystemExit(main())
