"""Compare M1 XML with confirmed patterns in the user's EA 1.129 and Sonozaki 2.2.1 samples.

Reference existence is NOT a TDESC validation and is NOT proof of game startup.
The original third-party/EA files are never copied into this repository.
"""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

F = Path(__file__).resolve().parents[1] / "src" / "experiments" / "m1_unbuilt"
PICKER = "interactions.base.picker_interaction"
CONFIRM = "interactions.base.immediate_interaction"
NOTICE = ("./V[@n='outcome']/U[@n='single']/U[@n='actions']/"
          "L[@n='basic_extras']/V[@t='notification']/U[@n='notification']")
EA_GAME_VERSION = "1.129.39.1230"
LOT51_TDESC_VERSION = "1.128.90"


class ReviewError(ValueError):
    pass


def inspect():
    supported = []
    for klass in (1, 2):
        picker = ET.parse(F / ("ChooseClass%d.xml" % klass)).getroot()
        confirm = ET.parse(F / ("ConfirmClass%d.xml" % klass)).getroot()
        if (picker.get("c"), picker.get("m")) != ("SimPickerInteraction", PICKER):
            raise ReviewError("Not a native SimPickerInteraction")
        if (confirm.get("c"), confirm.get("m")) != ("ImmediateSuperInteraction", CONFIRM):
            raise ReviewError("Not a native ImmediateSuperInteraction")
        for path in ("./L[@n='actor_continuation']/U/T[@n='affordance']",
                     "./V[@n='picker_dialog'][@t='sim_picker']/U[@n='sim_picker']",
                     "./T[@n='category']", "./L[@n='sim_tests']", "./L[@n='test_globals']"):
            if picker.find(path) is None:
                raise ReviewError("Missing picker path: " + path)
        notice = confirm.find(NOTICE)
        if notice is None or notice.find("./V[@n='dialog']") is None:
            raise ReviewError("Notification is not inside the observed outcome path")

        # Sonozaki has SEVEN other SimPickerInteraction tunings with this EXACT
        # sim_info who=PickedSim TEEN pattern (including removal of classmates).
        actor = picker.find("./L[@n='sim_tests']/L/V[@t='sim_info']/U[@n='sim_info']")
        if actor is None:
            raise ReviewError("PickedSim info-test absent")
        who = actor.find("./E[@n='who']")
        ages = [e.text for e in actor.findall("./V[@n='ages']/L/E")]
        if who is None or who.text != "PickedSim" or ages != ["TEEN"]:
            raise ReviewError("Selected teenager test differs from supported exemplar")
        supported.append({"class": klass, "pattern": "PICKEDSIM_SIM_INFO_TEEN",
                          "reference": "Sonozaki 2.2.1, Remove_Classmates and other SimPickers"})

        literal = notice.find("./V[@n='dialog']/V[@n='single']/U[@n='literal']")
        if literal is None or literal.find("./V[@n='title'][@t='enabled']/T[@n='enabled']") is None:
            raise ReviewError("Notification title not in the EA-observed form")
        supported.append({"class": klass, "pattern": "NOTIFICATION_TITLE",
                          "reference": "EA immediate_HighSchool_Active_CheckClassSchedule"})

        if notice.find("./V[@n='timing'][@t='at_beginning']") is None:
            raise ReviewError("Notification timing does not match observed EA form")
        supported.append({"class": klass, "pattern": "NOTIFICATION_TIMING_AT_BEGINNING",
                          "reference": "EA mixer_Social_Fight_HighSchool_Active_SchoolFight"})

    return {
        "status": "PATTERNS_SUPPORTED_NOT_GAME_VALIDATED",
        "ea_version": EA_GAME_VERSION,
        "lot51_tdesc_version": LOT51_TDESC_VERSION,
        "supported_patterns": supported,
        "open_checks": [
            "Complete tuning/TDESC comparison for actual game version 1.129",
            "Picker population and played-household coverage in game",
            "XML Injector activation, STBL linking and full-package integrity",
            "The Sims 4 startup and in-game menu behavior"
        ],
        "release_ready": False
    }


if __name__ == "__main__":
    print(json.dumps(inspect(), indent=2))
