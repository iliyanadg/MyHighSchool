"""Static reference check only. No game-load validation."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
F=Path(__file__).resolve().parents[1]/"src"/"experiments"/"m1_unbuilt"
PICKER="interactions.base.picker_interaction"
CONFIRM="interactions.base.immediate_interaction"
NOTIFICATION="./V[@n='outcome']/U[@n='single']/U[@n='actions']/L[@n='basic_extras']/V[@t='notification']/U[@n='notification']/V[@n='dialog']"

class ReviewError(ValueError): pass

def inspect():
    findings=[]
    for klass in (1,2):
        picker=ET.parse(F/("ChooseClass%d.xml"%klass)).getroot()
        confirm=ET.parse(F/("ConfirmClass%d.xml"%klass)).getroot()
        if (picker.get("c"),picker.get("m"))!=("SimPickerInteraction",PICKER):
            raise ReviewError("Not a native SimPickerInteraction")
        if (confirm.get("c"),confirm.get("m"))!=("ImmediateSuperInteraction",CONFIRM):
            raise ReviewError("Not a native ImmediateSuperInteraction")
        for path in ("./L[@n='actor_continuation']/U/T[@n='affordance']",
                     "./V[@n='picker_dialog'][@t='sim_picker']/U[@n='sim_picker']",
                     "./T[@n='category']", "./L[@n='sim_tests']", "./L[@n='test_globals']"):
            if picker.find(path) is None:raise ReviewError("Picker lacks reference shape: "+path)
        if confirm.find(NOTIFICATION) is None:raise ReviewError("Notification nesting differs from reference")
        if picker.find(".//E[@n='who'][.='PickedSim']") is not None:
            findings.append({"class":klass,"code":"PICKEDSIM_AGE_TEST_UNVERIFIED"})
        if confirm.find(".//V[@n='title'][@t='enabled']") is not None:
            findings.append({"class":klass,"code":"NOTIFICATION_TITLE_UNVERIFIED"})
        if confirm.find(".//V[@n='timing'][@t='at_beginning']") is not None:
            findings.append({"class":klass,"code":"NOTIFICATION_TIMING_UNVERIFIED"})
    return {"status":"NOT_READY_FOR_GAME","ea_version":"1.129.39.1230","lot51_tdesc_version":"1.128.90",
            "matched":"Native picker and notification structure as seen in user-supplied Sonozaki 2.2.1",
            "review_items":findings,"release_ready":False,
            "note":"Unverified tunables are not proven errors or proven causes of startup failure."}

if __name__=="__main__":print(json.dumps(inspect(),indent=2))
