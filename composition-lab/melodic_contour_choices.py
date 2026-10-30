"""Observed middle-note alternatives with fixed neighboring notes and contour.

The existing musical pitch owner remains authoritative. Three adjacent attacks
are a local comparison neighborhood, not an inferred phrase or melodic role.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import json
import math

POLICY = 'source_local_melodic_contour'
NOTE_EXPRESSION = ('hp', 'ghost', 'dead', 'tie', 'slide', 'bend', 'harmonic',
    'harmonicFret', 'staccato', 'tremolo', 'vibrato', 'wideVibrato',
    'leftHandVibrato', 'pickScrape', 'trill')
BEAT_EXPRESSION = ('palmMute', 'tapping', 'letRing', 'brushStroke', 'arpeggio',
    'downStroke', 'downArpeggio', 'upStroke', 'pickStroke', 'fadeIn',
    'tremoloBar', 'vibrato', 'wideVibrato', 'leftHandVibrato',
    'vibratoWithTremoloBar', 'tremolo', 'harmonic', 'gradualVelocity', 'wahwah',
    'golpe', 'sustainPedal', 'slapping')
SAFE_BEAT = {'notes', 'type', 'duration', 'beamStart', 'beamStop', 'beam',
    'beamMode', 'velocity', 'chord', 'rest', 'dots', 'dotted', 'tuplet',
    'tupletStart', 'tupletStop', 'graceNote', *BEAT_EXPRESSION}
SAFE_NOTE = {'string', 'fret', 'rest', 'velocity', 'accentuated', *NOTE_EXPRESSION}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def direction(a, b):
    return (F(b) > F(a)) - (F(b) < F(a))


def contour(pitches):
    if len(pitches) != 3:
        raise ValueError('Exactly three adjacent pitches required')
    return [direction(pitches[0], pitches[1]), direction(pitches[1], pitches[2])]


def inventory(tier1):
    """Every source triple, including refusals; no chosen key or note generator."""
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    from local_accents import inventory as accents
    from execution_dependencies import build as dependencies
    docs = project_documents(tier1)
    lower = extract_documents(docs)
    events = {e['id']: e for e in lower['events']}
    states = {r['occurrence_ref']: r for r in accents(tier1)['occurrences']}
    pinned = set(dependencies(tier1)['pinned_members'])
    streams = defaultdict(list)
    bypart = defaultdict(list)
    for e in events.values():
        bypart[e['part_id']].append(e)
    for name, part in sorted(docs.items()):
        if not name.startswith('track-'):
            continue
        for bar, measure in enumerate(part.get('measures', []), 1):
            for voice, v in enumerate(measure.get('voices', [])):
                for bi, b in enumerate(v.get('beats', [])):
                    beat_ref = f'{name}#/measures/{bar-1}/voices/{voice}/beats/{bi}'
                    streams[part['partId'], voice].append(dict(part=part,
                        bar=bar, voice=voice, beat=bi, beat_ref=beat_ref, raw=b,
                        rest_container=bool(measure.get('rest') or v.get('rest'))))
    rows = []
    for (pid, voice), lane in sorted(streams.items()):
        for i in range(1, len(lane)-1):
            nodes = lane[i-1:i+2]
            closure = lane[max(0, i-2):min(len(lane), i+3)]
            refs, pitches, physical, markings, times, reasons = [], [], [], [], [], []
            part = nodes[0]['part']
            if type(part.get('instrumentId')) is not int or not 24 <= part['instrumentId'] <= 39:
                reasons.append('OUTSIDE_GUITAR_BASS_SCOPE')
            for node in nodes:
                b = node['raw']
                if node['rest_container'] or b.get('rest'):
                    reasons.append('SOURCE_REST_CONTAINER')
                if set(b)-SAFE_BEAT:
                    reasons.append('UNKNOWN_BEAT_DECLARATION')
                if any(k in b and b[k] is not None and b[k] is not False for k in BEAT_EXPRESSION):
                    reasons.append('BEAT_EXECUTION_DECLARATION')
                if len(b.get('notes', [])) != 1:
                    reasons.append('NOT_ONE_RAW_NOTE_PER_BEAT')
                    continue
                n = b['notes'][0]
                ref = f"event:{part['songId']}:{pid}:{node['bar']}:{voice}:{node['beat']}:0"
                refs.append(ref)
                if set(n)-SAFE_NOTE:
                    reasons.append('UNKNOWN_NOTE_DECLARATION')
                if any(k in n and n[k] is not None and n[k] is not False for k in NOTE_EXPRESSION):
                    reasons.append('NOTE_EXECUTION_DECLARATION')
                if n.get('rest'):
                    reasons.append('SOURCE_REST_NOTE')
                if ref in pinned:
                    reasons.append('LINKED_EXECUTION')
                s = states.get(ref)
                if s is None:
                    reasons.append('MISSING_SOURCE_NOTE')
                else:
                    reasons.extend(s['reasons'])
                    markings.append([s['dynamic_marking'], s['state']])
                e = events.get(ref)
                if e is None or e['pitch'] is None or F(e['pitch']).denominator != 1:
                    reasons.append('UNKNOWN_WRITTEN_PITCH')
                else:
                    pitches.append(str(F(e['pitch'])))
                    times.append([e['onset_q'], e['duration_q']])
                string, fret = n.get('string'), n.get('fret')
                if type(string) is not int or type(fret) is not int or fret < 0:
                    reasons.append('UNKNOWN_PHYSICAL_NOTE')
                physical.append([string, fret])
            if len(refs) != 3 or len(set(refs)) != 3:
                reasons.append('INCOMPLETE_TRIPLE')
            if len(pitches) != 3 or len(times) != 3:
                reasons.append('INCOMPLETE_PITCH_CLOCK')
            else:
                if any(F(a[0])+F(a[1]) != F(b[0]) for a,b in zip(times,times[1:])):
                    reasons.append('NOT_CONTIGUOUS_WRITTEN_ATTACKS')
                a, b = F(times[0][0]), F(times[-1][0])+F(times[-1][1])
                if any(e['id'] not in refs and
                    ((F(e['duration_q']) > 0 and F(e['onset_q']) < b and F(e['onset_q'])+F(e['duration_q']) > a)
                     or (F(e['duration_q']) == 0 and a <= F(e['onset_q']) < b))
                    for e in bypart[pid]):
                    reasons.append('OTHER_SAME_PART_NOTES_OVERLAP')
            if len(physical) != 3 or len({p[0] for p in physical}) != 1:
                reasons.append('NOT_ONE_PHYSICAL_STRING')
            closure_refs = []
            for node in closure:
                b = node['raw']
                closure_refs.append(node['beat_ref'])
                for ni, n in enumerate(b.get('notes', [])):
                    ref = f"event:{part['songId']}:{pid}:{node['bar']}:{voice}:{node['beat']}:{ni}"
                    closure_refs.append(ref)
                    if ref in pinned:
                        reasons.append('NEIGHBOR_LINKED_EXECUTION')
                    if any(k in n and n[k] is not None and n[k] is not False for k in NOTE_EXPRESSION):
                        reasons.append('NEIGHBOR_NOTE_EXECUTION')
                if any(k in b and b[k] is not None and b[k] is not False for k in BEAT_EXPRESSION):
                    reasons.append('NEIGHBOR_BEAT_EXECUTION')
            middle = nodes[1]
            target_ref = f"event:{part['songId']}:{pid}:{middle['bar']}:{voice}:{middle['beat']}:0"
            key = None
            if not reasons:
                key = dict(part=pid, voice=voice, string=physical[1][0],
                    outer_pitches=[pitches[0],pitches[2]], directions=contour(pitches),
                    written_rhythm=[t[1] for t in times], emphasis=markings,
                    source_meter=[states[r]['source_meter'] for r in refs],
                    bar_positions=[states[r]['position_q'] for r in refs],
                    chord_declarations=[deepcopy(n['raw'].get('chord')) for n in nodes])
            rows.append(dict(target_ref=target_ref, occurrence_refs=refs,
                closure_refs=sorted(set(closure_refs)), part_id=pid, voice=voice,
                bar=middle['bar'], beat=middle['beat'],
                note_ref=middle['beat_ref']+'/notes/0',
                pitches=pitches, physical=physical, times=times,
                context_key=key, reasons=sorted(set(reasons))))
    return dict(schema='source-melodic-neighborhoods/1', neighborhoods=rows,
        meaning='Adjacent written notes on one string; not inferred phrases, roles, keys or artist preference')


def source_options(view, target_ref):
    """Source candidates only; harmony and whole-output checks still required."""
    target = next((r for r in view['neighborhoods'] if r['target_ref']==target_ref), None)
    if target is None:
        raise ValueError('Original middle-note occurrence required')
    donors = [r for r in view['neighborhoods'] if target['context_key'] is not None
        and r['context_key']==target['context_key']
        and not set(r['closure_refs']).intersection(target['closure_refs'])]
    witness = next(([a['target_ref'],b['target_ref']] for i,a in enumerate(donors)
        for b in donors[i+1:] if a['pitches'][1]!=b['pitches'][1]
        and not set(a['closure_refs']).intersection(b['closure_refs'])), None)
    groups = defaultdict(list)
    for donor in donors:
        groups[donor['pitches'][1]].append(donor['target_ref'])
    observed = [dict(pitch=p, donor_refs=sorted(rs), changed=p!=target['pitches'][1])
        for p,rs in sorted(groups.items(), key=lambda x:F(x[0]))]
    return dict(target=deepcopy(target), observed_options=observed,
        witness_pair=witness, options=deepcopy(observed) if witness else [],
        status='REFUSED_SOURCE_NEIGHBORHOOD' if target['reasons'] else
        'INDEPENDENT_MELODIC_ALTERNATIVES' if witness else 'NO_INDEPENDENT_MELODIC_ALTERNATIVES')


def validate_controls(controls):
    if type(controls) is not dict or set(controls)!={'context_policy','melody','target_ref','seed'} or controls['context_policy']!=POLICY:
        raise ValueError('Explicit local melody controls required; all other dimensions locked')
    p=controls['melody']
    if type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=100:
        raise ValueError('Melody release must be0..100')
    if type(controls['seed']) is not int or type(controls['target_ref']) is not str or not controls['target_ref'].startswith('event:'):
        raise ValueError('Original note identity and typed seed required')


def sample(evidence, controls):
    validate_controls(controls)
    from declared_degree_choices import sample as release
    chosen, report=release(evidence,dict(voicing=controls['melody'],seed=controls['seed']))
    if chosen is not None:
        report['status']='SOURCE_SUPPORTED_MELODIC_NOTE' if report['changed'] else 'OBSERVED_COINCIDENCE'
    return chosen,report
