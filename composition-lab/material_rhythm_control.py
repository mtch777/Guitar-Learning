"""One coordinated rhythmic displacement per use, through its existing clock.

The intention is earlier/later against the current backing, not a claim to have
learned which groove is best. Candidate magnitudes come from actual accompanying
attack spacings. Complete source material and observations remain immutable.
"""
from copy import deepcopy
from fractions import Fraction as F
import random

import support_material_uses as uses
from source_observation_evidence import digest


def _use(upper, use_id):
    found = [u for u in upper['uses'] if u['id'] == use_id]
    if len(found) != 1:
        raise ValueError('One stable material-use identity required')
    return found[0]


def expand_uses(upper):
    """Read through existing owners; no new choice or inverse lives here."""
    import section_arrangements as sections
    import support_arrangement as arrangement
    import thematic_return as theme
    if upper.get('tier') == 5:
        return sections.expand(theme.expand(upper))
    if upper.get('tier') == 4:
        return (sections.expand(upper) if upper.get('schema') == sections.SCHEMA
                else arrangement.expand(upper))
    uses._shape(upper)
    return upper


def embed_uses(upper, changed, use_id):
    """Keep section/return responsibilities, changing only the supplied T3.

    Rhythm is explicitly independent of T5's material-reference recall. The
    caller cannot accidentally make a repeated rhythm change an artist rule.
    """
    import section_arrangements as sections
    import support_arrangement as arrangement
    import thematic_return as theme
    previous = deepcopy(expand_uses(upper)); protected = deepcopy(changed)
    _use(previous, use_id).pop('rhythm_offset_q', None)
    _use(protected, use_id).pop('rhythm_offset_q', None)
    if protected['schema'] not in (previous['schema'], uses.RHYTHM_SCHEMA):
        raise ValueError('Unrelated material schema changed')
    protected['schema'] = previous['schema']
    if previous != protected:
        raise ValueError('Rhythmic update changed an unrelated relationship or observation')
    if upper['tier'] == 3:
        return changed
    if upper['tier'] == 5:
        return theme.pack_uses(upper, changed)
    out = deepcopy(upper)
    section = out['lower_tier'] if out['tier'] == 5 else out
    child = deepcopy(changed)
    owners = section['choices'] if section['schema'] == sections.SCHEMA else [section]
    for owner in owners:
        use = _use(child, owner['allocation']['use_id'])
        use.pop('material_ref'); use.pop('expression')
    section['lower_tier'] = child
    inverse = theme if out['tier'] == 5 else sections if section['schema'] == sections.SCHEMA else arrangement
    inverse.reconstruct(out, {'variation': 0})
    if expand_uses(out) != changed:
        raise ValueError('Rhythmic update altered a section or return obligation')
    return out


def lift_composed(upper, use_id):
    return embed_uses(upper, lift(expand_uses(upper), use_id), use_id)


def candidate_composed(upper, use_id, offset_q):
    return embed_uses(upper, candidate(expand_uses(upper), use_id, offset_q), use_id)


def lift(upper, use_id):
    """Make timing independent of allocation; do not replace old owners."""
    before = uses.expand(upper)
    selected = _use(upper, use_id)
    if 'rhythm_offset_q' in selected:
        raise ValueError('Existing timing ownership cannot be reset by a constructor')
    out = deepcopy(upper)
    if out['schema'] != uses.DIRECT_SCHEMA:
        out['schema'] = uses.RHYTHM_SCHEMA
    _use(out, use_id)['rhythm_offset_q'] = '0'
    if uses.expand(out) != before:
        raise ValueError('Zero timing ownership changed the preceding model')
    return out


def candidate(upper, use_id, offset_q):
    """An explicit displacement, checked without changing any other choice."""
    uses._shape(upper)
    if type(offset_q) is not str or str(F(offset_q)) != offset_q:
        raise ValueError('Canonical rational displacement required')
    if 'rhythm_offset_q' not in _use(upper, use_id):
        raise ValueError('Use has no rhythmic displacement owner')
    out = deepcopy(upper)
    _use(out, use_id)['rhythm_offset_q'] = offset_q
    uses.reconstruct(out, {'variation': 0})
    return out


