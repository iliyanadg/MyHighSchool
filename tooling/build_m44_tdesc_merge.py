"""M44: integrate freshly generated Lot51 TDesc menu category resources.

The M43 live game has correct parent values in XML/SimData but still shows
all class menus alongside the root. This tool does NOT assume the previous
hand-patched SimData was correct; it takes newly exported Lot51 category
XML + SimData resources, checks them, and swaps only these five paired
resources into M43 while remapping interaction.category if IDs changed.
It never rewrites student roster data or the 15 Python 3.7 scripts.

Usage:
    python -m tooling.build_m44_tdesc_merge <tdesc_1.package> ... <tdesc_5.package> <outdir>
    Download Package in Lot51 from each of the five PIE_MENU_CATEGORY tabs (not actions).
Do NOT install the Lot51 export directly; it omits our class interactions.

Passing the offline gate does not prove the nesting works in the Mac game.
If export is semantically and binary-identical to M43, no new build is
made; further game tests with the same data would be pointless.
"""
import hashlib
import json
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

from tooling.build_m43_matched_root import package_bytes as original_m43,ROOT_NAME
from tooling.build_m39_conditional_menu import compile_scripts
from tooling.build_m27_removal import ENTRY,TYPE_INTERACTION
from tooling.build_m41_complete_menu import CATEGORY_TYPE,SIMDATA_TYPE,SIMDATA_GROUP
from tooling.simdata_release_gate import resources,inspect_bytes

PACK_NAME='MHS_M44_TDESC_CATEGORIE_RIGENERATE_TEST.package'
SCRIPT_NAME='MHS_M44_TDESC_CATEGORIE_RIGENERATE_TEST.ts4script'
SCHEMA_HASH=struct.pack('<I',0xE2EAA141)


class M44BuildError(ValueError):
    pass


def categories_and_data(rows):
    categories={}
    simdata={}
    for typ,group,iid,raw in rows:
        if typ==CATEGORY_TYPE:
            root=ET.fromstring(raw)
            if (root.get('c')!='PieMenuCategory' or
                    root.get('s')!=str(iid) or not root.get('n')):
                raise M44BuildError('Malformed pie menu category tuning')
            name=root.get('n')
            if name in categories:
                raise M44BuildError('Duplicate menu category name')
            categories[name]=(iid,raw,root)
        elif typ==SIMDATA_TYPE:
            if group!=SIMDATA_GROUP:
                continue
            simdata[iid]=raw
    return categories,simdata


def normalize_xml(raw):
    root=ET.fromstring(raw)
    for el in root.iter():
        if el.text is not None and not el.text.strip():
            el.text=None
        if el.tail is not None and not el.tail.strip():
            el.tail=None
    return ET.tostring(root,encoding='utf-8')


def transform(export_package):
    current=resources(original_m43())
    exported=resources(export_package)
    old_cat,old_data=categories_and_data(current)
    new_cat,new_data=categories_and_data(exported)
    expected=set(old_cat)
    if len(expected)!=5 or ROOT_NAME not in expected:
        raise M44BuildError('Unexpected original menu category inventory')
    if set(new_cat)!=expected:
        raise M44BuildError(
            'TDesc must export precisely these 5 categories: '+repr(sorted(expected)))
    old_ids={name:iid for name,(iid,raw,node) in old_cat.items()}
    new_ids={name:iid for name,(iid,raw,node) in new_cat.items()}
    if (len(set(new_ids.values()))!=5 or
            any(iid not in new_data for iid in new_ids.values())):
        raise M44BuildError('Five regenerated SimData resources are required')
    main=new_ids[ROOT_NAME]
    if (not 0<main<2**64 or
            new_cat[ROOT_NAME][2].find('./T[@n="_parent"]') is not None):
        raise M44BuildError('Root must have no parent')
    for name,(iid,raw,node) in new_cat.items():
        binary=new_data[iid]
        if not(binary[:4]==b'DATA' and len(binary)>=112 and
                SCHEMA_HASH in binary):
            raise M44BuildError('Wrong TDesc SimData schema or header')
        if name.encode('utf-8') not in binary:
            raise M44BuildError('SimData name does not match its tuning')
        xml_parent=node.find('./T[@n="_parent"]')
        parent=0 if xml_parent is None else int(xml_parent.text)
        # TDesc October-2026 exports store the TableSetReference in
        # high 32 bits of the 64-bit slot starting at 0x5c.
        # M43 hand-edited low 32 bits; THIS is the actual mismatch.
        actual_ref=struct.unpack_from('<Q',binary,0x5c)[0]
        expected_parent=0 if name==ROOT_NAME else main
        if parent!=expected_parent or actual_ref!=(expected_parent<<32):
            raise M44BuildError(
                'TDesc root/child parent mismatch in '+name)
        visible=node.find('./T[@n="_collapsible"]')
        if visible is None or visible.text!='False' or binary[0x40]!=0:
            raise M44BuildError('Unexpected _collapsible for '+name)

    mapping={old_ids[n]:new_ids[n] for n in expected}
    changes=[]
    output=[]
    for typ,group,iid,raw in current:
        if typ==CATEGORY_TYPE:
            node=ET.fromstring(raw)
            name=node.get('n')
            revised_iid,revised,unused=new_cat[name]
            if iid!=revised_iid or normalize_xml(raw)!=normalize_xml(revised):
                changes.append('category:'+name)
            output.append((typ,group,revised_iid,revised))
        elif typ==SIMDATA_TYPE and group==SIMDATA_GROUP:
            name=next((n for n,i in old_ids.items() if i==iid),None)
            if name is None:
                raise M44BuildError('Old orphan SimData')
            revised_iid=new_ids[name]
            revised=new_data[revised_iid]
            if iid!=revised_iid or raw!=revised:
                changes.append('simdata:'+name)
            output.append((typ,group,revised_iid,revised))
        elif typ==TYPE_INTERACTION:
            node=ET.fromstring(raw)
            field=node.find('./T[@n="category"]')
            if field is not None:
                old=int(field.text)
                if old not in mapping:
                    raise M44BuildError('Unrecognized interaction category')
                if mapping[old]!=old:
                    field.text=str(mapping[old])
                    raw=ET.tostring(node,encoding='utf-8')
                    changes.append('interaction:'+node.get('n',''))
            output.append((typ,group,iid,raw))
        else:
            output.append((typ,group,iid,raw))
    if len(output)!=35 or len(set(entry[:3] for entry in output))!=35:
        raise M44BuildError('Resource count or TGI collision after merge')
    if not changes:
        raise M44BuildError('UNCHANGED: TDesc generated the same category resources as M43; do not retest')
    return output,changes


