"""Synthetic DBPF tests for a static category/SimData release gate."""
import importlib.util
from pathlib import Path
import struct
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_gate',ROOT/'tooling'/'simdata_release_gate.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

INSTANCE=7064630105397426819
XML=('<?xml version="1.0"?><I c="PieMenuCategory" '
     'i="pie_menu_category" n="Iliyana_MHS_Test_Menu" '
     'm="interactions.pie_menu_category" s="{}"><T n="_collapsible">False</T></I>'.format(INSTANCE)).encode()
SIMDATA=b'DATA'+bytes(range(96))


def package(contents):
    header=bytearray(96);header[:4]=b'DBPF'
    struct.pack_into('<II',header,4,2,1)
    struct.pack_into('<I',header,0x24,len(contents))
    idx=bytearray(struct.pack('<I',0));body=bytearray()
    for typ, group, instance, raw, compressed in contents:
        data=zlib.compress(raw,9) if compressed else raw
        offset=96+len(body)
        idx+=mod.INDEX_ENTRY.pack(typ,group,instance>>32,instance&0xffffffff,
                                  offset,len(data)|(0x80000000 if compressed else 0),
                                  len(raw),0x5A42 if compressed else 0,1 if compressed else 0)
        body+=data
    struct.pack_into('<I',header,0x2c,len(idx))
    struct.pack_into('<Q',header,0x40,96+len(body))
    return bytes(header+body+idx)

class GateTests(unittest.TestCase):
    def test_missing_simdata_is_blocked(self):
        blob=package([(mod.TYPE_CATEGORY,0,INSTANCE,XML,True)])
        self.assertIn('MISSING_SIMDATA',[x['code'] for x in mod.inspect_bytes(blob)['findings']])

    def test_paired_category_passes_static_gate(self):
        blob=package([(mod.TYPE_CATEGORY,0,INSTANCE,XML,True),
                      (mod.TYPE_SIMDATA,0x00e9d7e7,INSTANCE,SIMDATA,True)])
        self.assertEqual(mod.inspect_bytes(blob)['status'],'STATIC_GATE_PASSED')

    def test_simdata_wrong_instance_is_blocked(self):
        blob=package([(mod.TYPE_CATEGORY,0,INSTANCE,XML,True),
                      (mod.TYPE_SIMDATA,0x00e9d7e7,INSTANCE+1,SIMDATA,True)])
        self.assertEqual(mod.inspect_bytes(blob)['status'],'BLOCKED')

    def test_bad_simdata_magic_blocked(self):
        blob=package([(mod.TYPE_CATEGORY,0,INSTANCE,XML,False),
                      (mod.TYPE_SIMDATA,0x00e9d7e7,INSTANCE,b'FAKE'+bytes(120),False)])
        self.assertIn('SIMDATA_HEADER_INVALID',[x['code'] for x in mod.inspect_bytes(blob)['findings']])

    def test_category_xml_identity_mismatch_blocked(self):
        blob=package([(mod.TYPE_CATEGORY,0,INSTANCE,XML.replace(str(INSTANCE).encode(),b'123'),False),
                      (mod.TYPE_SIMDATA,0x00e9d7e7,INSTANCE,SIMDATA,False)])
        self.assertIn('CATEGORY_ID_MISMATCH',[x['code'] for x in mod.inspect_bytes(blob)['findings']])

    def test_corrupt_payload_rejected(self):
        blob=bytearray(package([(mod.TYPE_CATEGORY,0,INSTANCE,XML,True)]))
        blob[96]=255
        with self.assertRaises(mod.PackageError): mod.inspect_bytes(blob)

    def test_corrupt_index_rejected(self):
        blob=bytearray(package([(mod.TYPE_CATEGORY,0,INSTANCE,XML,True)]))
        struct.pack_into('<Q',blob,0x40,0xdeadbeef)
        with self.assertRaises(mod.PackageError): mod.inspect_bytes(blob)

    def test_duplicate_resources_rejected(self):
        item=(mod.TYPE_CATEGORY,0,INSTANCE,XML,False)
        with self.assertRaises(mod.PackageError):mod.inspect_bytes(package([item,item]))

if __name__ == '__main__':unittest.main()
