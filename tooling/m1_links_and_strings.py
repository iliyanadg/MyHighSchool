"""Verify M1 native menu link chain and localization keys (offline only).

Does not validate EA tuning schemas, mailbox injections, Sim picker behavior or game startup.
"""
from pathlib import Path
import json
import re
import struct
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
M1 = ROOT / 'src' / 'experiments' / 'm1_unbuilt'
LOCALIZATION = M1 / 'localization.json'
CATEGORY_ID = '14567074618947653827'
PICKER_IDS = {'1': '10604127343160706865', '2': '10604124044625822232'}
CONFIRM_IDS = {'1': '13813934116852558422', '2': '13813933017340930211'}
CATEGORY_FILE = M1 / '03E9D964!00000000!CA28A52FAEFBD0C3.Iliyana_MHS_MainMenu.xml'


class LinkError(ValueError):
    pass


def _must(root, path, expected, message):
    field = root.find(path)
    if field is None or (field.text or '').strip() != expected:
        raise LinkError(message)


def check_links():
    data = json.loads(LOCALIZATION.read_text(encoding='utf-8'))
    entries = data['entries']
    keys = {}
    for entry in entries:
        value = int(entry['key'], 16)
        if value in keys or not (0 <= value < 2**32):
            raise LinkError('Duplicate or invalid STBL key')
        for locale in ('it', 'en'):
            if not isinstance(entry.get(locale), str) or not entry[locale].strip():
                raise LinkError('Missing translation: ' + locale)
        keys[value] = entry

    if len(keys) != 9:
        raise LinkError('Expected exactly nine UI text keys')
    cat = ET.parse(CATEGORY_FILE).getroot()
    if cat.attrib.get('s') != CATEGORY_ID or cat.attrib.get('n') != 'Iliyana:MHS_MainMenu':
        raise LinkError('Category identity mismatch')
    used = set()
    key_regexp = re.compile(r'^0[xX][0-9a-fA-F]{8}$')

    def collect(root):
        for item in root.iter('T'):
            value = (item.text or '').strip()
            if key_regexp.fullmatch(value):
                used.add(int(value, 16))

    collect(cat)
    for klass in ('1', '2'):
        picker = ET.parse(M1 / ('ChooseClass' + klass + '.xml')).getroot()
        confirm = ET.parse(M1 / ('ConfirmClass' + klass + '.xml')).getroot()
        if picker.attrib.get('c') != 'SimPickerInteraction' or picker.attrib.get('s') != PICKER_IDS[klass]:
            raise LinkError('Picker identity mismatch for class ' + klass)
        if confirm.attrib.get('c') != 'ImmediateSuperInteraction' or confirm.attrib.get('s') != CONFIRM_IDS[klass]:
            raise LinkError('Confirm identity mismatch for class ' + klass)
        _must(picker, './T[@n="category"]', CATEGORY_ID, 'Menu category link wrong')
        _must(picker, './L[@n="actor_continuation"]/U/T[@n="affordance"]',
              CONFIRM_IDS[klass], 'Picker confirmation link wrong')
        _must(picker, './/T[@n="number_selectable"]', '8', 'Picker limit must remain eight')
        if picker.find('.//E[.="TEEN"]') is None:
            raise LinkError('Teen filter absent')
        if confirm.find('./V[@n="outcome"]/U[@n="single"]/U[@n="actions"]/L[@n="basic_extras"]/V[@t="notification"]') is None:
            raise LinkError('Notification not under expected outcome')
        collect(picker)
        collect(confirm)

    missing = sorted(used - set(keys))
    unused = sorted(set(keys) - used)
    if missing or unused:
        raise LinkError('STBL references mismatch: missing={} unused={}'.format(missing, unused))
    return {
      'status':'SOURCE_LINKS_COMPLETE_NOT_GAME_VALIDATED',
      'category_id':CATEGORY_ID, 'class_choices':2, 'max_selectable_per_picker':8,
      'referenced_text_keys':len(used),
      'languages':['it','en']
    }


def compile_stbl(locale):
    """Serialize original-format STBL for future vetted build; never package game resources."""
    data = json.loads(LOCALIZATION.read_text(encoding='utf-8'))
    if locale not in ('it', 'en'):
        raise LinkError('Unsupported locale')
    rows = sorted(((int(item['key'], 16), item[locale].encode('utf-8'))
                   for item in data['entries']), key=lambda row: row[0])
    if len(rows) != len({key for key, value in rows}):
        raise LinkError('Duplicate STBL key')
    payload = bytearray()
    for key, raw in rows:
        if len(raw) > 65535:
            raise LinkError('Translation too long')
        payload.extend(struct.pack('<IBH', key, 0, len(raw)))
        payload.extend(raw)
    header = b'STBL' + struct.pack('<HBQ2sI', 5, 0, len(rows), b'\x00\x00',
                                    sum(len(raw) + 1 for key,raw in rows))
    result = bytes(header + payload)
    locale_id = int(data['locales'][locale],16)
    low56 = int(data['instance_low_56_hex'],16)
    instance = (locale_id << 56) | low56
    return instance, result


def parse_stbl(payload):
    if len(payload) < 21 or payload[:4] != b'STBL':
        raise LinkError('STBL signature missing')
    version, compression, count, reserved, expected_bytes = struct.unpack_from('<HBQ2sI', payload, 4)
    if version != 5 or compression or reserved != b'\x00\x00':
        raise LinkError('Unsupported STBL header')
    position = 21
    decoded = {}
    total_bytes = 0
    for number in range(count):
        if position + 7 > len(payload):
            raise LinkError('STBL row truncated')
        key, flags, length = struct.unpack_from('<IBH', payload, position)
        position += 7
        if flags or position + length > len(payload) or key in decoded:
            raise LinkError('Malformed STBL row')
        decoded[key] = payload[position:position+length].decode('utf-8')
        position += length
        # Header stores size AS IF every string had a null terminator,
        # though UTF-8 entries in the file do not contain that terminator.
        total_bytes += length + 1
    if position != len(payload) or total_bytes != expected_bytes:
        raise LinkError('STBL count or trailing bytes mismatch')
    return decoded


if __name__ == '__main__':
    print(check_links())
    for locale in ('it','en'):
        instance, payload = compile_stbl(locale)
        print(locale, hex(instance), len(parse_stbl(payload)), 'entries')