def package_bytes(export_package):
    rows,changes=transform(export_package)
    header=bytearray(original_m43()[:96])
    contents=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,raw in rows:
        packed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(contents),len(packed)|0x80000000,
                                len(raw),0x5A42,1))
        contents.extend(packed)
    struct.pack_into('<I',header,0x24,len(rows))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(contents))
    package=bytes(header+contents+index)
    if resources(package)!=rows:
        raise M44BuildError('DBPF merge failed roundtrip')
    result=inspect_bytes(package)
    if (result['status']!='STATIC_GATE_PASSED' or
            result['category_count']!=5 or result['simdata_count']!=5):
        raise M44BuildError('Regenerated package invalid')
    return package,changes


def merge_lot51_exports(export_paths):
    """Combine separate Lot51 packages; ignore any accidental interaction tabs."""
    all_categories=[]
    seen=set()
    for path in export_paths:
        rows=resources(Path(path).read_bytes())
        for typ,g,i,raw in rows:
            if typ not in (CATEGORY_TYPE,SIMDATA_TYPE):
                continue
            key=(typ,g,i)
            if key in seen:
                raise M44BuildError('Duplicate category or SimData from Lot51 exports')
            seen.add(key)
            all_categories.append((typ,g,i,raw))
    if len(all_categories)!=10:
        raise M44BuildError(
            'Needed 5 category XML + 5 binary SimData resources, got {}. '
            'Make sure to export Class_1_, Class_2_, Class_3_, MainMenu, Settings '
            'rather than ChooseClass1/2/3 interactions.'.format(len(all_categories)))
    base=bytearray(original_m43()[:96])
    payload=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,g,i,raw in all_categories:
        compressed=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,g,i>>32,i&0xffffffff,
                                96+len(payload),len(compressed)|0x80000000,
                                len(raw),0x5A42,1))
        payload.extend(compressed)
    struct.pack_into('<I',base,0x24,len(all_categories))
    struct.pack_into('<I',base,0x2c,len(index))
    struct.pack_into('<Q',base,0x40,96+len(payload))
    return bytes(base+payload+index)


def release(export_paths,dest):
    if isinstance(export_paths,(str,Path)):
        export_paths=[export_paths]
    dest=Path(dest)
    blob,changes=package_bytes(merge_lot51_exports(export_paths))
    dest.mkdir(parents=True,exist_ok=True)
    (dest/PACK_NAME).write_bytes(blob)
    compile_scripts(dest/SCRIPT_NAME)
    return {'status':'MAC_GAME_TEST_REQUIRED',
            'changed':changes,
            'sha256':hashlib.sha256(blob).hexdigest(),
            'scripts_preserved':15}


if __name__=='__main__':
    if len(sys.argv)<3:
        raise SystemExit('Usage: python -m tooling.build_m44_tdesc_merge <tdesc_1.package> [tdesc_2.package ...] <outdir>')
    print(json.dumps(release(sys.argv[1:-1],sys.argv[-1]),indent=2))
