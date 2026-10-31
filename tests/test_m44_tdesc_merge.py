"""M44 merge safety: TDesc-generated menu categories do not erase M43 actions."""
import struct
import unittest
import xml.etree.ElementTree as ET
import zlib
from tooling.build_m44_tdesc_merge import (
    transform,package_bytes,M44BuildError,ROOT_NAME,merge_lot51_exports,
    CATEGORY_TYPE,SIMDATA_TYPE,SIMDATA_GROUP)
from tooling.build_m43_matched_root import package_bytes as m43
from tooling.build_m27_removal import ENTRY
from tooling.simdata_release_gate import resources,inspect_bytes


def dbpf_with_resources(rows):
    old=m43()
    header=bytearray(old[:96])
    data=bytearray()
    index=bytearray(struct.pack('<I',0))
    for typ,group,iid,raw in rows:
        zipdata=zlib.compress(raw,9)
        index.extend(ENTRY.pack(typ,group,iid>>32,iid&0xffffffff,
                                96+len(data),len(zipdata)|0x80000000,
                                len(raw),0x5A42,1))
        data.extend(zipdata)
    struct.pack_into('<I',header,0x24,len(rows))
    struct.pack_into('<I',header,0x2c,len(index))
    struct.pack_into('<Q',header,0x40,96+len(data))
    return bytes(header+data+index)


def exported_categories(new_priority=None, legacy_low_parent=False):
    current=resources(m43())
    rows=[]
    root_id=next(i for typ,g,i,raw in current
                 if typ==CATEGORY_TYPE and ET.fromstring(raw).get('n')==ROOT_NAME)
    for typ,g,i,raw in current:
        if typ not in (CATEGORY_TYPE,SIMDATA_TYPE):
            continue
        if typ==SIMDATA_TYPE and i!=root_id and not legacy_low_parent:
            # TDesc emits the child TableSetReference in high 32 bits.
            data=bytearray(raw)
            parent=struct.unpack_from('<Q',data,0x5c)[0]
            assert parent==root_id
            struct.pack_into('<Q',data,0x5c,parent<<32)
            raw=bytes(data)
        if i==root_id and new_priority is not None:
            if typ==CATEGORY_TYPE:
                node=ET.fromstring(raw)
                field=node.find('./T[@n="_display_priority"]')
                assert field is not None
                field.text=str(new_priority)
                raw=ET.tostring(node,encoding='utf-8')
            else:
                data=bytearray(raw)
                struct.pack_into('<i',data,0x48,new_priority)
                raw=bytes(data)
        rows.append((typ,g,i,raw))
    return dbpf_with_resources(rows)


class M44Tests(unittest.TestCase):
    def test_reject_handpatched_low_half_simdata_reference(self):
        with self.assertRaisesRegex(M44BuildError,'parent mismatch'):
            transform(exported_categories(legacy_low_parent=True))

    def test_tdesc_changes_only_category_resources(self):
        blob,changes=package_bytes(exported_categories(8))
        self.assertTrue(any(x.startswith('simdata:') for x in changes))
        self.assertEqual(inspect_bytes(blob)['status'],'STATIC_GATE_PASSED')
        old=resources(m43())
        new=resources(blob)
        self.assertEqual(len(new),35)
        for a,b in zip(old,new):
            if a[0] not in (CATEGORY_TYPE,SIMDATA_TYPE):
                self.assertEqual(a,b,'M44 modified an interaction, string or injector')
        pairs=[r for r in new if r[0]==CATEGORY_TYPE]
        self.assertEqual(len(pairs),5)

    def test_reject_missing_child_simdata(self):
        short=[r for r in resources(exported_categories(8))
               if not(r[0]==SIMDATA_TYPE and r[2]==869446548)]
        with self.assertRaisesRegex(M44BuildError,'SimData'):
            transform(dbpf_with_resources(short))

    def test_reject_export_unlinked_child(self):
        rows=resources(exported_categories(8))
        new=[]
        for typ,g,i,raw in rows:
            if typ==CATEGORY_TYPE and i==869446548:
                root=ET.fromstring(raw)
                root.find('./T[@n="_parent"]').text='0'
                raw=ET.tostring(root,encoding='utf-8')
            new.append((typ,g,i,raw))
        with self.assertRaisesRegex(M44BuildError,'parent mismatch'):
            transform(dbpf_with_resources(new))


if __name__=='__main__':
    unittest.main()
