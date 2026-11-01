"""MHS integrated M85 + EA school capacity pilot for Sims 4 Mac.

Uses nine original current EA tuning XMLs supplied by the user.
Patch exactly two Base NPC situation upper counts (6 -> 16) and four
classroom phase student job upper counts (6 -> 8). This is NOT a
completed 16-registered-student dispatcher: the six-to-sixteen change is
a ceiling, not a guarantee, and EA can still select random classmates.
"""
import hashlib
import json
import py_compile
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

from tooling.build_m55_attendance_trial import package_bytes
from tooling.build_m58_diagnostic import SCRIPTS
from tooling.simdata_release_gate import resources, inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'/'ea_2026_11_01'
ENTRY=struct.Struct('<IIIIIIIHH')
SNIPPET=0x7DF2169C
GROUP=0x35
SCHEDULES=(277657,279958)
PHASES=(293642,293644,304561,304563)
ALREADY_EIGHT=(297773,304570)
PACKAGE='MHS_M85_CAPIENZA_8X8_MAC_BETA.package'
SCRIPT='MHS_M85_CAPIENZA_8X8_MAC_BETA.ts4script'

def _value(element):
    return '' if element is None or element.text is None else element.text.strip()

def _original(iid,expected):
    root=ET.fromstring((ASSETS/(str(iid)+'.xml')).read_bytes())
    if root.get('s')!=str(iid) or root.get('c')!=expected:
        raise ValueError('EA tuning mismatch for '+str(iid))
    return root

def capacity_resources():
    records=[]
    for iid in SCHEDULES:
        root=_original(iid,'WeeklyScheduleDay')
        matched=[]
        for entry in root.findall('./L[@n="long_term_situations"]/U'):
            if _value(entry.find('./T[@n="situation"]'))!='277733':
                continue
            low=entry.find('./U[@n="count"]/T[@n="lower_bound"]')
            high=entry.find('./U[@n="count"]/T[@n="upper_bound"]')
            if _value(low)!='6' or _value(high)!='6':
                raise ValueError('EA school count no longer matches original')
            high.text='16'
            matched.append(entry)
        if len(matched)!=1:
            raise ValueError('Expected exactly one Base Student situation')
        records.append((SNIPPET,GROUP,iid,ET.tostring(root,encoding='utf-8')))
    for iid in PHASES:
        root=_original(iid,'WeeklyScheduleSituationData')
        matched=[]
        for job in root.findall('./L[@n="job_assignments"]/U'):
            if _value(job.find('./T[@n="job"]'))!='277919':
                continue
            upper=job.find('./U[@n="sim_count"]/T[@n="upper_bound"]')
            if _value(upper)!='6':
                raise ValueError('EA student classroom count changed')
            upper.text='8'
            matched.append(job)
        if len(matched)!=1:
            raise ValueError('Expected exactly one Class1 student job')
        records.append((SNIPPET,GROUP,iid,ET.tostring(root,encoding='utf-8')))
    for iid,job_id in ((297773,'277919'),(304570,'280777')):
        root=_original(iid,'WeeklyScheduleSituationData')
        selected=[j for j in root.findall('./L[@n="job_assignments"]/U')
                  if _value(j.find('./T[@n="job"]'))==job_id]
        if len(selected)!=1 or _value(selected[0].find(
                './U[@n="sim_count"]/T[@n="upper_bound"]'))!='8':
            raise ValueError('Other class capacity no longer eight')
    core=_original(298052,'CustomStatesSituation')
    default_core_jobs=[_value(x) for x in core.findall(
        './L[@n="default_job_and_roles"]/U/T[@n="Situation Job"]')]
    state_core_jobs=[_value(x) for x in core.findall(
        './L[@n="_situation_states"]/U/V[@n="Situation State"]/'
        'U[@n="literal"]/L[@n="job_and_role_changes"]/U/'
        'T[@n="Situation Job"]')]
    # Default list has 2 teachers + 5 possible student jobs.
    # NoBehavior changes include 2 teachers + 4 student jobs.
    # These are possible roles, not an observed headcount in the save.
    if default_core_jobs!=['277895','278963','278965','278966',
                           '278967','278968','303765']:
        raise ValueError('EA core teachers or student roles changed')
    if state_core_jobs!=['277895','278963','278965','278966',
                         '278967','278968']:
        raise ValueError('EA Core NoBehavior role mapping changed')
    if _value(core.find('./T[@n="max_participants"]'))!='20':
        raise ValueError('EA core max participants changed')
    base=_original(277733,'CustomStatesSituation')
    if _value(base.find('./T[@n="max_participants"]'))!='20':
        raise ValueError('Base situation max participants changed')
    if len(records)!=6 or len(set(r[:3] for r in records))!=6:
        raise ValueError('Unexpected tuning resource count')
    return records

def _assemble(records,header):
    hdr=bytearray(header[:96])
    data=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,raw in records:
        compressed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
            96+len(data),len(compressed)|0x80000000,len(raw),0x5A42,1))
        data.extend(compressed)
    struct.pack_into('<I',hdr,0x24,len(records))
    struct.pack_into('<I',hdr,0x28,0)
    struct.pack_into('<I',hdr,0x2c,len(index))
    struct.pack_into('<Q',hdr,0x40,96+len(data))
    return bytes(hdr+data+index)

def combined_package():
    base=package_bytes()
    old=resources(base)
    if len(old)!=63:
        raise ValueError('M85 original resource count changed')
    add=capacity_resources()
    seen=set(x[:3] for x in old)
    if any(r[:3] in seen for r in add):
        raise ValueError('EA tuning overlaps M85 resource')
    expected=old+add
    result=_assemble(expected,base)
    if resources(result)!=expected:
        raise ValueError('DBPF roundtrip failed')
    report=inspect_bytes(result)
    if report['status']!='STATIC_GATE_PASSED' or report['resource_count']!=69:
        raise ValueError('M85 menu structural regression')
    return result

def release(directory):
    if sys.version_info[:2]!=(3,7):
        raise RuntimeError('The Sims 4 script bytecode requires Python 3.7')
    if len(SCRIPTS)!=32:
        raise ValueError('M85 script count changed')
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    blob=combined_package()
    (directory/PACKAGE).write_bytes(blob)
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(str(directory/SCRIPT),'w',zipfile.ZIP_DEFLATED) as z:
            for src in SCRIPTS:
                compiled=Path(temp)/(src.name+'c')
                py_compile.compile(str(src),cfile=str(compiled),doraise=True)
                z.write(str(compiled),arcname=src.name+'c')
    status={'status':'CAPACITY_PILOT_NOT_COMPLETE_16_ROSTER_MOD',
            'resources':69,'preserved_M85_resources':63,'EA_capacity_overrides':6,
            'M85_script_modules':32,'EA_Base_NPC_min':6,'EA_Base_NPC_max':16,
            'EA_Class1_phase_max':8,
            'registered_16_attendance_implemented':False,
            'EA_random_students_still_possible':True,
            'test_only_on_a_copy_of_save':True,
            'sha256_package':hashlib.sha256(blob).hexdigest()}
    (directory/'MHS_CAPACITY_BETA_AUDIT.json').write_text(
        json.dumps(status,indent=2,sort_keys=True))
    return status

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_mhs_capacity_beta dist/')
    print(json.dumps(release(sys.argv[1]),indent=2))
