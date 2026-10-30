"""Static checks of failed M0 tuning. Does not validate game load/startup."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

NAMES = ("Category", "ChooseClass1", "ChooseClass2", "ConfirmClass1", "ConfirmClass2", "Injector")

def audit(folder, inventory, alternatives=None):
    folder = Path(folder)
    alternatives = alternatives or {}
    roots = {}
    issues = []
    for name in NAMES:
        try:
            content = alternatives[name] if name in alternatives else (folder / (name + ".xml")).read_bytes()
            roots[name] = ET.fromstring(content)
        except (OSError, ET.ParseError) as exc:
            issues.append("XML_UNREADABLE:" + name)
    if len(roots) != len(NAMES):
        return sorted(set(issues))
    try:
        ids = {name: int(root.attrib["s"]) for name, root in roots.items()}
    except (ValueError, KeyError):
        return ["INVALID_TUNING_ID"]
    if len(set(ids.values())) != len(NAMES):
        issues.append("DUPLICATE_TUNING_ID")
    if ids["Category"] not in {int(v) for v in inventory.get("simdata_instances", [])}:
        issues.append("MISSING_CATEGORY_SIMDATA")
    for number in (1, 2):
        picker = roots["ChooseClass" + str(number)]
        category = picker.find('./T[@n="category"]')
        if category is None or (category.text or "").strip() != str(ids["Category"]):
            issues.append("PICKER_CATEGORY_LINK:" + str(number))
        link = picker.find('./L[@n="actor_continuation"]/U/T[@n="affordance"]')
        if link is None or (link.text or "").strip() != str(ids["ConfirmClass" + str(number)]):
            issues.append("PICKER_CONTINUATION_LINK:" + str(number))
        count = picker.find('.//T[@n="number_selectable"]')
        if count is None or (count.text or "").strip() != "8":
            issues.append("PICKER_LIMIT:" + str(number))
        confirmation = roots["ConfirmClass" + str(number)]
        if confirmation.find('./L[@n="basic_extras"]') is not None:
            issues.append("CONFIRM_EXTRAS_AT_ROOT:" + str(number))
        if confirmation.find('./V[@n="outcome"]/U[@n="single"]/U[@n="actions"]/L[@n="basic_extras"]/V[@t="notification"]') is None:
            issues.append("CONFIRM_NOTIFICATION_NOT_IN_OUTCOME:" + str(number))
    links = set()
    for node in roots["Injector"].findall('./L[@n="add_interactions_to_objects"]/U/L[@n="_super_affordances"]/T'):
        try:
            links.add(int(node.text.strip()))
        except (TypeError, ValueError):
            issues.append("INVALID_INJECTOR_LINK")
    if links != {ids["ChooseClass1"], ids["ChooseClass2"]}:
        issues.append("INJECTOR_PICKER_LINK_MISMATCH")
    return sorted(set(issues))

def main():
    root = Path(__file__).resolve().parents[1]
    folder = root / "src" / "experiments" / "m0_failed"
    inventory = json.loads((folder / "resource_inventory.json").read_text(encoding="utf-8"))
    for issue in audit(folder, inventory):
        print("M0 DIAGNOSTIC:", issue)
    print("No game compatibility claim: no build or EA runtime involved.")

if __name__ == "__main__":
    main()
