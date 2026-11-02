"""M108 school-only Bouncer filter overlay, a *disabled* research adapter.

EA Bouncer uses request._sim_filter and request.get_additional_filter_terms()
in four paths: already-instanced matching, looking-for-work, zone spin-up
spawning and running-zone spawning. A Sim ID constraint alone does not make
a Sim pass EA's original job filter.

This module isolates a potential filter substitution to one explicitly
requested, verified teen NPC in the *original* EA Base/Core school situation.
It NEVER changes SituationJob.filter, the Sim's traits, EA filter service,
global blacklists, or an unrelated BouncerRequest. No runtime installer
imports this module; all proof flags are false until measured in game.
"""
import weakref

BASE_SITUATION = 277733
CORE_SITUATION = 298052
BASE_JOB = 277894
CORE_JOBS = (278965, 278966, 278967, 278968, 303765)
SCHOOL_SCHEDULES = (277657, 279958)

REQUIRED_FILTER_PROOF = (
    'native_school_bouncer_origin_verified',
    'exact_student_invitation_prepared_before_ea',
    'school_only_filter_tuning_verified',
    'job_additional_terms_scope_verified',
    'no_show_replacement_protected',
    'blacklist_and_exclusivity_preserved',
    'original_bouncer_request_class_verified',
)


def _guid(item):
    if item is None:
        return None
    for obj in (item, getattr(item, 'tuned_class', None), type(item)):
        value = getattr(obj, 'guid64', None)
        if type(value) is int and value > 0:
            return value
    return None


def _id(value):
    if type(value) not in (int, str) or not str(value).isdigit():
        return None
    num = int(value)
    return num if num > 0 and str(num) == str(value) else None


