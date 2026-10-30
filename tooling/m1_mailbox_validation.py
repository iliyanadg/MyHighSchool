"""Check experimental M1 UI/mailbox injection against XML Injector v4.2 shape.

The official XML Injector v4.2 modder example uses add_interactions_to_objects,
an object_list selection for standard/wall mailboxes, and _super_affordances.
This is a static *schema-shape* check, NOT EA tuning/launch validation.
"""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
M1 = ROOT / 'src' / 'experiments' / 'm1_unbuilt'
INJECTOR = M1 / 'Injector.xml'
VALID_IDS = ('10604127343160706865', '10604124044625822232')
MAILBOX_IDS = ('14940', '133176')
CATEGORY_ID = '14567074618947653827'


class MailboxValidationError(ValueError):
    pass


def _text_values(elements):
    return tuple((item.text or '').strip() for item in elements)


def validate_injector(path=INJECTOR):
    root = ET.parse(str(path)).getroot()
    for key, expected in {
        'c':'XmlInjector', 'i':'snippet', 'm':'xml_injector.snippet',
        'n':'Iliyana:MHS_M1_Mailbox_Injector',
        's':'2184544182686720149'
    }.items():
        if root.get(key) != expected:
            raise MailboxValidationError('Wrong injector {}'.format(key))

    entries = root.findall('./L[@n="add_interactions_to_objects"]/U')
    if len(entries) != 1:
        raise MailboxValidationError('Expected exactly one object injection group')
    entry = entries[0]
    selection = entry.find('./V[@n="object_selection"]')
    if selection is None or selection.get('t') != 'object_list':
        raise MailboxValidationError('Not XML Injector object_list variant')

    targets = _text_values(entry.findall(
        './V[@n="object_selection"]/U[@n="object_list"]/L[@n="object_list"]/T'))
    if targets != MAILBOX_IDS:
        raise MailboxValidationError('Expected supported mailbox tuning IDs')
    affordances = _text_values(entry.findall('./L[@n="_super_affordances"]/T'))
    if affordances != VALID_IDS:
        raise MailboxValidationError('Injected affordances do not match the pickers')
    if 'lot51_core' in ET.tostring(root, encoding='unicode'):
        raise MailboxValidationError('Must not silently mix injector frameworks')

    for number, expected in enumerate(VALID_IDS, 1):
        picker=ET.parse(str(M1/('ChooseClass'+str(number)+'.xml'))).getroot()
        if (picker.get('c') != 'SimPickerInteraction'
                or picker.get('m') != 'interactions.base.picker_interaction'
                or picker.get('s') != expected):
            raise MailboxValidationError('Bad native picker identity')
        category=picker.find('./T[@n="category"]')
        if category is None or category.text.strip() != CATEGORY_ID:
            raise MailboxValidationError('Picker references wrong menu')
        teen_test=picker.findall('.//L[@n="sim_tests"]//E')
        if not any((x.text or '').strip() == 'TEEN' for x in teen_test):
            raise MailboxValidationError('No teenage candidate test')

    return {'status':'STATIC_SCHEMA_SHAPE_ONLY',
            'mailbox_object_ids':list(MAILBOX_IDS),
            'affordance_ids':list(VALID_IDS),
            'category_id':CATEGORY_ID,
            'dependency':'XML Injector v4.2',
            'limitations':'Game loading, TDESC validity and mailbox menu display not tested'}


if __name__=='__main__':
    print(validate_injector())
