"""M35B: test whether TS4 flattens categories containing only one action.

Game test from M35: the mailbox works; the single 'Consulta iscritti -
Classe 1' action is rendered as a top-level option, not as a submenu.
Try exactly TWO actions in the same one new category, still with NO
parent category, so we distinguish auto-flattening from broken
category registration. Both actions are unchanged except category id.

Do not use this as a replacement for final nested-class UI.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib

from tooling.build_m35_category_smoke import (
    package_bytes as build_m35, CATEGORY_ID, BASE_CATEGORY,
    VIEW_ONLY_INTERACTION, TYPE_INTERACTION, PACK_NAME as OLD_PACK_NAME,
    SCRIPT_NAME as OLD_SCRIPT_NAME)
from tooling.build_m27_removal import IDS as REMOVE_IDS, ENTRY
from tooling.build_m34_settings import compile_scripts as compile_m34_scripts
from tooling.simdata_release_gate import resources, inspect_bytes

REMOVE_CLASS1=REMOVE_IDS[0]
PACK_NAME='MHS_M35B_DUE_AZIONI_CLASSE1_TEST.package'
SCRIPT_NAME='MHS_M35B_DUE_AZIONI_CLASSE1_TEST.ts4script'


class M35BError(ValueError):
    pass


def package_bytes():
    original=build_m35()
    original_rows=resources(original)
    altered=[]
    count=0
    for t,g,i,raw in original_rows:
        if t==TYPE_INTERACTION and i==REMOVE_CLASS1:
            root=ET.fromstring(raw)
            category=root.find('./T[@n="category"]')
            if category is None or category.text!=str(BASE_CATEGORY):
                raise M35BError('Unexpected Class 1 removal baseline')
            category.text=str(CATEGORY_ID)
            raw=ET.tostring(root,encoding='utf-8')
            count+=1
        altered.append((t,g,i,raw))
    if count!=1:
        raise M35BError('Could not relocate only Class 1 removal')
    ids=[]
    for t,g,i,raw in altered:
        if t==TYPE_INTERACTION:
            category=ET.fromstring(raw).find('./T[@n="category"]')
            if category is not None and category.text==str(CATEGORY_ID):
                ids.append(i)
    if set(ids)!={VIEW_ONLY_INTERACTION,REMOVE_CLASS1}:
        raise M35BError('Exactly two Class 1 actions expected')
    head=bytearray(original[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for t,g,i,raw in altered:
        comp=zlib.compress(raw,9)
        index.extend(ENTRY.pack(t,g,i>>32,i&0xffffffff,
                                96+len(payload),len(comp)|0x80000000,
                                len(raw),0x5A42,1))
        payload.extend(comp)
    struct.pack_into('<I',head,0x24,len(altered))
    struct.pack_into('<I',head,0x2c,len(index))
    struct.pack_into('<Q',head,0x40,96+len(payload))
    output=bytes(head+payload+index)
    if resources(output)!=altered:
        raise M35BError('DBPF mismatch')
    report=inspect_bytes(output)
    if report['status']!='STATIC_GATE_PASSED' or report['category_count']!=2 or report['simdata_count']!=2:
        raise M35BError('Category pairs changed unexpectedly')
    return output


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    compile_m34_scripts(folder/SCRIPT_NAME)
    return {'status':'GAME_UI_TEST_REQUIRED',
            'hypothesis':'Single-action category was auto-flattened',
            'resource_count':len(resources(blob)),
            'sha256':hashlib.sha256(blob).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m35b_two_actions <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
