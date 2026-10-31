"""M48 one-package native enrollment experiment built ON verified M45 menu.

Modifies exactly the three "Prepara iscrizione" affordance tuning XMLs,
converting them from SimPickerInteraction to ImmediateSuperInteraction
compatible with mhs48_single_picker._EnrollmentAction. The native SimPicker checkmark immediately saves the validated batch;
X closes without modifying the registry. There is no second dialog. The other 32 DBPF resources are unchanged.

Existing M45 class categories, four Lot51 child SimData, all category
parents and activation/visibility logic are untouched. Python 3.7 required.
This is a Mac in-game TEST build, not evidence that EA attendance works.
"""
import hashlib
import importlib.util
import json
import py_compile
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

from tooling.build_m45_visibility_complete import (
    package_bytes as build_m45,ENROLL_IDS,CATEGORY_IDS)
from tooling.build_m27_removal import TYPE_INTERACTION,ENTRY,IDS as REMOVE_IDS
from tooling.build_m34_settings import SCRIPTS as M34_SCRIPTS
from tooling.build_m39_conditional_menu import RULES,UI
from tooling.simdata_release_gate import resources,inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
TXN=ROOT/'src'/'m2_registry'/'mhs46_enrollment_transaction.py'
ENROLL_UI=ROOT/'src'/'m48_enrollment'/'mhs48_single_picker.py'
SCRIPTS=tuple(M34_SCRIPTS)+(RULES,UI,TXN,ENROLL_UI)
PACKAGE='MHS_M48_ISCRIZIONE_SPUNTA_UNICA_TEST.package'
SCRIPT='MHS_M48_ISCRIZIONE_SPUNTA_UNICA_TEST.ts4script'


class M48BuildError(ValueError):
    pass


def _replace_picker(raw,template,klass):
    root=ET.fromstring(raw)
    base=ET.fromstring(template)
    if (root.get('c')!='MHS45ChooseClass{}'.format(klass)
            or root.get('m')!='mhs39_visibility_ui'):
        raise M48BuildError('Unexpected M45 picker class')
    if (base.get('m')!='mhs39_visibility_ui'
            or base.get('c')!='MHS39_MHS27RemoveClass1'):
        raise M48BuildError('Unexpected M45 immediate interaction template')
    name=root.get('n')
    iid=root.get('s')
    title=root.find('./T[@n="display_name"]')
    category=root.find('./T[@n="category"]')
    if (title is None or category is None or
            category.text!=str(CATEGORY_IDS[klass-1])):
        raise M48BuildError('Missing original picker name/category')
    base.set('m','mhs48_single_picker')
    base.set('c','MHS47EnrollClass{}'.format(klass))
    base.set('n',name)
    base.set('s',iid)
    base.find('./T[@n="category"]').text=category.text
    base.find('./T[@n="display_name"]').text=title.text
    return ET.tostring(base,encoding='utf-8')


def transformed_resources():
    original=resources(build_m45())
    templates={iid:raw for typ,g,iid,raw in original
               if typ==TYPE_INTERACTION and iid in REMOVE_IDS}
    if len(templates)!=2:
        raise M48BuildError('Missing established M27 immediate interaction template')
    template=templates[REMOVE_IDS[0]]
    changed=set()
    entries=[]
    for typ,g,iid,raw in original:
        if typ==TYPE_INTERACTION and iid in ENROLL_IDS:
            klass=ENROLL_IDS.index(iid)+1
            raw=_replace_picker(raw,template,klass)
            changed.add(iid)
        entries.append((typ,g,iid,raw))
    if len(entries)!=35 or changed!=set(ENROLL_IDS):
        raise M48BuildError('Expected three and only three new enrollment affordances')
    for old,new in zip(original,entries):
        if old[:3]!=new[:3]:
            raise M48BuildError('Resource key changed')
        if old[2] not in ENROLL_IDS and old!=new:
            raise M48BuildError('Altered known working M45 menu or SimData')
    return entries


def package_bytes():
    source=build_m45()
    entries=transformed_resources()
    header=bytearray(source[:96])
    body=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,g,iid,raw in entries:
        packed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,g,iid>>32,iid&0xffffffff,
                                96+len(body),len(packed)|0x80000000,
                                len(raw),0x5A42,1))
        body.extend(packed)
    struct.pack_into('<I',header,0x24,len(entries))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(body))
    blob=bytes(header+body+index)
    if resources(blob)!=entries:
        raise M48BuildError('DBPF roundtrip failed')
    audit=inspect_bytes(blob)
    if audit['status']!='STATIC_GATE_PASSED' or audit['category_count']!=5 or audit['simdata_count']!=5:
        raise M48BuildError('M45 known-good categories were not preserved')
    return blob


def compile_scripts(path):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M48BuildError('The Sims 4 requires Python 3.7')
    if len(SCRIPTS)!=17 or len({p.name for p in SCRIPTS})!=17:
        raise M48BuildError('Expected 17 unique scripts')
    with tempfile.TemporaryDirectory() as folder:
        with zipfile.ZipFile(str(path),'w',zipfile.ZIP_DEFLATED) as z:
            for file in SCRIPTS:
                output=Path(folder)/(file.name+'c')
                py_compile.compile(str(file),cfile=str(output),doraise=True)
                z.write(str(output),arcname=file.name+'c')


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACKAGE).write_bytes(blob)
    compile_scripts(folder/SCRIPT)
    return {
        'status':'IN_GAME_MAC_TEST_REQUIRED',
        'modified_interactions':3,
        'unchanged_category_and_SimData_pairs':5,
        'archive_modules':len(SCRIPTS),
        'package_sha256':hashlib.sha256(blob).hexdigest(),
    }


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m48_native_enrollment <output_dir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
