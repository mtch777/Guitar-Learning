"""One source-observed coattack family, two explicitly requested treatments.

The SAME relation owns the target coattack anchors in analysis and inversion:
    target = reference + shared_residual + follow * (target_backing-source_backing)
Member voicing intervals and unpitched/dead occurrences retain their existing
owners. This bounded version accepts only the plain shared pitch representation.
It is intentional control, not a predictor of a composer's preferred treatment.
"""
from copy import deepcopy
from fractions import Fraction as F
import math
import random

import backing_pitch_ownership as backing
import backing_written_tie_constraints as ties
import backing_execution_constraints as execution
import figure_register_ownership as figure
import group_rhythm_relations as rhythm
import musical_tier2 as music
from source_observation_evidence import digest, origin, validate_origin as check_origin

SCHEMA = 'coattack-treatment-ownership/1'
POLICY = 'source_coattack_treatment'
OBSERVATIONS = 'original-coattack-reference-observations/1'
INTENTS = ('repeat_reference_pitch', 'follow_reference_interval_class')
BINDING_FIELDS = {'reference_anchor_ref', 'target_anchor_ref', 'source_backing_ref', 'target_backing_ref'}
FIELDS = {'schema', 'core', 'bindings', 'parameters', 'observations',
          'execution_constraints', 'written_tie_constraints', 'target_notation_sha256'}
OBS_FIELDS = {'schema', 'source_origin', 'bindings_sha256', 'reference_factor',
              'reference_context_sha256', 'coattack_count', 'backing_occurrence_count',
              'counting_unit', 'qualification', 'evidence_sha256'}


