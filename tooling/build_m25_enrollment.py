"""M25 diagnostic package: native M1 UI + staged Python confirmation.

Only confirmed game runtime tests can establish whether notifications and
the external registry work in actual The Sims 4 on Mac.
"""
from pathlib import Path
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

from tooling.build_m1_offline import build_m1_bytes
from tooling.simdata_release_gate import inspect_bytes, resources
from tooling.m1_links_and_strings import parse_stbl

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src' / 'm25_enrollment'
SCRIPTS = (
    SOURCE / 'mhs25_confirmation.py',
    ROOT / 'src' / 'm2_registry' / 'mhs_m2_roster.py',
    ROOT / 'src' / 'm2_registry' / 'mhs_m2_store.py',
    ROOT / 'src' / 'm2_registry' / 'mhs_m2_selection_probe.py',
    ROOT / 'src' / 'm2_registry' / 'mhs_m2_game_bridge.py',
)
CONFIRMATIONS = {
    13813934116852558422: 'MHS25StageConfirmClass1',
    13813933017340930211: 'MHS25StageConfirmClass2',
}
TEXT_OVERRIDES = {
    'it': {
        0x3FCE8D06: 'MY HIGH SCHOOL (M25 TEST)',
        0xED9F1219: 'Prepara iscrizione Classe 1',
        0xEA9F0D60: 'Prepara iscrizione Classe 2',
        0x32988D0E: 'Classe 1 - Seleziona studenti',
        0x31988B7B: 'Classe 2 - Seleziona studenti',
        0x7FE4CEBC: 'Scegli fino a 8 adolescenti. La spunta prepara la selezione, NON la salva. Poi usa mhs25.preview.',
        0x78718F64: 'MY HIGH SCHOOL - M25 TEST',
        0x19B49209: 'Selezione Classe 1 ricevuta. Controlla con mhs25.preview prima di salvare.',
        0x16B48D50: 'Selezione Classe 2 ricevuta. Controlla con mhs25.preview prima di salvare.',
    },
    'en': {
        0x3FCE8D06: 'MY HIGH SCHOOL (M25 TEST)',
        0xED9F1219: 'Stage Class 1 enrollment',
        0xEA9F0D60: 'Stage Class 2 enrollment',
        0x32988D0E: 'Class 1 - Select students',
        0x31988B7B: 'Class 2 - Select students',
        0x7FE4CEBC: 'Choose up to 8 teens. Confirming STAGES the selection, it does NOT save. Then use mhs25.preview.',
        0x78718F64: 'MY HIGH SCHOOL - M25 TEST',
        0x19B49209: 'Class 1 selection received. Check mhs25.preview before saving.',
        0x16B48D50: 'Class 2 selection received. Check mhs25.preview before saving.',
    }
}
TYPE_INTERACTION = 0xE882D22F
TYPE_STBL = 0x220557DA
ENTRY = struct.Struct('<IIIIIIIHH')
PACKAGE_NAME = 'MHS_M25_REGISTRO_TEST.package'
SCRIPT_NAME = 'MHS_M25_REGISTRO_TEST.ts4script'


class M25BuildError(ValueError):
    pass


def new_stbl(payload, locale):
    decoded=parse_stbl(payload)
    changes=TEXT_OVERRIDES[locale]
    if set(decoded)!=set(changes):
        raise M25BuildError('Localization set changed')
    decoded.update(changes)
    data=bytearray()
    total=0
    for key, value in sorted(decoded.items()):
        encoded=value.encode('utf-8')
        data.extend(struct.pack('<IBH',key,0,len(encoded)))
        data.extend(encoded)
        total+=len(encoded)+1
    result=(b'STBL'+struct.pack('<HBQ2sI',5,0,len(decoded),b'\\x00\\x00',total)+bytes(data))
    if parse_stbl(result)!=decoded:
        raise M25BuildError('STBL roundtrip mismatch')
    return result


def replace_resources(entries):
    changed=[]
    out=[]
    for typ,group,iid,payload in entries:
        if typ==TYPE_INTERACTION and iid in CONFIRMATIONS:
            root=ET.fromstring(payload)
            if root.get('c')!='ImmediateSuperInteraction':
                raise M25BuildError('Unexpected confirmation class')
            root.set('c',CONFIRMATIONS[iid])
            root.set('m','mhs25_confirmation')
            payload=ET.tostring(root,encoding='utf-8')
            changed.append(('confirm',iid))
        elif typ==TYPE_STBL:
            locale={0:'en',11:'it'}.get(iid>>56)
            if locale is None:
                raise M25BuildError('Unexpected locale')
            payload=new_stbl(payload,locale)
            changed.append(('stbl',locale))
        out.append((typ,group,iid,payload))
    if len(out)!=9 or len(changed)!=4:
        raise M25BuildError('M25 expected 4 resource mutations only')
    return out


def build_package():
    base=build_m1_bytes()
    old=resources(base)
    newer=replace_resources(old)
    head=bytearray(base[:96])
    if head[:4]!=b'DBPF' or struct.unpack_from('<I',head,0x3C)[0]!=3:
        raise M25BuildError('Invalid original DBPF index')
    data=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,raw in newer:
        compressed=zlib.compress(raw,9)
        offset=96+len(data)
        data.extend(compressed)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xFFFFFFFF,offset,
                                len(compressed)|0x80000000,len(raw),0x5A42,1))
    struct.pack_into('<I',head,0x24,len(newer))
    struct.pack_into('<I',head,0x2C,len(index))
    struct.pack_into('<Q',head,0x40,96+len(data))
    result=bytes(head+data+index)
    if resources(result)!=newer:
        raise M25BuildError('Package roundtrip mismatch')
    if inspect_bytes(result)['status']!='STATIC_GATE_PASSED':
        raise M25BuildError('SimData structural gate failed')
    if [(x[:3]) for x in old]!=[(x[:3]) for x in newer]:
        raise M25BuildError('TGI changed')
    return result


def compile_script(output):
    if sys.version_info[:2]!=(3,7) or importlib.util.MAGIC_NUMBER!=bytes((66,13,13,10)):
        raise M25BuildError('M25 ts4script must be compiled on CPython 3.7')
    with tempfile.TemporaryDirectory() as directory:
        with zipfile.ZipFile(str(output),'w',zipfile.ZIP_DEFLATED) as result:
            for source in SCRIPTS:
                if not source.exists():
                    raise M25BuildError('Missing source '+str(source))
                compiled=Path(directory)/str(source.name+'c')
                py_compile.compile(str(source),cfile=str(compiled),doraise=True)
                result.write(str(compiled),arcname=source.name+'c')
    with zipfile.ZipFile(str(output)) as result:
        if set(result.namelist())!={src.name+'c' for src in SCRIPTS}:
            raise M25BuildError('Missing script from release archive')
        if any(result.read(name)[:4]!=importlib.util.MAGIC_NUMBER for name in result.namelist()):
            raise M25BuildError('Wrong bytecode magic')


def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    binary=build_package()
    (folder/PACKAGE_NAME).write_bytes(binary)
    compile_script(folder/SCRIPT_NAME)
    return {'package_size':len(binary),
            'package_sha256':hashlib.sha256(binary).hexdigest(),
            'scripts':len(SCRIPTS),
            'status':'NOT_TESTED_IN_GAME'}


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m tooling.build_m25_enrollment <output_dir>')
    print(json.dumps(release(sys.argv[1]),indent=2))
