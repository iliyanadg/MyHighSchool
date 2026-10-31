"""M38 experimental complete static hierarchy based on compact-root M37.

Constructs MY HIGH SCHOOL -> class 1, class 2, class 3, settings.
All class-specific interactions are moved into their respective categories.
Category root/children are 31-bit. Does NOT dynamically hide class 3
or implement pause-time interaction execution. Keep M35B as fallback.

IMPORTANT: M37 must work in-game BEFORE suggesting this M38 to user.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib

from tooling.build_m37_small_root import (
    package_bytes as build_m37,NEW_ROOT,CATEGORY_ID,MAIN_LABEL,
    TYPE_CATEGORY,TYPE_SIMDATA,SIMDATA_GROUP,TYPE_INTERACTION,TYPE_STBL)
from tooling.build_m30_nested_menu import (
    CATEGORY_IDS,CATEGORY_NAMES,NEW_KEYS,ENROLL_IDS,REMOVE_CLASS_IDS,
    NEW_VIEW_IDS,category_id)
from tooling.build_m33_flat_recovery import IDS as TRANSFER_IDS,ROUTES
from tooling.build_m34_settings import IDS as SETTINGS_IDS,compile_scripts
from tooling.build_m27_removal import ENTRY
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import inspect_bytes,resources

SETTINGS_NAME='Iliyana:MHS_Settings'  # fixed 20-byte SimData name
SETTINGS_CATEGORY=category_id(SETTINGS_NAME)
SETTINGS_LABEL=0x5A892844
PACK_NAME='MHS_M38_MENU_CLASSI_COMPLETO_TEST.package'
SCRIPT_NAME='MHS_M38_MENU_CLASSI_COMPLETO_TEST.ts4script'
CHILD_NAME=CATEGORY_NAMES[0]


class M38BuildError(ValueError):
    pass


def new_category_xml(template,iid,name,label):
    base=ET.fromstring(template)
    if base.get('s')!=str(CATEGORY_ID):
        raise M38BuildError('Wrong class-1 category template')
    base.set('s',str(iid))
    base.set('n',name)
    display=base.find('./T[@n="_display_name"]')
    if display is None:
        raise M38BuildError('Missing child display label')
    display.text='0x{:08X}'.format(label)
    parent=base.find('./T[@n="_parent"]')
    if parent is None or parent.text!=str(NEW_ROOT):
        raise M38BuildError('Wrong compact root')
    return ET.tostring(base,encoding='utf-8')


def new_category_simdata(template,name,label):
    if (len(template)!=475 or template[:4]!=b'DATA'
            or len(name)!=20 or len(CHILD_NAME)!=20
            or template.count(CHILD_NAME.encode('ascii'))!=1
            or struct.unpack_from('<I',template,0x44)[0]!=NEW_KEYS[0]
            or struct.unpack_from('<Q',template,0x5c)[0]!=NEW_ROOT):
        raise M38BuildError('Unexpected category SimData layout')
    data=bytearray(template)
    struct.pack_into('<I',data,0x44,label)
    offset=data.find(CHILD_NAME.encode('ascii'))
    data[offset:offset+20]=name.encode('ascii')
    return bytes(data)


def remap_action(blob,target):
    root=ET.fromstring(blob)
    category=root.find('./T[@n="category"]')
    if category is None or category.text!=str(NEW_ROOT):
        raise M38BuildError('Unrecognized root interaction category')
    category.text=str(target)
    return ET.tostring(root,encoding='utf-8')


def with_labels(raw,locale):
    values=parse_stbl(raw)
    for key,label in ((NEW_KEYS[1],'Classe 2'),(NEW_KEYS[2],'Classe 3'),
                      (SETTINGS_LABEL,'Impostazioni')):
        if key in values:
            raise M38BuildError('Duplicate label key')
        values[key]=label if locale=='it' else (
            label.replace('Classe','Class').replace('Impostazioni','Settings'))
    values[MAIN_LABEL]='MY HIGH SCHOOL (M38 TEST)'
    payload=bytearray()
    total=0
    for key,value in sorted(values.items()):
        encoded=value.encode('utf-8')
        payload.extend(struct.pack('<IBH',key,0,len(encoded)))
        payload.extend(encoded)
        total+=len(encoded)+1
    output=b'STBL'+struct.pack('<HBQ2sI',5,0,len(values),b'\x00\x00',total)+bytes(payload)
    if parse_stbl(output)!=values:
        raise M38BuildError('Localization mismatch')
    return output


def target_map():
    mapping={}
    for klass in (1,2,3):
        cat=CATEGORY_IDS[klass-1]
        if klass==1 and cat!=CATEGORY_ID:
            raise M38BuildError('Class 1 category mismatch')
        for iid in (ENROLL_IDS[klass-1],REMOVE_CLASS_IDS[klass-1],
                    NEW_VIEW_IDS[klass-1]):
            mapping[iid]=cat
    for iid,(source,dest) in zip(TRANSFER_IDS,ROUTES):
        mapping[iid]=CATEGORY_IDS[source-1]
    # Keep the two state actions (MHS34_Enable/Disable) in root.
    mapping[SETTINGS_IDS[2]]=SETTINGS_CATEGORY
    mapping[SETTINGS_IDS[3]]=SETTINGS_CATEGORY
    return mapping


def transformed_resources():
    if (len(SETTINGS_NAME)!=20 or len(set(CATEGORY_IDS))!=3
            or NEW_ROOT in CATEGORY_IDS
            or SETTINGS_CATEGORY in set(CATEGORY_IDS)|{NEW_ROOT}
            or not 0<SETTINGS_CATEGORY<2**31):
        raise M38BuildError('Category ID collision or invalid name')
    existing=resources(build_m37())
    cat_xml=next(raw for t,g,i,raw in existing if t==TYPE_CATEGORY and i==CATEGORY_ID)
    cat_data=next(raw for t,g,i,raw in existing if t==TYPE_SIMDATA and i==CATEGORY_ID and g==SIMDATA_GROUP)
    move=target_map()
    # Class1 consulta/rimuovi are already in the child, all other items are in root.
    changed=set()
    result=[]
    locales=set()
    for t,g,i,blob in existing:
        if t==TYPE_INTERACTION and i in move:
            if i in (REMOVE_CLASS_IDS[0],NEW_VIEW_IDS[0]):
                category=ET.fromstring(blob).find('./T[@n="category"]')
                if category is None or category.text!=str(CATEGORY_ID):
                    raise M38BuildError('M37 class 1 child items disappeared')
            else:
                blob=remap_action(blob,move[i])
            changed.add(i)
        elif t==TYPE_STBL:
            locale={0:'en',11:'it'}.get(i>>56)
            if locale is None:
                raise M38BuildError('Unrecognized STBL locale')
            blob=with_labels(blob,locale)
            locales.add(locale)
        result.append((t,g,i,blob))
    if changed!=set(move) or locales!={'en','it'}:
        raise M38BuildError('Missing interactions or translations')
    for cls_idx in (1,2):
        result.extend([
            (TYPE_CATEGORY,0,CATEGORY_IDS[cls_idx],
             new_category_xml(cat_xml,CATEGORY_IDS[cls_idx],CATEGORY_NAMES[cls_idx],NEW_KEYS[cls_idx])),
            (TYPE_SIMDATA,SIMDATA_GROUP,CATEGORY_IDS[cls_idx],
             new_category_simdata(cat_data,CATEGORY_NAMES[cls_idx],NEW_KEYS[cls_idx]))
        ])
    result.extend([
        (TYPE_CATEGORY,0,SETTINGS_CATEGORY,
         new_category_xml(cat_xml,SETTINGS_CATEGORY,SETTINGS_NAME,SETTINGS_LABEL)),
        (TYPE_SIMDATA,SIMDATA_GROUP,SETTINGS_CATEGORY,
         new_category_simdata(cat_data,SETTINGS_NAME,SETTINGS_LABEL))
    ])
    if len(result)!=35 or len(set(row[:3] for row in result))!=35:
        raise M38BuildError('Unexpected resource count or duplicate')
    return result


def package_bytes():
    old=build_m37()
    records=transformed_resources()
    head=bytearray(old[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for t,g,i,raw in records:
        zipped=zlib.compress(raw,9)
        index.extend(ENTRY.pack(t,g,i>>32,i&0xffffffff,
                                96+len(payload),len(zipped)|0x80000000,
                                len(raw),0x5A42,1))
        payload.extend(zipped)
    struct.pack_into('<I',head,0x24,len(records))
    struct.pack_into('<I',head,0x2c,len(index))
    struct.pack_into('<Q',head,0x40,96+len(payload))
    result=bytes(head+payload+index)
    if resources(result)!=records:
        raise M38BuildError('Package failed roundtrip')
    audit=inspect_bytes(result)
    if (audit['status']!='STATIC_GATE_PASSED'
            or audit['category_count']!=5 or audit['simdata_count']!=5):
        raise M38BuildError('Category structural audit failed')
    return result


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    compile_scripts(folder/SCRIPT_NAME)
    return {'status':'UNVERIFIED_NOT_FOR_INSTALL_UNTIL_M37_WORKS',
            'resources':len(resources(blob)),
            'categories':5,
            'sha256':hashlib.sha256(blob).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m38_three_class_menu <dir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
