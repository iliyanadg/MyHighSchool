"""M90: session-scoped roster resolver for the existing EA Base Student slots.

Pure Python 3.7. No EA hooks or disk access. This decides the next eligible
registered NPC before M89 attempts the *same* EA creation request.
"""
class SelectionSession(object):
    def __init__(self, class_ids, playable_ids=(), excluded_ids=()):
        self.roster=tuple(str(x) for group in class_ids for x in group)
        self.playable=frozenset(str(x) for x in playable_ids)
        self.excluded=frozenset(str(x) for x in excluded_ids)
        self.assigned=set()
        self.issued=0
        if len(set(self.roster))!=len(self.roster):
            raise ValueError('duplicated registered Sim IDs')
        if any(not s.isdigit() or int(s)<1 for s in self.roster):
            raise ValueError('invalid registered Sim ID')

    def choose(self, eligible_ids, physically_present_ids=()):
        eligible=frozenset(str(x) for x in eligible_ids)
        present=frozenset(str(x) for x in physically_present_ids)
        for sid in self.roster:
            if (sid in eligible and sid not in self.playable and
                    sid not in self.excluded and sid not in self.assigned and
                    sid not in present):
                return int(sid)
        return None

    def confirm(self, sid):
        """Only call AFTER M89 successfully applied the replacement."""
        value=str(sid)
        if value not in self.roster or value in self.assigned:
            return False
        self.assigned.add(value)
        self.issued+=1
        return True
