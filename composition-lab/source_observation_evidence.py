"""Original-observation identity, not a hidden source score or authenticity claim.

A digest can show that a policy is about to learn from changed input. It cannot
recover original observations. Migrated owners retain their semantic evidence;
unmigrated policies must refuse instead of blessing generated music as source.
"""
from functools import wraps
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
import re

CONTROLS = frozenset(('dynamics', 'accents', 'palm_mute', 'rhythm', 'tempo',
                      'melody', 'voicing', 'register', 'physical'))
DYNAMIC_POLICIES = frozenset(('source_local_dynamic_level', 'source_local_dynamic_transition'))
_CONTROL_UPDATE_ACTIVE = ContextVar('stable_pitch_control_update_active', default=False)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def operation_changes(before, after_melody, after, *, initial_relationships, final_relationships):
    """Report the complete realized edit, including cancellation between stages."""
    initial, middle, final = map(digest, (before, after_melody, after))
    return dict(changed=final != initial, melody_changed=middle != initial,
                register_changed=final != middle,
                relationships_changed=digest(initial_relationships) != digest(final_relationships))


def assert_only_parameter_changes(before, after, paths):
    """Preserve the complete model outside explicit EXISTING scalar leaves.

    This checks an update's history, not just standalone output validity. It
    cannot bless a constructor as an updater or prove source authenticity.
    Containers cannot be permitted wholesale: identities and memberships survive.
    """
    if (type(paths) not in (tuple, list)
            or any(type(path) is not tuple or not path
                   or any(type(key) not in (str, int) for key in path) for path in paths)
            or len(set(paths)) != len(paths)):
        raise ValueError('EXPLICIT_UNIQUE_PARAMETER_PATHS_REQUIRED')
    left, right = deepcopy(before), deepcopy(after)
    for path in paths:
        if type(path) is not tuple or not path:
            raise ValueError('EXPLICIT_EXISTING_SCALAR_PARAMETER_REQUIRED')
        for model in (left, right):
            parent = model
            for key in path[:-1]:
                if type(parent) is dict and type(key) is str and key in parent:
                    parent = parent[key]
                elif type(parent) is list and type(key) is int and 0 <= key < len(parent):
                    parent = parent[key]
                else:
                    raise ValueError('EXPLICIT_EXISTING_SCALAR_PARAMETER_REQUIRED')
            key = path[-1]
            if not (type(parent) is dict and type(key) is str and key in parent
                    or type(parent) is list and type(key) is int and 0 <= key < len(parent)):
                raise ValueError('EXPLICIT_EXISTING_SCALAR_PARAMETER_REQUIRED')
            if type(parent[key]) in (dict, list):
                raise ValueError('PARAMETER_SUBTREE_PERMISSION_FORBIDDEN')
            parent[key] = None
    if digest(left) != digest(right):
        raise ValueError('UPDATE_CHANGED_PROTECTED_STATE')


def origin(tier1):
    from source_fact_tier1 import validate
    validate(tier1)
    return dict(schema='declared-source-observation-origin/1', facts_sha256=digest(tier1))


def validate_origin(value):
    if (type(value) is not dict or set(value) != {'schema', 'facts_sha256'}
            or value['schema'] != 'declared-source-observation-origin/1'
            or type(value['facts_sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', value['facts_sha256']) is None):
        raise ValueError('Typed original-observation origin required')


def require(upper, controls):
    if type(controls) is not dict:
        raise ValueError('Explicit control mapping required')
    from connected_tier2 import realize
    current = realize(upper)
    if not any(type(controls.get(k)) in (int, float) and controls[k] > 0 for k in CONTROLS):
        return
    provenance = upper.get('source_origin')
    if provenance is None:
        raise ValueError('MISSING_ORIGINAL_OBSERVATIONS: reanalyze the captured input; legacy zero remains supported')
    validate_origin(provenance)
    from observed_expression import POLICIES as EXPRESSION_POLICIES, source_view
    if controls.get('context_policy') in EXPRESSION_POLICIES and source_view(upper,controls['context_policy']) is not None:
        return
    if controls.get('context_policy') in DYNAMIC_POLICIES and 'observed_dynamics' in upper['owned_parameters']:
        from observed_dynamics import validate
        validate(upper['owned_parameters']['observed_dynamics'], provenance)
        return
    if controls.get('context_policy') in ('source_guitar_figure_register', 'source_muted_figure_register') and 'figure_register_observations' in upper['owned_parameters']:
        from figure_register_observations import supported_controls, validate_current
        if supported_controls(controls):
            validate_current(upper)
            return
    if digest(current) != provenance['facts_sha256']:
        raise ValueError('UNSUPPORTED_CHAINED_EVIDENCE: policy has no retained original observations for this edited score')


def guarded(function):
    """Protect direct policy calls as well as dispatcher calls before mutation."""
    @wraps(function)
    def call(upper, controls):
        require(upper, controls)
        return function(upper, controls)
    return call


def controlled_update(function):
    """Apply saved stable-pitch intent at every supported public edit boundary.

    The operation works on a copy when a preference is attached. A refusal cannot
    leave partial edits, discard the preference or create a saved bypass.
    """
    @wraps(function)
    def call(upper, controls):
        if 'stable_pitch_preference' not in upper or _CONTROL_UPDATE_ACTIVE.get():
            return function(upper, controls)
        from connected_tier2 import realize
        from stable_pitch_policy import enforce_transition
        before = realize(upper)
        token = _CONTROL_UPDATE_ACTIVE.set(True)
        try:
            edited, decision = function(deepcopy(upper), controls)
        finally:
            _CONTROL_UPDATE_ACTIVE.reset(token)
        if edited.get('stable_pitch_preference') != upper['stable_pitch_preference']:
            raise ValueError('UPDATE_CHANGED_STABLE_PITCH_PREFERENCE')
        report = enforce_transition(upper, before, realize(edited))
        decision = dict(decision, stable_pitch_check=report)
        return edited, decision
    return call