class SchoolFilterScope(object):
    """One save/day/school-zone selection policy, no EA imports."""

    def __init__(self, native_guest_session, blank_filter, teen_age,
                 human_species, sim_info_lookup, context_provider):
        if (not callable(sim_info_lookup) or not callable(context_provider)
                or blank_filter is None
                or not callable(getattr(blank_filter, 'get_filter_terms', None))
                or not getattr(native_guest_session, '_local_core_holds', None)):
            raise ValueError('M108 school-only filter prerequisites absent')
        self.guests = native_guest_session
        self.manifest = native_guest_session.manifest
        self.blank_filter = blank_filter
        self.teen_age = teen_age
        self.human_species = human_species
        self.lookup = sim_info_lookup
        self.context_provider = context_provider
        self._tracked = weakref.WeakKeyDictionary()
        self.accepted_proposals = 0

    def _context_ok(self):
        try:
            data = self.context_provider()
            return (type(data) is dict
                    and data.get('native_school_bouncer_origin_verified') is True
                    and data.get('school_verified') is True
                    and data.get('schedule_guid') in SCHOOL_SCHEDULES
                    and str(data.get('save_slot')) == self.manifest['save_slot']
                    and type(data.get('sim_day')) is int
                    and data['sim_day'] == self.manifest['sim_day']
                    and str(data.get('zone_id')) == self.manifest['school_zone'])
        except (TypeError, KeyError, ValueError):
            return False

    def _expected_for_request(self, request):
        job = _guid(getattr(request, '_job_type', None))
        situation = _guid(getattr(request, '_situation', None))
        if job == BASE_JOB and situation == BASE_SITUATION:
            return frozenset(self.manifest['base_ids'])
        if job in CORE_JOBS and situation == CORE_SITUATION:
            return frozenset(sid for core_job, sid in
                             self.guests._local_core_holds if core_job == job)
        return frozenset()

    def eligible(self, request):
        """Reject every generic, replacement, mismatched or playable request."""
        if not self._context_ok():
            return False
        requested = _id(getattr(request, '_requested_sim_id', None))
        if requested is None:
            return False
        expected = self._expected_for_request(request)
        if str(requested) not in expected:
            return False
        constrained = getattr(request, '_constrained_sim_ids', None)
        if (type(constrained) not in (set, frozenset, tuple, list)
                or len(constrained) != 1 or requested not in constrained):
            return False
        if (getattr(request, '_continue_if_constraints_fail', None) is not False
                or getattr(request, '_for_persisted_sim', None) is not False):
            return False
        job_type = getattr(request, '_job_type', None)
        if getattr(request, '_sim_filter', None) is not getattr(job_type, 'filter', None):
            return False
        # No role mutation or generalized bypass: age, species and existing
        # NPC identity are independently verified from live SimInfo.
        try:
            info = self.lookup(requested)
            if (info is None or _id(getattr(info, 'sim_id', None)) != requested
                    or getattr(info, 'age', None) != self.teen_age
                    or getattr(info, 'species', None) != self.human_species
                    or getattr(info, 'is_selectable', True) is not False):
                return False
        except Exception:
            return False
        return True

    def apply(self, request):
        """Change *request* only; leave its job tuning and SimInfo intact."""
        if not self.eligible(request) or request in self._tracked:
            return False
        prior = request._sim_filter
        try:
            self._tracked[request] = prior
            request._sim_filter = self.blank_filter
            self.accepted_proposals += 1
            return True
        except (AttributeError, TypeError):
            try:
                self._tracked.pop(request, None)
            except TypeError:
                pass
            return False

    def is_tracked(self, request):
        """Only requests from this scope can skip additional job filter terms."""
        try:
            return (request in self._tracked
                    and request._sim_filter is self.blank_filter
                    and self._context_ok()
                    and str(_id(getattr(request, '_requested_sim_id', None)))
                    in self._expected_for_request(request))
        except (TypeError, AttributeError):
            return False

    def release(self, request):
        """Fail back to the original terms and filter when context changes."""
        try:
            if request not in self._tracked:
                return False
            prior = self._tracked.pop(request)
            if getattr(request, '_sim_filter', None) is self.blank_filter:
                request._sim_filter = prior
            return True
        except (TypeError, AttributeError):
            return False

    def restore(self):
        """Restore the exact original filter on all still-live requests."""
        for request in tuple(self._tracked):
            self.release(request)

    def snapshot(self):
        return {
            'kind': 'M108_OFFLINE_ONLY_SCHOOL_REQUEST_FILTER_SCOPE',
            'requests_proposed': self.accepted_proposals,
            'tracked_requests': len(self._tracked),
            'native_filter_runtime_verified': False,
            'native_bouncer_assignment_verified': False,
            'attendance_verified': False,
        }


def install_offline_only(request_class, scope, live_proofs):
    """Simulate request-scoped EA BouncerRequest interception, not shipped.

    This hook is inert unless every externally proven gate is True. The
    current branch has NO live caller that can supply those proofs.
    """
    if (not isinstance(live_proofs, dict)
            or any(live_proofs.get(key) is not True
                   for key in REQUIRED_FILTER_PROOF)
            or not isinstance(scope, SchoolFilterScope)):
        return None
    previous_init = getattr(request_class, '__init__', None)
    previous_terms = getattr(request_class, 'get_additional_filter_terms', None)
    if (not callable(previous_init) or not callable(previous_terms)
            or getattr(previous_init, '_mhs108_school_filter', False)
            or getattr(previous_terms, '_mhs108_school_filter', False)):
        return None

    def init_wrapper(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        # Never affect construction errors or retry EA's constructor.
        scope.apply(self)

    def terms_wrapper(self):
        if scope.is_tracked(self):
            return ()
        # If the request left the verified school/save/day context,
        # revert the request's own filter before returning EA terms.
        scope.release(self)
        return previous_terms(self)

    init_wrapper._mhs108_school_filter = True
    terms_wrapper._mhs108_school_filter = True
    request_class.__init__ = init_wrapper
    request_class.get_additional_filter_terms = terms_wrapper

    def uninstall():
        if (request_class.__init__ is not init_wrapper
                or request_class.get_additional_filter_terms
                is not terms_wrapper):
            return False
        request_class.__init__ = previous_init
        request_class.get_additional_filter_terms = previous_terms
        scope.restore()
        return True

    return uninstall
