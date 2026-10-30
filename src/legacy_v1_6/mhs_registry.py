"""MY HIGH SCHOOL — pure-Python roster core v0.1.

Independent from Sims 4 APIs. The adapter that reads real Sims and persists
per save must be developed and validated separately.
NO attendance tracking, illnesses, or absence justification.
Python 3.7-compatible source (NOT a game-loadable .ts4script).
"""
import json


class RosterError(ValueError):
    pass


class SchoolRoster(object):
    VERSION = 1
    MAX_PER_CLASS = 8

    def __init__(self, save_key, capacities=None):
        if not save_key or not isinstance(save_key, str):
            raise RosterError("save_key must be a nonempty string")
        self.save_key = save_key
        self.capacities = dict(capacities or {1: 8, 2: 8})
        self.assignments = {}  # stable Sim ID string => class number
        self.alumni = []  # graduates only; NOT attendance history
        self._validate_capacities()

    def _validate_capacities(self):
        if not self.capacities:
            raise RosterError("At least one class must exist")
        for klass, capacity in self.capacities.items():
            if type(klass) is not int or klass < 1 or klass > 4:
                raise RosterError("Classes must be numbered 1 to 4")
            if type(capacity) is not int or capacity < 1 or capacity > self.MAX_PER_CLASS:
                raise RosterError("Class capacity must be 1 to 8")

    @staticmethod
    def _id(sim_id):
        if isinstance(sim_id, bool):
            raise RosterError("Invalid Sim ID")
        try:
            value = int(sim_id)
        except (ValueError, TypeError, OverflowError):
            raise RosterError("Invalid Sim ID")
        if value <= 0 or str(value) != str(sim_id).strip():
            raise RosterError("Invalid Sim ID")
        return str(value)

    def list_class(self, klass):
        self._class(klass)
        return sorted((s for s, c in self.assignments.items() if c == klass), key=int)

    def _class(self, klass):
        if type(klass) is not int or klass not in self.capacities:
            raise RosterError("Class is not active")

    def enroll(self, sim_id, klass, is_teen):
        """Enrol/move a teen. Never enrol an ineligible Sim or exceed capacity."""
        sid = self._id(sim_id)
        self._class(klass)
        if is_teen is not True:
            raise RosterError("Only eligible teen Sims may be enrolled")
        old_class = self.assignments.get(sid)
        if old_class == klass:
            return False
        if len(self.list_class(klass)) >= self.capacities[klass]:
            raise RosterError("The destination class is full")
        self.assignments[sid] = klass
        return True

    def swap(self, sim_a, sim_b):
        """Swap students already enrolled in different classes."""
        a, b = self._id(sim_a), self._id(sim_b)
        if a not in self.assignments or b not in self.assignments:
            raise RosterError("Both students must be enrolled")
        if self.assignments[a] == self.assignments[b]:
            return False
        self.assignments[a], self.assignments[b] = self.assignments[b], self.assignments[a]
        return True

    def withdraw(self, sim_id):
        """Remove from our custom registry ONLY; never delete Sims from the game."""
        return self.assignments.pop(self._id(sim_id), None) is not None

    def graduate(self, sim_id):
        sid = self._id(sim_id)
        klass = self.assignments.pop(sid, None)
        if klass is not None:
            self.alumni.append({"sim_id": sid, "former_class": klass})
            return True
        return False

    def set_capacity(self, klass, capacity):
        self._class(klass)
        if type(capacity) is not int or not 1 <= capacity <= self.MAX_PER_CLASS:
            raise RosterError("Capacity must be 1 to 8")
        if len(self.list_class(klass)) > capacity:
            raise RosterError("Cannot shrink below current enrollment")
        self.capacities[klass] = capacity

    def to_dict(self):
        return {"version": self.VERSION, "save_key": self.save_key,
                "capacities": {str(k): v for k, v in self.capacities.items()},
                "assignments": dict(self.assignments), "alumni": list(self.alumni)}

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)

    @classmethod
    def from_json(cls, raw):
        data = json.loads(raw)
        if data.get("version") != cls.VERSION:
            raise RosterError("Unsupported roster version")
        capacities = {int(k): v for k, v in data["capacities"].items()}
        # Read old prototype registries that allowed 9/10: never increase their
        # physical places. Tighten capacity to 8 in memory, only if they have
        # no more than 8 enrolled. Refuse overfull files WITHOUT overwriting.
        for klass, capacity in capacities.items():
            if type(capacity) is not int or capacity < 1 or capacity > 10:
                raise RosterError('Invalid stored capacity')
            capacities[klass] = min(capacity, cls.MAX_PER_CLASS)
        roster = cls(data["save_key"], capacities)
        for sid, klass in data["assignments"].items():
            roster._id(sid)
            roster._class(klass)
            if len(roster.list_class(klass)) >= roster.capacities[klass]:
                raise RosterError("Corrupt saved roster: class capacity exceeded")
            roster.assignments[sid] = klass
        roster.alumni = list(data.get("alumni", []))
        return roster

    def without_enrollment_change(self, sim_id, absent_today=True):
        """Intended truancy/absence has no effect on enrollment."""
        return self.assignments.get(self._id(sim_id))
