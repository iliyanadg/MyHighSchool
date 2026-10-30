"""Build the combined M28 prototype with three class menus and controls.

Runtime validation still required in The Sims 4; static tests alone
cannot prove that the cloned class-3 SimPicker is game-compatible.
"""
import hashlib
import importlib.util
import json
import py_compile
import struct
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import zlib

from tooling.build_m27_removal import (package_bytes as build_m27,
                                      SCRIPTS as M27_SCRIPTS,
                                      fnv64_highbit, BASE_CATEGORY,
                                      TYPE_INTERACTION, TYPE_SNIPPET,
                                      TYPE_STBL, ENTRY)
from tooling.m1_links_and_strings import parse_stbl
from tooling.simdata_release_gate import resources, inspect_bytes

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT/'src'/'m28_bundle'/'mhs28_controls.py'
SCRIPTS = tuple(M27_SCRIPTS) + (CONTROLS,)
PACK_NAME = 'MHS_M28_REGISTRO_3_CLASSI_TEST.package'
SCRIPT_NAME = 'MHS_M28_REGISTRO_3_CLASSI_TEST.ts4script'
PICKER_2 = 10604124044625822232
CONFIRM_2 = 13813933017340930211
KEY_MENU = 0x3FCE8D06
KEY_ENROLL = 0x5A892831
KEY_PICKER_TITLE = 0x5A892832
KEY_CONFIRM = 0x5A892833
KEY_REMOVE = 0x5A892834
PICKER_3 = fnv64_highbit('Iliyana:MHS28_ChooseClass3')
CONFIRM_3 = fnv64_highbit('Iliyana:MHS28_ConfirmClass3')
REMOVE_3 = fnv64_highbit('Iliyana:MHS28_RemoveClass3')
ADDITIONS = (PICKER_3, CONFIRM_3, REMOVE_3)


class M28BuildError(ValueError):
    pass


def clone_resource(entries, source_id, new_id, klass, module, name):
    candidate = [row for row in entries if row[0] == TYPE_INTERACTION
                 and row[2] == source_id]
    if len(candidate) != 1:
        raise M28BuildError('Missing or repeated baseline tuning {}'.format(source_id))
    typ, group, _iid, blob = candidate[0]
    root = ET.fromstring(blob)
    root.set('s', str(new_id))
    root.set('n', name)
    root.set('c', klass)
    root.set('m', module)
    return root


def new_resources(entries):
    picker = clone_resource(entries, PICKER_2, PICKER_3,
                            'SimPickerInteraction',
                            'interactions.base.picker_interaction',
                            'Iliyana:MHS28_ChooseClass3')
    ref = picker.find('./L[@n="actor_continuation"]/U/T[@n="affordance"]')
    label = picker.find('./T[@n="display_name"]')
    title = picker.find('./V[@n="picker_dialog"]/U[@n="sim_picker"]/V[@n="title"]/T[@n="enabled"]')
    if ref is None or label is None or title is None:
        raise M28BuildError('Class 2 picker lacks required tuning links')
    ref.text = str(CONFIRM_3)
    label.text = '0x{:08X}'.format(KEY_ENROLL)
    title.text = '0x{:08X}'.format(KEY_PICKER_TITLE)

    confirm = clone_resource(entries, CONFIRM_2, CONFIRM_3,
                             'MHS28StageConfirmClass3', 'mhs28_controls',
                             'Iliyana:MHS28_ConfirmClass3')
    original = confirm.find('.//T[@n="text"]')
    # M25 notification text can be linked by its literal STBL id.
    found = [e for e in confirm.iter('T') if e.text == '0x16B48D50']
    if len(found) != 1:
        raise M28BuildError('Could not identify Class 2 confirmation text')
    found[0].text = '0x{:08X}'.format(KEY_CONFIRM)

    removal = ET.Element('I', {'c':'MHS28RemoveClass3','i':'interaction',
                               'm':'mhs28_controls',
                               'n':'Iliyana:MHS28_RemoveClass3',
                               's':str(REMOVE_3)})
    ET.SubElement(removal,'T',{'n':'category'}).text=str(BASE_CATEGORY)
    ET.SubElement(removal,'T',{'n':'display_name'}).text='0x{:08X}'.format(KEY_REMOVE)
    ET.SubElement(removal,'E',{'n':'target_type'}).text='OBJECT'
    ET.SubElement(removal,'V',{'n':'_saveable','t':'disabled'})
    tests = ET.SubElement(removal,'L',{'n':'test_globals'})
    u = ET.SubElement(ET.SubElement(tests,'V',{'t':'sim_info'}),'U',{'n':'sim_info'})
    ages = ET.SubElement(ET.SubElement(u,'V',{'n':'ages','t':'specified'}),
                         'L',{'n':'specified'})
    for age in ('TEEN','YOUNGADULT','ADULT','ELDER'):
        ET.SubElement(ages,'E').text=age
    ET.SubElement(u,'E',{'n':'who'}).text='Actor'

    return [(TYPE_INTERACTION, 0, PICKER_3, ET.tostring(picker,encoding='utf-8')),
            (TYPE_INTERACTION, 0, CONFIRM_3, ET.tostring(confirm,encoding='utf-8')),
            (TYPE_INTERACTION, 0, REMOVE_3, ET.tostring(removal,encoding='utf-8'))]


