"""M114: link original BouncerRequest filter + no-show as TWO reversible stages.

This module is NOT an installable Sims mod. No EA class is patched by import
or by build_school_bouncer_pair(). A future independently verified EA runtime
provider must supply the actual BouncerRequest owner, a verified
school-only empty filter and in-game gate evidence.

The same SchoolFilterScope object is shared by both stages so that
clone_for_replace() can only be blocked for requests whose exact native
Base/Core guest invitation was prepared by the M108 session. The owner
must declare all three BouncerRequest methods itself: inherited or
split-owner EA methods are deliberately not patched.
"""
from mhs108_school_filter_scope import (
    SchoolFilterScope, REQUIRED_FILTER_PROOF,
    install_offline_only as install_school_scope,
)
from mhs108_no_show_guard import (
    SchoolNoShowGuard, REQUIRED_NO_SHOW_PROOFS,
    install_offline_only as install_no_show_guard,
)
from mhs109_native_hook_stage import M109NativeStage

EXPECTED_BOUNCER_OWNER = 'situations.bouncer.bouncer_request.BouncerRequest'
REQUIRED_DESCRIPTORS = (
    '__init__', 'get_additional_filter_terms', 'clone_for_replace',
)


def _valid_owner(owner):
    """Do not patch a subclass, inherited methods, or a guessed class."""
    if not isinstance(owner, type):
        return False
    if owner.__module__ + '.' + owner.__name__ != EXPECTED_BOUNCER_OWNER:
        return False
    for name in REQUIRED_DESCRIPTORS:
        value = owner.__dict__.get(name)
        if not callable(value):
            return False
        for marker in ('_mhs108_school_filter',
                       '_mhs108_no_show_guard', '_mhs113_entry'):
            if getattr(value, marker, False) is True:
                return False
    return True


class M114SchoolBouncerPair(object):
    def __init__(self, owner, scope):
        self.owner = owner
        self.scope = scope
        self.guard = SchoolNoShowGuard(scope)
        self.installs = ()
        self._stages = None

    def stage_graph(self, filter_proofs, no_show_proofs):
        """Only convert to two install/restore stages with evidence.

        Supplying dictionaries of True in a unit test is NOT game proof.
        The real M113 caller must obtain these from independently verified
        Bouncer hooks/tuning/capacity observations before using the graph.
        """
        if (self._stages is not None
                or not isinstance(filter_proofs, dict)
                or not isinstance(no_show_proofs, dict)
                or any(filter_proofs.get(key) is not True
                       for key in REQUIRED_FILTER_PROOF)
                or any(no_show_proofs.get(key) is not True
                       for key in REQUIRED_NO_SHOW_PROOFS)):
            return None
        stages = {}

        def clear_scoped_filters():
            self.scope.restore()
            return self.scope.snapshot()['tracked_requests'] == 0

        def install_filter(_manifest, _evidence):
            return install_school_scope(self.owner, self.scope,
                                        filter_proofs)

        def install_guard(_manifest, _evidence):
            return install_no_show_guard(self.owner, self.guard,
                                         no_show_proofs)

        # M109NativeStage stores original EA descriptors before install,
        # handles partial mutation and refuses unknown third-party edits.
        stages['school_filter_scope'] = M109NativeStage(
            'school_filter_scope', self.owner,
            install_filter, cleanup=clear_scoped_filters)
        stages['no_show_guard'] = M109NativeStage(
            'no_show_guard', self.owner, install_guard)
        self._stages = stages
        return {name: stage.as_stage() for name, stage in stages.items()}

    def snapshot(self):
        return {
            'kind': 'M114_ORIGINAL_EA_BOUNCER_STAGE_PAIR_OFFLINE_ONLY',
            'owner_name': self.owner.__module__+'.'+self.owner.__name__,
            'two_reversible_stages_constructed': self._stages is not None,
            'student_invitation_receipt_required': True,
            'real_runtime_evidence_provider_connected': False,
            'game_bouncer_modified': False,
            'live_filter_admission_verified': False,
            'native_student_role_assignment_verified': False,
            'roster_16_verified': False,
        }


def build_school_bouncer_pair(session, request_owner, blank_filter,
                              teen_age, human_species, sim_info_lookup,
                              context_provider):
    """Return (pair, reason); construction is read-only, no EA mutations."""
    if not _valid_owner(request_owner):
        return None, 'BOUNCER_REQUEST_OWNER_NOT_VERIFIED'
    if (not callable(getattr(session,'has_native_student_invitation',None))
            or not getattr(session,'_local_core_holds',None)):
        return None, 'NATIVE_EA_GUEST_SESSION_NOT_READY'
    if not callable(sim_info_lookup) or not callable(context_provider):
        return None, 'LIVE_EA_SIM_INFO_OR_CONTEXT_LOOKUP_MISSING'
    try:
        scope = SchoolFilterScope(
            session, blank_filter, teen_age, human_species,
            sim_info_lookup, context_provider)
        return M114SchoolBouncerPair(request_owner, scope), (
            'ORIGINAL_EA_BOUNCER_STAGE_PAIR_CONSTRUCTED_NOT_ACTIVATED')
    except (ValueError,TypeError,AttributeError) as exc:
        return None,'BOUNCER_SCOPE_CONSTRUCTION_FAILED_'+type(exc).__name__


def compose_m113_late_graph(other_stages, bouncer_pair):
    """Supply only missing names; no fake stages for not-yet-proven hooks."""
    if (not isinstance(other_stages,dict)
            or set(other_stages) != {
                'native_precreate','unified_lessons','post_bouncer_observer'}
            or not isinstance(bouncer_pair,dict)
            or set(bouncer_pair) != {
                'school_filter_scope','no_show_guard'}):
        return None
    graph = dict(other_stages)
    graph.update(bouncer_pair)
    for stage in graph.values():
        if (not isinstance(stage,dict)
                or set(stage) != {'install','restore'}
                or not callable(stage['install'])
                or not callable(stage['restore'])):
            return None
    return graph