def candidate_many(upper, requests):
    """Apply already resolved offsets atomically, without choosing new offsets.

    Each stable use identity is bound to its declared scope. This is a batch of
    the existing timing-owner equation, not a sampler or an assumption that
    arbitrary context-dependent choices commute. Absent timing owners are
    initialized together and checked against the complete preceding model.
    """
    uses._shape(upper)
    if type(requests) is not list or not requests:
        raise ValueError('Explicit nonempty rhythmic requests required')
    seen = set()
    for request in requests:
        if type(request) is not dict or set(request) != {'use_id', 'scope', 'offset_q'}:
            raise ValueError('Exact rhythmic use/scope/offset request required')
        identity = request['use_id']
        if type(identity) is not str or identity in seen:
            raise ValueError('Unique stable rhythmic use identities required')
        seen.add(identity)
        selected = _use(upper, identity)
        scope = request['scope']
        if type(scope) is not dict or set(scope) != {'parts', 'first_bar', 'last_bar'}:
            raise ValueError('Exact rhythmic destination scope required')
        uses.material._scope(scope['parts'], scope['first_bar'], scope['last_bar'])
        if scope != upper['slots'][selected['slot_ref']]['scope']:
            raise ValueError('Rhythmic request scope differs from its saved use')
        value = request['offset_q']
        if type(value) is not str or str(F(value)) != value:
            raise ValueError('Canonical rational displacement required')
    before = uses.expand(upper)
    initialized = deepcopy(upper)
    missing = [r['use_id'] for r in requests
               if 'rhythm_offset_q' not in _use(initialized, r['use_id'])]
    if missing:
        if initialized['schema'] != uses.DIRECT_SCHEMA:
            initialized['schema'] = uses.RHYTHM_SCHEMA
        for identity in missing:
            _use(initialized, identity)['rhythm_offset_q'] = '0'
        if uses.expand(initialized) != before:
            raise ValueError('Zero timing ownership changed the preceding model')
    out = deepcopy(initialized)
    for request in requests:
        _use(out, request['use_id'])['rhythm_offset_q'] = request['offset_q']
    uses.reconstruct(out, {'variation': 0})
    return out


def options(upper, use_id):
    """Freeze all observed backing spacings before testing any candidate.

    These are current-context observations, never extra original-source votes.
    Structural feasibility is separate from the complete candidate inverse.
    """
    from source_fact_tier1 import project_documents
    from source_key_tier1 import extract_documents
    lower = uses.reconstruct(upper, {'variation': 0})
    documents = project_documents(lower)
    events = extract_documents(documents)['events']
    return _options_from_context(upper, use_id, documents, events)


def _options_from_context(upper, use_id, documents, events):
    """Same options equation with a caller-frozen, reconstructed current context.

    Internal batch callers compute this context once before any proposals. It is
    not cached source evidence and is never used instead of the final inverse.
    """
    from material_rhythm_displacement import solve
    from material_approaches import SCHEMA, expand
    selected = _use(upper, use_id)
    scope = upper['slots'][selected['slot_ref']]['scope']
    times = {}
    for event in events:
        measure = documents[f'track-{event["part_id"]}.json']['measures'][event['bar']-1]
        voice = measure['voices'][event['voice']]
        beat = voice['beats'][event['beat']]
        note = beat['notes'][event['note']]
        if (event['part_id'] not in scope['parts']
                and scope['first_bar'] <= event['bar'] <= scope['last_bar']
                and not measure.get('rest') and not voice.get('rest')
                and not beat.get('graceNote') and not beat.get('rest')
                and not note.get('rest') and not note.get('tie')
                and F(event['duration_q']) > 0):
            times.setdefault(event['bar'], {}).setdefault(event['onset_q'], []).append(event['id'])
    witnesses = []
    for bar, by_time in sorted(times.items()):
        ordered = sorted(by_time, key=F)
        for a, b in zip(ordered, ordered[1:]):
            witnesses.append(dict(bar=bar, from_q=a, to_q=b,
                                  from_refs=by_time[a], to_refs=by_time[b], spacing_q=str(F(b)-F(a))))
    magnitudes = {F(w['spacing_q']) for w in witnesses}
    values = sorted({F(0)} | magnitudes | {-v for v in magnitudes})
    definition = upper['materials'][selected['material_ref']]
    if definition['schema'] == SCHEMA:
        definition = expand(definition, selected['approach_mode'])
    definition = uses.material.rhythm_context(definition, upper['lower_tier'])
    attempts = []
    for value in values:
        try:
            _, report = solve(definition, str(value))
            attempts.append(dict(offset_q=str(value), status='CLOCK_AND_NOTATION_FIT', effect=report))
        except ValueError as error:
            attempts.append(dict(offset_q=str(value), status='REFUSED', reason=str(error)))
    return dict(input_sha256=digest(upper), use_id=use_id,
                basis='current_backing_attack_spacings_not_original_observations',
                witnesses=witnesses, attempts=attempts,
                limitation='Clock/notation feasibility only; complete inverse checks current execution and owners.')


