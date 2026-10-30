"""Read-only source audit for Lot51-exported category and its SimData XML.

A SimData.xml export is NOT the binary SimData resource placed in a .package.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

CATEGORY_ID = 14567074618947653827
CATEGORY_KEY = '0x3FCE8D06'
M1 = Path(__file__).resolve().parents[1] / 'src' / 'experiments' / 'm1_unbuilt'
TUNING = M1 / '03E9D964!00000000!CA28A52FAEFBD0C3.Iliyana_MHS_MainMenu.xml'
SIMDATA = M1 / '545AC67A!00E9D967!CA28A52FAEFBD0C3.Iliyana_MHS_MainMenu.SimData.xml'


class PairError(ValueError):
    pass


def check_pair(category=TUNING, simdata=SIMDATA):
    category, simdata = Path(category), Path(simdata)
    c = ET.parse(str(category)).getroot()
    s = ET.parse(str(simdata)).getroot()
    if c.tag != 'I' or c.attrib.get('c') != 'PieMenuCategory':
        raise PairError('Not a PieMenuCategory tuning')
    if c.attrib.get('n') != 'Iliyana:MHS_MainMenu':
        raise PairError('Unexpected tuning name')
    if c.attrib.get('s') != str(CATEGORY_ID):
        raise PairError('Tuning Instance ID mismatch')
    if s.tag != 'SimData':
        raise PairError('Not SimData XML source')
    i = s.find('./Instances/I')
    if i is None or i.attrib.get('name') != c.attrib['n'] or i.attrib.get('schema') != c.attrib['c']:
        raise PairError('SimData name/schema not aligned')
    key_c = c.find('./T[@n="_display_name"]')
    key_s = i.find('./T[@name="_display_name"]')
    if key_c is None or key_s is None or key_c.text != CATEGORY_KEY or key_s.text != key_c.text:
        raise PairError('Display STBL key mismatch')
    for path, expected_type, expected_group in ((category, '03E9D964', '00000000'),
                                                  (simdata, '545AC67A', '00E9D967')):
        m = re.match(r'^([0-9A-F]{8})!([0-9A-F]{8})!([0-9A-F]{16})\.',path.name)
        if m is None or m.group(1) != expected_type or m.group(2) != expected_group or int(m.group(3),16) != CATEGORY_ID:
            raise PairError('Incorrect resource name (TGI): '+path.name)
    return {'name':c.attrib['n'],'id':CATEGORY_ID,'display_name_key':CATEGORY_KEY,'status':'XML_SOURCES_MATCH_ONLY'}


if __name__ == '__main__':
    print(check_pair())