def coordinate(value):
    if type(value) is not str:
        raise ValueError('Canonical integral semitone coordinate required')
    try:
        number = F(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError('Invalid semitone coordinate') from error
    if str(number) != value or number.denominator != 1:
        raise ValueError('Canonical integral semitone coordinate required')
    return number


def relation(*, reference, source_backing, target_backing, follow, residual=None, target=None):
    """Solve target or the shared residual through the same existing p=a+d."""
    if type(follow) is not int or follow not in (0, 1) or (residual is None) == (target is None):
        raise ValueError('Explicit binary follow and exactly one relation side required')
    p, a, b = map(coordinate, (reference, source_backing, target_backing))
    base = music.relation(anchor=str(p), interval=str(follow * (b-a)))['pitch']
    solved = music.relation(anchor=base, interval=str(coordinate(residual))) if target is None else music.relation(anchor=base, pitch=str(coordinate(target)))
    return dict(reference=str(p), source_backing=str(a), target_backing=str(b),
                follow=follow, residual=solved['interval'], target=solved['pitch'])


def _bindings(rows):
    if type(rows) is not list or len(rows) < 2 or any(type(r) is not dict or set(r) != BINDING_FIELDS for r in rows):
        raise ValueError('At least two complete explicit coattack bindings required')
    for row in rows:
        for ref in row.values():
            backing.address(ref)
    for key in ('reference_anchor_ref', 'target_anchor_ref'):
        refs = [r[key] for r in rows]
        if len(set(refs)) != len(refs) or refs != sorted(refs, key=backing.address):
            raise ValueError('Unique structurally ordered reference and target anchors required')
    return rows


def _pairs(core, rows):
    index = backing._index(core); pairs = []; source_groups = set(); target_groups = set()
    for row in rows:
        if any(ref not in index for ref in row.values()):
            raise ValueError('Dangling coattack binding')
        source, sm = index[row['reference_anchor_ref']]; target, tm = index[row['target_anchor_ref']]
        sg, sn = index[row['source_backing_ref']]; tg, tn = index[row['target_backing_ref']]
        if source['id'] in source_groups or target['id'] in target_groups:
            raise ValueError('Duplicate coattack authority')
        source_groups.add(source['id']); target_groups.add(target['id'])
        if len({backing.address(ref)[0] for ref in row.values()}) != 1 or source['part_id'] != target['part_id'] or sg['part_id'] != tg['part_id'] or source['part_id'] == sg['part_id']:
            raise ValueError('Independent backing part and one focal part in the same song required')
        for group, anchor in ((source, sm), (target, tm)):
            lows = [m['id'] for m in group['members'] if m['voicing_interval'] == '0']
            if lows != [anchor['id']] or group['timing_uncertain'] is not False:
                raise ValueError('Unique existing lowest-pitch anchor and known clock required')
            if len({(m['bar'], m['voice'], m['beat']) for m in group['members']}) != 1:
                raise ValueError('One complete source beat per coattack required')
        shape = lambda g: [(m['duration_q'], m['voicing_interval']) for m in g['members']]
        if shape(source) != shape(target) or sm['voice'] != tm['voice']:
            raise ValueError('Complete known/dead voicing and duration shape must agree')
        if any('bass_register_anchor' not in g for g in (source, sg, tg)):
            raise ValueError('Dependency cycle or unsupported dependent reference')
        pairs.append((source, target, sg, sn, tg, tn))
    if source_groups & target_groups:
        raise ValueError('Reference and target coattacks must be disjoint')
    if len({(s['part_id'], s['members'][0]['voice']) for s, *_ in pairs}) != 1:
        raise ValueError('One explicit focal written lane required')
    if len({p[2]['part_id'] for p in pairs}) != 1:
        raise ValueError('One explicit backing part across the complete treatment required')
    for side in (0, 1):
        starts = [F(p[side]['onset_q']) for p in pairs]
        if starts != sorted(set(starts)):
            raise ValueError('Strictly chronological coattacks required')
    source_times = [F(p[0]['onset_q']) - F(pairs[0][0]['onset_q']) for p in pairs]
    target_times = [F(p[1]['onset_q']) - F(pairs[0][1]['onset_q']) for p in pairs]
    if source_times != target_times:
        raise ValueError('Written relative attack pattern differs')
    spans = [(min(F(p[i]['onset_q']) for p in pairs), max(F(p[i]['onset_q'])+max(F(m['duration_q']) for m in p[i]['members']) for p in pairs)) for i in (0, 1)]
    if max(spans[0][0], spans[1][0]) < min(spans[0][1], spans[1][1]):
        raise ValueError('Reference and target written spans overlap')
    return index, pairs


def _contexts(core, pairs):
    """Complete held written context, not a nearest-attack or chosen subset."""
    contexts = []
    for source, target, sg, sn, tg, tn in pairs:
        row = []
        for focal, backing_group, backing_note in ((source, sg, sn), (target, tg, tn)):
            start = F(focal['onset_q']); end = start + max(F(m['duration_q']) for m in focal['members'])
            if end <= start:
                raise ValueError('Positive complete coattack durations required')
            candidates = []
            for g in core['coattacks']:
                if g['part_id'] != backing_group['part_id']:
                    continue
                if g['timing_uncertain'] is not False:
                    raise ValueError('Uncertain backing written clock')
                for m in g['members']:
                    a = F(g['onset_q']); b = a + F(m['duration_q'])
                    if a == b and start <= a < end:
                        raise ValueError('Unresolved backing grace activity')
                    if max(a, start) < min(b, end):
                        pitch = music.member_pitch(g, m)
                        if pitch is None:
                            raise ValueError('Unknown written backing pitch')
                        coordinate(pitch); candidates.append((g, m, a, b, pitch))
            edges = sorted({start, end} | {max(start, a) for _, _, a, _, _ in candidates} | {min(end, b) for _, _, _, b, _ in candidates})
            cells = []
            for a, b in zip(edges, edges[1:]):
                active = [(g, m, pitch) for g, m, x, y, pitch in candidates if x <= a and y >= b]
                if not active:
                    raise ValueError('Missing full-hold backing coverage')
                low = min(F(p) for _, _, p in active)
                lowest = [m['id'] for _, m, p in active if F(p) == low]
                if lowest != [backing_note['id']]:
                    raise ValueError('Specified backing is not the unique held lowest written pitch')
                cells.append(dict(start=str(a), end=str(b), members=[m['id'] for _, m, _ in active]))
            row.append(cells)
        contexts.append(row)
    return contexts


def _scope(pairs, contexts):
    refs = {m['id'] for p in pairs for i in (0, 1) for m in p[i]['members']}
    refs |= {ref for row in contexts for side in row for cell in side for ref in cell['members']}
    return sorted(refs, key=backing.address)


def _observation_shape(observations, bindings):
    if type(observations) is not dict or set(observations) != OBS_FIELDS or observations['schema'] != OBSERVATIONS:
        raise ValueError('Typed original reference observations required')
    check_origin(observations['source_origin'])
    if observations['bindings_sha256'] != digest(bindings) or observations['evidence_sha256'] != digest({k:v for k,v in observations.items() if k != 'evidence_sha256'}):
        raise ValueError('Original reference evidence integrity mismatch')
    if (type(observations['coattack_count']) is not int or observations['coattack_count'] != len(bindings)
            or type(observations['backing_occurrence_count']) is not int or observations['backing_occurrence_count'] != len({r['source_backing_ref'] for r in bindings})
            or observations['counting_unit'] != 'original_written_coattacks_not_independent_examples'
            or observations['qualification'] != 'plain_known_pitch_or_explicit_dead_with_full_held_scaffold_v1'):
        raise ValueError('Original observation scope/count changed')
    factor = observations['reference_factor']
    if type(factor) is not dict or set(factor) != {'interval_class','offsets_semitones','octave'}:
        raise ValueError('Minimal reference relation factor required')
    solved = figure.relation(**factor)
    if len(solved['intervals']) != len(bindings):
        raise ValueError('Reference factor cardinality differs')
    _constant_octave(solved['intervals'])


def _plan(wrapper):
    if type(wrapper) is not dict or set(wrapper) != FIELDS or wrapper['schema'] != SCHEMA:
        raise ValueError('Unknown coattack treatment owner')
    core = wrapper['core']
    if type(core) is not dict or core.get('schema') != backing.PLAIN or set(core) != backing.BASE_FIELDS or any('interpretation' in g for g in core['coattacks']):
        raise ValueError('Plain core without cached views required; existing wrappers are unsupported')
    rows = _bindings(wrapper['bindings']); index, pairs = _pairs(core, rows)
    params = wrapper['parameters']
    if type(params) is not dict or set(params) != {'residual','follow'} or type(params['follow']) is not int or params['follow'] not in (0,1):
        raise ValueError('One shared residual and binary follow authority required')
    coordinate(params['residual'])
    targets = {p[1]['id'] for p in pairs}
    if any(('bass_register_anchor' in g) == (g['id'] in targets) for g in core['coattacks']):
        raise ValueError('Missing or duplicate absolute coattack authority')
    _observation_shape(wrapper['observations'], rows)
    contexts = _contexts(core, pairs); refs = _scope(pairs, contexts)
    ties.shape(wrapper['written_tie_constraints'], refs); execution.shape(wrapper['execution_constraints'], refs)
    return index, pairs, contexts, refs


def _targets(pairs, parameters):
    return [relation(reference=s['bass_register_anchor'], source_backing=music.member_pitch(sg,sn),
                     target_backing=music.member_pitch(tg,tn), **parameters)['target'] for s,_,sg,sn,tg,tn in pairs]


def expand(wrapper):
    """Restore only transient coattack anchors through the stored equation."""
    _, pairs, _, _ = _plan(wrapper); pitches = _targets(pairs, wrapper['parameters'])
    result = deepcopy(wrapper['core']); index = backing._index(result)
    for row, pitch in zip(wrapper['bindings'], pitches):
        index[row['target_anchor_ref']][0]['bass_register_anchor'] = pitch
    rhythm.refresh(result); music.validate(result)
    return result


def validate(wrapper):
    return expand(wrapper)


def _raw(documents, ref):
    _, part, bar, voice, beat, note = backing.address(ref)
    doc = documents[f'track-{part}.json']; raw = doc['measures'][bar-1]['voices'][voice]['beats'][beat]
    return doc, raw, raw['notes'][note]


def _notation_digest(pairs, documents):
    beats = {}
    for _, target, *_ in pairs:
        for member in target['members']:
            _, raw, _ = _raw(documents, member['id']); key = member['id'].rsplit(':',1)[0]
            if key not in beats:
                beats[key] = deepcopy(raw)
            if member['voicing_interval'] is not None:
                beats[key]['notes'][member['note']]['fret'] = '<derived-pitch-contact>'
    return digest(beats)


def _reference_digest(pairs, contexts, documents):
    groups = {}; beats = {}; geometry = {}
    for (source, _, *_), row in zip(pairs, contexts):
        groups[source['id']] = {k:v for k,v in source.items() if k != 'interpretation'}
        refs = {m['id'] for m in source['members']} | {ref for cell in row[0] for ref in cell['members']}
        for ref in refs:
            doc, beat, _ = _raw(documents, ref)
            beats[ref.rsplit(':',1)[0]] = beat
            geometry[str(doc['partId'])] = {k:doc[k] for k in ('instrumentId','tuning','capo','frets') if k in doc}
    return digest(dict(source_groups=groups, raw_reference_and_backing_beats=beats, physical_geometry=geometry))


def _constant_octave(intervals):
    values = {int(coordinate(d)//12) for d in intervals}
    if len(values) != 1:
        raise ValueError('Shared relative octave is ambiguous across this family')
    return values.pop()


def _factors(pairs, target_pitches):
    source = [music.relation(anchor=music.member_pitch(sg,sn),pitch=s['bass_register_anchor'])['interval'] for s,_,sg,sn,_,_ in pairs]
    current = [music.relation(anchor=music.member_pitch(tg,tn),pitch=p)['interval'] for (_,_,_,_,tg,tn),p in zip(pairs,target_pitches)]
    _constant_octave(source); _constant_octave(current)
    return figure.relation(intervals=source), figure.relation(intervals=current)


def lift(shared, tier1, bindings, *, source_origin=None):
    """Fresh original-source preparation; no existing owner is flattened."""
    if type(shared) is not dict or shared.get('schema') != backing.PLAIN:
        raise ValueError('Unsupported existing ownership wrapper; original plain forward input required')
    music.validate(shared); rows = deepcopy(_bindings(bindings)); _, pairs = _pairs(shared, rows)
    contexts = _contexts(shared, pairs); refs = _scope(pairs, contexts)
    original = origin(tier1)
    if source_origin is not None and source_origin != original:
        raise ValueError('Initial original-source origin mismatch')
    residuals = {relation(reference=s['bass_register_anchor'], source_backing=music.member_pitch(sg,sn),target_backing=music.member_pitch(tg,tn),follow=0,target=t['bass_register_anchor'])['residual'] for s,t,sg,sn,tg,tn in pairs}
    if len(residuals) != 1:
        raise ValueError('No single shared original residual; separate note payload is forbidden')
    sf, _ = _factors(pairs,[p[1]['bass_register_anchor'] for p in pairs])
    from source_fact_tier1 import project_documents
    documents = project_documents(tier1)
    observations = dict(schema=OBSERVATIONS,source_origin=original,bindings_sha256=digest(rows),
        reference_factor={k:sf[k] for k in ('interval_class','offsets_semitones','octave')},
        reference_context_sha256=_reference_digest(pairs,contexts,documents),coattack_count=len(rows),
        backing_occurrence_count=len({r['source_backing_ref'] for r in rows}),
        counting_unit='original_written_coattacks_not_independent_examples',
        qualification='plain_known_pitch_or_explicit_dead_with_full_held_scaffold_v1')
    observations['evidence_sha256'] = digest(observations)
    core = deepcopy(shared); index = backing._index(core)
    for row in rows:
        del index[row['target_anchor_ref']][0]['bass_register_anchor']
    for view in rhythm.VIEWS:
        core.pop(view,None)
    for group in core['coattacks']:
        group.pop('interpretation',None)
    result = dict(schema=SCHEMA,core=core,bindings=rows,parameters=dict(residual=residuals.pop(),follow=0),observations=observations,
                  written_tie_constraints=ties.from_tier1(shared,tier1,refs),execution_constraints=execution.build(tier1,refs),
                  target_notation_sha256=_notation_digest(pairs,documents))
    validate_execution(result,tier1)
    return result


def validate_origin(wrapper, upper_origin):
    _observation_shape(wrapper['observations'], wrapper['bindings']); check_origin(upper_origin)
    if wrapper['observations']['source_origin'] != upper_origin:
        raise ValueError('Saved original observation origin differs from package origin')


def validate_execution(wrapper, tier1):
    """Current inverse checks; historical reference equality is NOT required."""
    normal = expand(wrapper); index = backing._index(normal)
    _, pairs, contexts, refs = _plan(wrapper)
    from source_fact_tier1 import project_documents
    from backing_motion_intervention import original_contact, PLAIN_BEAT
    from technique_analysis import classify_group
    documents = project_documents(tier1)
    for ref in refs:
        g,m = index[ref]; doc, beat, note = _raw(documents,ref)
        if set(beat)-PLAIN_BEAT or set(note)-{'string','fret','dead'} or ('dead' in note and type(note['dead']) is not bool):
            raise ValueError('Unsupported current coattack/backing execution notation')
        pitch = music.member_pitch(g,m)
        if pitch is None:
            if note.get('dead') is not True:
                raise ValueError('Unknown pitch must remain an explicit dead occurrence')
            # A dead contact remains a literal contact, never a guessed pitch.
            tuning=doc.get('tuning'); string=note.get('string'); fret=note.get('fret'); limit=doc.get('frets')
            if (type(tuning) is not list or type(string) is not int or not 0<=string<len(tuning)
                    or type(fret) is not int or fret<0 or type(tuning[string]) is not int
                    or limit is not None and (type(limit) is not int or limit<0 or fret>limit)):
                raise ValueError('Valid unchanged dead-note contact required')
        else:
            if note.get('dead') is True:
                raise ValueError('Known written pitch contradicts dead declaration')
            original_contact(doc,note,pitch)
    for row in contexts:
        for side in row:
            for cell in side:
                notes = []
                for ref in cell['members']:
                    g,m = index[ref]; _,_,raw = _raw(documents,ref)
                    notes.append(dict(midi=int(coordinate(music.member_pitch(g,m))),string=raw['string']))
                if not set(classify_group(notes)) & {'power_chord','extended_power_chord'}:
                    raise ValueError('Unsupported complete held backing scaffold')
    if _notation_digest(pairs,documents) != wrapper['target_notation_sha256']:
        raise ValueError('Fixed target string/dead/timing/expression contract changed')
    ties.validate_tier1(wrapper['written_tie_constraints'],normal,tier1,refs)
    execution.validate(wrapper['execution_constraints'],tier1,refs)


def validate_choice_evidence(upper, *, current=None):
    from connected_tier2 import realize
    wrapper = upper['musical_relationships']; validate_origin(wrapper,upper.get('source_origin'))
    if current is None:
        current = realize(upper)
    _, pairs, contexts, _ = _plan(wrapper)
    from source_fact_tier1 import project_documents
    if _reference_digest(pairs,contexts,project_documents(current)) != wrapper['observations']['reference_context_sha256']:
        raise ValueError('ORIGINAL_REFERENCE_EVIDENCE_CHANGED: inverse propagation is valid, new nonzero choices are unsupported')
    sf,_ = _factors(pairs,_targets(pairs,wrapper['parameters']))
    if {k:sf[k] for k in ('interval_class','offsets_semitones','octave')} != wrapper['observations']['reference_factor']:
        raise ValueError('Original source interval observations differ')


def validate_controls(controls):
    fields = {'context_policy','melody','intent','allow_note_octave_changes','seed'}
    if type(controls) is not dict or set(controls) != fields or controls['context_policy'] != POLICY or controls['intent'] not in INTENTS:
        raise ValueError('Explicit supported coattack intention required')
    if type(controls['melody']) not in (int,float) or not math.isfinite(controls['melody']) or not 0 <= controls['melody'] <= 100:
        raise ValueError('Finite melody release0..100 required')
    if type(controls['seed']) is not int or type(controls['allow_note_octave_changes']) is not bool:
        raise ValueError('Typed seed and Boolean note-octave permission required')


def release(controls):
    """One repeatable group-level release; percentages do not blend pitches."""
    validate_controls(controls)
    return random.Random(f"coattack-treatment:{controls['seed']}").random() < controls['melody']/100


def assert_preserved(before, after):
    expand(before); expand(after)
    a = deepcopy(before); b = deepcopy(after)
    a.pop('parameters'); b.pop('parameters')
    if digest(a) != digest(b):
        raise ValueError('COATTACK_AUTHORITY_LOSS: only shared treatment parameters may change')


from source_observation_evidence import controlled_update as _controlled_update
@_controlled_update
def intervene(upper, controls):
    from connected_tier2 import realize
    validate_controls(controls); before = realize(upper)
    wrapper = upper['musical_relationships']; validate_origin(wrapper,upper.get('source_origin'))
    decision = dict(context_policy=POLICY,intent=controls['intent'],released=False,changed=False,pitch_changes=[])
    if controls['melody'] == 0:
        return deepcopy(upper),decision
    validate_choice_evidence(upper,current=before)
    decision['released'] = release(controls)
    if not decision['released']:
        return deepcopy(upper),decision
    _, pairs, _, _ = _plan(wrapper)
    current_pitches = _targets(pairs,wrapper['parameters'])
    if controls['intent'] == 'repeat_reference_pitch':
        parameters = dict(residual='0',follow=0)
    else:
        sf,tf = _factors(pairs,current_pitches)
        parameters = dict(residual=str(12*(tf['octave']-sf['octave'])),follow=1)
    result = deepcopy(upper); changed = result['musical_relationships']; changed['parameters'] = parameters
    proposed = _targets(pairs,parameters)
    for (_,target,*_),old,new in zip(pairs,current_pitches,proposed):
        for member in target['members']:
            if member['voicing_interval'] is None:
                continue
            a = coordinate(old)+coordinate(member['voicing_interval']); b = coordinate(new)+coordinate(member['voicing_interval'])
            if a != b:
                if a//12 != b//12 and not controls['allow_note_octave_changes']:
                    raise ValueError('NOTE_OCTAVE_PERMISSION_REQUIRED')
                decision['pitch_changes'].append(dict(ref=member['id'],before=str(a),after=str(b),before_octave=int(a//12)-1,after_octave=int(b//12)-1))
    assert_preserved(wrapper,changed)
    from source_observation_evidence import assert_only_parameter_changes
    assert_only_parameter_changes(upper, result, [
        ('musical_relationships', 'parameters', 'residual'),
        ('musical_relationships', 'parameters', 'follow'),
    ])
    realize(result)  # The same full inverse validates all current consequences.
    decision.update(changed=bool(decision['pitch_changes']),parameters=deepcopy(parameters),
                    original_evidence_sha256=wrapper['observations']['evidence_sha256'])
    return result,decision
