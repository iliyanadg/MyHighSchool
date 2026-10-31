"""M39 experimental complete class tree with active & 2/3-class UI gating.

M38 generated a static hierarchy, still visible while switched off.
M39 attaches subclasses to 19 existing actions that override only
the _test hook using persisted per-slot settings. No base action is
reimplemented or new data writes introduced.

Compatibility with TS4's test dispatch / no pause is not proven until
the user checks in game. M37 compact-root must work in-game first.
"""
import ast
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

from tooling.build_m38_three_class_menu import package_bytes as build_m38
from tooling.build_m34_settings import SCRIPTS as M34_SCRIPTS
from tooling.build_m27_removal import ENTRY,TYPE_INTERACTION
from tooling.simdata_release_gate import resources, inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
RULES=ROOT/'src'/'m39_visibility'/'mhs39_visibility_rules.py'
UI=ROOT/'src'/'m39_visibility'/'mhs39_visibility_ui.py'
PACK_NAME='MHS_M39_CLASSI_DINAMICHE_TEST.package'
SCRIPT_NAME='MHS_M39_CLASSI_DINAMICHE_TEST.ts4script'


class M39BuildError(ValueError):
    pass


def specs():
    tree=ast.parse(UI.read_text(encoding='utf-8'))
    for item in tree.body:
        if (isinstance(item,ast.Assign)
                and any(isinstance(n,ast.Name) and n.id=='SPECS'
                        for n in item.targets)):
            value=ast.literal_eval(item.value)
            if len(value)!=19:
                raise M39BuildError('Expected exactly 19 gated affordances')
            return {(mod,cls):'MHS39_'+cls for mod,cls,action,num in value}
    raise M39BuildError('Missing source specs')


def transformed_resources():
    mapping=specs()
    touched=set()
    original=resources(build_m38())
    result=[]
    for t,g,i,blob in original:
        if t==TYPE_INTERACTION:
            root=ET.fromstring(blob)
            pair=(root.get('m'),root.get('c'))
            if pair in mapping:
                touched.add(pair)
                root.set('m','mhs39_visibility_ui')
                root.set('c',mapping[pair])
                blob=ET.tostring(root,encoding='utf-8')
            elif pair!=('interactions.base.picker_interaction','SimPickerInteraction'):
                raise M39BuildError('No guard for unexpected action {}'.format(pair))
            # EA SimPickerInteraction is a supporting picker tuning, not one
            # of the school menu's 19 clickable affordances. Keep unchanged.
        result.append((t,g,i,blob))
    if touched!=set(mapping):
        raise M39BuildError('Not all 19 game actions guarded')
    if len(result)!=35:
        raise M39BuildError('Wrong package resource count')
    return result


def package_bytes():
    original=build_m38()
    data=transformed_resources()
    head=bytearray(original[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for t,g,i,raw in data:
        packed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(t,g,i>>32,i&0xffffffff,
                                96+len(payload),len(packed)|0x80000000,
                                len(raw),0x5A42,1))
        payload.extend(packed)
    struct.pack_into('<I',head,0x24,len(data))
    struct.pack_into('<I',head,0x2c,len(index))
    struct.pack_into('<Q',head,0x40,96+len(payload))
    out=bytes(head+payload+index)
    if resources(out)!=data:
        raise M39BuildError('DBPF roundtrip failed')
    report=inspect_bytes(out)
    if (report['status']!='STATIC_GATE_PASSED'
            or report['category_count']!=5
            or report['simdata_count']!=5):
        raise M39BuildError('Invalid category pair structure')
    return out


def compile_scripts(dest):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M39BuildError('Requires Python 3.7 bytecode for The Sims 4')
    sources=tuple(M34_SCRIPTS)+(RULES,UI)
    if len(sources)!=15 or len(set(f.name for f in sources))!=15:
        raise M39BuildError('Duplicate source or wrong script inventory')
    with tempfile.TemporaryDirectory() as folder:
        with zipfile.ZipFile(str(dest),'w',zipfile.ZIP_DEFLATED) as archive:
            for source in sources:
                compiled=Path(folder)/(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                archive.write(str(compiled),arcname=source.name+'c')


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    blob=package_bytes()
    (folder/PACK_NAME).write_bytes(blob)
    compile_scripts(folder/SCRIPT_NAME)
    return {'status':'UNVERIFIED_GAME_TEST_REQUIRED',
            'resources':len(resources(blob)),
            'gated_actions':len(specs()),
            'scripts':15,
            'sha256':hashlib.sha256(blob).hexdigest()}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m39_conditional_menu <outdir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