def update_injector(blob):
    root=ET.fromstring(blob)
    entries=root.find('./L[@n="add_interactions_to_objects"]/U/L[@n="_super_affordances"]')
    if entries is None:
        raise M28BuildError('Missing verified M27 injection path')
    existing={int((e.text or '0').strip()) for e in entries.findall('T')}
    for iid in (PICKER_3, REMOVE_3):
        if iid in existing:
            raise M28BuildError('Duplicate third class action')
        ET.SubElement(entries,'T').text=str(iid)
    # Continuation is reachable ONLY through picker confirmation, not as mailbox option.
    if CONFIRM_3 in existing:
        raise M28BuildError('Class 3 continuation inserted into mailbox by error')
    return ET.tostring(root,encoding='utf-8')


def update_stbl(blob, locale):
    original=parse_stbl(blob)
    if KEY_MENU not in original:
        raise M28BuildError('Missing original menu text')
    if locale=='it':
        values={KEY_MENU:'MY HIGH SCHOOL (M28 TEST)',
                KEY_ENROLL:'Prepara iscrizione Classe 3',
                KEY_PICKER_TITLE:'Classe 3 - Seleziona studenti',
                KEY_CONFIRM:'Selezione Classe 3 ricevuta. Usa mhs25.preview prima di salvare.',
                KEY_REMOVE:'Rimuovi studenti - Classe 3'}
    else:
        values={KEY_MENU:'MY HIGH SCHOOL (M28 TEST)',
                KEY_ENROLL:'Stage Class 3 enrollment',
                KEY_PICKER_TITLE:'Class 3 - Select students',
                KEY_CONFIRM:'Class 3 selection received. Use mhs25.preview before saving.',
                KEY_REMOVE:'Remove students - Class 3'}
    if any(k in original for k in values if k!=KEY_MENU):
        raise M28BuildError('Duplicate M28 localization key')
    original.update(values)
    raw=bytearray()
    total=0
    for key,value in sorted(original.items()):
        b=value.encode('utf-8')
        raw.extend(struct.pack('<IBH',key,0,len(b)))
        raw.extend(b)
        total+=len(b)+1
    result=b'STBL'+struct.pack('<HBQ2sI',5,0,len(original),bytes((0,0)),total)+bytes(raw)
    if parse_stbl(result)!=original:
        raise M28BuildError('Localization roundtrip mismatch')
    return result


def package_bytes():
    base=build_m27()
    older=resources(base)
    new_resources_list=new_resources(older)
    if set(ADDITIONS).intersection({x[2] for x in older}):
        raise M28BuildError('Resource ID collision')
    newer=[]
    modified=[]
    for typ,group,iid,blob in older:
        if typ==TYPE_SNIPPET:
            blob=update_injector(blob)
            modified.append('injector')
        elif typ==TYPE_STBL:
            locale={0:'en',11:'it'}.get(iid>>56)
            if locale is None:
                raise M28BuildError('Unexpected locale')
            blob=update_stbl(blob,locale)
            modified.append(locale)
        newer.append((typ,group,iid,blob))
    if sorted(modified)!=['en','injector','it']:
        raise M28BuildError('Unexpected baseline mutation count')
    newer.extend(new_resources_list)
    if len(newer)!=14:
        raise M28BuildError('Expected 14 resources')
    head=bytearray(base[:96])
    body=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,blob in newer:
        comp=zlib.compress(blob,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xFFFFFFFF,
                                96+len(body),len(comp)|0x80000000,
                                len(blob),0x5A42,1))
        body.extend(comp)
    struct.pack_into('<I',head,0x24,len(newer))
    struct.pack_into('<I',head,0x2C,len(index))
    struct.pack_into('<Q',head,0x40,96+len(body))
    output=bytes(head+body+index)
    if resources(output)!=newer:
        raise M28BuildError('Resource roundtrip failed')
    if inspect_bytes(output)['status']!='STATIC_GATE_PASSED':
        raise M28BuildError('SimData baseline failed structural check')
    for old,now in zip(older,newer):
        if old[:3]!=now[:3] or (old[0]==TYPE_INTERACTION and old[3]!=now[3]):
            raise M28BuildError('Modified existing tuning of verified M27')
    return output


def compile_scripts(output):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M28BuildError('Sims 4 requires the Python 3.7 compiler for this build')
    with tempfile.TemporaryDirectory() as directory:
        with zipfile.ZipFile(str(output),'w',zipfile.ZIP_DEFLATED) as archive:
            for script in SCRIPTS:
                compiled=Path(directory)/(script.name+'c')
                py_compile.compile(str(script),cfile=str(compiled),doraise=True)
                archive.write(str(compiled),arcname=script.name+'c')


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    package=package_bytes()
    (folder/PACK_NAME).write_bytes(package)
    compile_scripts(folder/SCRIPT_NAME)
    return {'status':'EXPERIMENTAL_NEEDS_IN_GAME_TEST',
            'package_sha256':hashlib.sha256(package).hexdigest(),
            'resources':len(resources(package)), 'modules':len(SCRIPTS)}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m28_bundle <output-dir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