def prepare(upper, use_id, intention):
    """First feasible observed displacement in the requested direction.

    Nearest first is a disclosed controlled-comparison policy, not learned taste.
    Every larger or opposite candidate remains in the report; no source reroll.
    """
    if intention not in ('earlier', 'later'):
        raise ValueError('Explicit earlier/later rhythmic intention required')
    evidence = options(upper, use_id)
    current = F(_use(upper, use_id)['rhythm_offset_q'])
    sign = -1 if intention == 'earlier' else 1
    rows = [a for a in evidence['attempts']
            if a['status'] == 'CLOCK_AND_NOTATION_FIT' and (F(a['offset_q'])-current)*sign > 0]
    rows.sort(key=lambda a: abs(F(a['offset_q'])-current))
    validation = []
    for row in rows:
        try:
            out = candidate(upper, use_id, row['offset_q'])
        except ValueError as error:
            validation.append(dict(offset_q=row['offset_q'], status='REFUSED', reason=str(error)))
            continue
        validation.append(dict(offset_q=row['offset_q'], status='FULL_INVERSE_PASS'))
        return out, dict(status='PREPARED', chosen_offset_q=row['offset_q'], intention=intention,
                         evidence=evidence, validation=validation, learned_preference=False)
    return deepcopy(upper), dict(status='NO_FEASIBLE_GROUP_DISPLACEMENT', intention=intention,
                                 evidence=evidence, validation=validation, learned_preference=False)


def intervene(upper, use_id, controls):
    if (type(controls) is not dict or set(controls) != {'release', 'intention', 'seed'}
            or type(controls['release']) is not int or not 0 <= controls['release'] <= 100
            or controls['intention'] not in ('earlier', 'later') or type(controls['seed']) is not int):
        raise ValueError('Explicit rhythmic release, intention and seed required')
    uses._shape(upper)
    current = _use(upper, use_id).get('rhythm_offset_q')
    if current is None:
        raise ValueError('Use has no rhythmic displacement owner')
    if controls['release'] == 0:
        uses.reconstruct(upper, {'variation': 0})
        return deepcopy(upper), dict(release_attempted=False, released=False, changed=False,
                                     release_percent=0, seed=controls['seed'], status='CURRENT_ZERO_LOCK')
    proposed, evidence = prepare(upper, use_id, controls['intention'])
    if evidence['status'] != 'PREPARED':
        return deepcopy(upper), dict(release_attempted=False, released=False, changed=False,
                                     release_percent=controls['release'], seed=controls['seed'],
                                     status=evidence['status'], evidence=evidence)
    released = random.Random(f'material-rhythm:release:{controls["seed"]}').random() < controls['release']/100
    choose = random.Random(f'material-rhythm:selection:{controls["seed"]}').choice((False, True)) if released else False
    out = proposed if choose else deepcopy(upper)
    return out, dict(release_attempted=True, released=released, changed=out != upper, release_percent=controls['release'],
                     seed=controls['seed'], chosen_offset_q=_use(out, use_id)['rhythm_offset_q'], evidence=evidence)
