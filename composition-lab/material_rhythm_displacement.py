"""One offset for a coordinated groove body, solved through its shared clock.

The immutable material definition is the reference for every solve. An offset
of zero restores its exact notation, including absent dots. Returned resolved
materials are transient inputs to the existing material inverse, not new source
observations or a replacement for the caller's immutable definition.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import re

import musical_support_material as material
from group_rhythm_relations import relation as clock_relation
from source_rhythm_groups import TYPES
from technique_observation_relations import scalar_relation

MAX_DOTS = 2
BEAT = re.compile(r'track-(\d+)\.json#/measures/(\d+)/voices/0/beats/(\d+)')


def _coordinate(value):
    if type(value) is not str or str(F(value)) != value:
        raise ValueError('Canonical rational offset required')
    return F(value)


def _index(rows, key):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate lower notation authority')
    return result


def _owners(fragment):
    return (_index(fragment['source_structure'], 'id'),
            _index(fragment['source_choices'], 'fact_ref'),
            _index(fragment['coverage'], 'fact_ref'))


def _value(ref, owners, *, notation=False):
    structure, choices, coverage = owners
    if ref not in structure or ref not in choices or ref not in coverage:
        raise ValueError('Missing explicit lower notation authority: ' + ref)
    row, choice = structure[ref], choices[ref]
    if coverage[ref]['owner'] != choice['owner']:
        raise ValueError('Conflicting lower field ownership: ' + ref)
    if notation and (row['type'] != 'integer' or choice['owner'] != 'source_notation_choice'):
        raise ValueError('Integer source notation choice required: ' + ref)
    if 'parameter' not in choice:
        raise ValueError('Unresolved scalar choice: ' + ref)
    return scalar_relation(row['type'], parameter=choice['parameter'])


def _notation(duration_q):
    candidates = [(typ, dots) for dots in range(MAX_DOTS+1) for typ in TYPES
                  if F(4, typ)*(2-F(1, 2**dots)) == duration_q]
    if len(candidates) != 1:
        raise ValueError('Clock has no unique supported type/dots notation: ' + str(duration_q))
    return candidates[0]


def _layout(definition, expanded, ticks):
    owners = _owners(expanded); structure, choices, _ = owners
    bindings = _index(definition['bindings'], 'beat_ref')
    frames = [F(0)]
    for span in definition['bar_spans_q']:
        value = _coordinate(span)
        if value <= 0:
            raise ValueError('Positive bar frames required')
        frames.append(frames[-1]+value)
    scope = definition['scope']
    if len(frames)-1 != scope['last_bar']-scope['first_bar']+1 or any(v not in ticks for v in frames):
        raise ValueError('Complete fixed bar frames required')
    rows = defaultdict(list); notation = {}
    for slot in definition['slots']:
        ref=slot['beat_ref']; match=BEAT.fullmatch(ref)
        if match is None:
            raise ValueError('Explicit voice-zero beat slot required')
        part, index, ordinal = map(int, match.groups()); bar=index+1
        if ref not in structure or structure[ref]['type'] != 'object':
            raise ValueError('Missing beat container authority')
        typ = _value(ref+'/type', owners, notation=True)
        dots = _value(ref+'/dots', owners, notation=True) if ref+'/dots' in structure else 0
        if typ not in TYPES or not 0 <= dots <= MAX_DOTS:
            raise ValueError('Unsupported original type or dots')
        start, end = ticks[slot['from_pulse']], ticks[slot['to_pulse']]
        numerator = _value(ref+'/duration/0', owners, notation=True)
        denominator = _value(ref+'/duration/1', owners, notation=True)
        if numerator <= 0 or denominator <= 0 or F(4*numerator, denominator) != end-start:
            raise ValueError('Original duration and shared clock disagree')
        if F(4,typ)*(2-F(1,2**dots)) != end-start:
            raise ValueError('Original type/dots and shared clock disagree')
        for name in ('dotted','tuplet','tupletStart','tupletStop','graceNote'):
            key=ref+'/'+name
            if key in structure and (structure[key]['type'] in ('object','array') or _value(key,owners) not in (False,None,0)):
                raise ValueError('Unsupported active notation: ' + name)
        binding=bindings.get(ref)
        if binding is not None:
            shape=definition['voicings'][binding['voicing_ref']]
            kind='pitched' if binding['pitch_path_ref'] is not None and all(v is not None for v in shape) else 'unpitched_or_unknown'
        else:
            notes=structure.get(ref+'/notes')
            if notes is None or notes['type'] != 'array':
                raise ValueError('Unclassified silent slot')
            if any(_value(n+'/rest',owners) is not True for n in notes['children']):
                raise ValueError('Non-rest member lacks a complete pitch binding')
            kind='rest'
        rows[(part,bar)].append(dict(slot=slot,ordinal=ordinal,start=start,end=end,kind=kind))
        notation[ref]=(typ,dots)
    used={v for s in definition['slots'] for v in (s['from_pulse'],s['to_pulse'])}
    if used != set(range(len(ticks))):
        raise ValueError('Unbound pulse boundaries cannot define a displacement')
    bars=[]
    for bar in range(scope['first_bar'],scope['last_bar']+1):
        left,right=frames[bar-scope['first_bar']:bar-scope['first_bar']+2]
        pattern=None; first_rows=None
        for part in scope['parts']:
            lane=sorted(rows[(part,bar)],key=lambda r:r['ordinal'])
            parent=f'track-{part}.json#/measures/{bar-1}/voices/0/beats'
            refs=[r['slot']['beat_ref'] for r in lane]
            if (not lane or [r['ordinal'] for r in lane] != list(range(len(lane)))
                    or structure.get(parent,{}).get('children') != refs
                    or lane[0]['start'] != left or lane[-1]['end'] != right
                    or any(a['end'] != b['start'] for a,b in zip(lane,lane[1:]))):
                raise ValueError('Complete contiguous part clock within fixed bar required')
            current=[(r['start'],r['end'],r['kind'])for r in lane]
            if pattern is not None and pattern != current:
                raise ValueError('Coordinated parts must share slot clock and pitched/rest pattern')
            pattern=current; first_rows=lane
        pitched=[r['start']for r in first_rows if r['kind']=='pitched']
        bars.append(dict(bar=bar,start=left,end=right,last_attack=max(pitched)if pitched else None))
    return bars, rows, notation


def _set_integer(fragment, ref, value):
    choice=next(r for r in fragment['source_choices'] if r['fact_ref']==ref)
    choice['parameter']=scalar_relation('integer',source=value)


def _add_dots(fragment, beat_ref, dots):
    structure,choices,coverage=_owners(fragment); ref=beat_ref+'/dots'
    if ref in structure or ref in choices or ref in coverage or ref in structure[beat_ref]['children']:
        raise ValueError('Duplicate dots owner')
    source=structure[beat_ref+'/type']; row=deepcopy(source)
    row.update(id=ref,pointer=source['pointer'][:-len('/type')]+'/dots',slot='dots')
    structure[beat_ref]['children'].append(ref)
    fragment['source_structure'].append(row)
    fragment['source_choices'].append(dict(fact_ref=ref,owner='source_notation_choice',parameter=scalar_relation('integer',source=dots)))
    fragment['coverage'].append(dict(fact_ref=ref,owner='source_notation_choice'))
    return ref


def solve(definition, offset_q):
    """Resolve one absolute offset from the supplied immutable base definition.

    For each bar, move shared boundaries after its start through its final
    pitched attack onset. Bar boundaries and later releases/rest boundaries stay
    fixed. No source files or current/original observation stores are consulted.
    """
    offset=_coordinate(offset_q)
    if type(definition) is not dict or definition.get('schema') != material.MATERIAL:
        raise ValueError('Resolved coordinated-support-material/1 required')
    expanded=material.expand(definition)
    clock=clock_relation(start_q='0',span_q=definition['span_q'],shares=definition['pulse_shares'])
    ticks=list(map(F,clock['onsets_q']))+[F(definition['span_q'])]
    bars,lanes,original_notation=_layout(definition,expanded,ticks)
    result=deepcopy(definition)
    report=dict(offset_q=offset_q,changed=False,shifted_pulses=[],shifted_attacks=[],added_notation_refs=[],notation_changes=[],
        bar_policy=[dict(bar=b['bar'],start_q=str(b['start']),end_q=str(b['end']),last_pitched_attack_q=None if b['last_attack'] is None else str(b['last_attack']))for b in bars])
    if not offset:
        return result,report
    if any(r['kind']=='unpitched_or_unknown'for lane in lanes.values()for r in lane):
        raise ValueError('Dead/unknown members do not establish a pitched groove boundary')
    owners=_owners(expanded)
    for ref in owners[1]:
        if ref.endswith('/tie') and _value(ref,owners) not in (False,None,0):
            raise ValueError('Tied clock displacement requires a supported dependency relationship')
    if definition['observed_execution']:
        raise ValueError('Execution-linked timing is outside this displacement scope')
    changed=list(ticks)
    for i,tick in enumerate(ticks):
        if any(b['last_attack'] is not None and b['start']<tick<=b['last_attack'] for b in bars):
            changed[i]=tick+offset
            report['shifted_pulses'].append(dict(pulse=i,before_q=str(tick),after_q=str(changed[i])))
    if not report['shifted_pulses']:
        raise ValueError('No internal pitched attack can move under this displacement')
    if any(a>=b for a,b in zip(changed,changed[1:])):
        raise ValueError('Offset produces nonpositive durations or crosses a fixed boundary')
    solved=clock_relation(start_q='0',span_q=definition['span_q'],durations_q=[str(b-a)for a,b in zip(changed,changed[1:])])
    result['pulse_shares']=solved['shares']
    structure,_,_=_owners(result['lower_tier'])
    for slot in result['slots']:
        ref=slot['beat_ref'];a,b=slot['from_pulse'],slot['to_pulse']
        typ,dots=_notation(changed[b]-changed[a]);old_type,old_dots=original_notation[ref]
        _set_integer(result['lower_tier'],ref+'/type',typ)
        if ref+'/dots' in structure:
            _set_integer(result['lower_tier'],ref+'/dots',dots)
        elif dots:
            report['added_notation_refs'].append(_add_dots(result['lower_tier'],ref,dots))
        if (typ,dots)!=(old_type,old_dots):
            report['notation_changes'].append(dict(beat_ref=ref,before=dict(type=old_type,dots=old_dots),after=dict(type=typ,dots=dots)))
    for lane in lanes.values():
        for row in lane:
            i=row['slot']['from_pulse']
            if row['kind']=='pitched' and changed[i]!=ticks[i]:
                report['shifted_attacks'].append(dict(beat_ref=row['slot']['beat_ref'],before_q=str(ticks[i]),after_q=str(changed[i])))
    resolved=material.expand(result)
    _layout(result,resolved,changed)
    for key in ('pitch_paths','voicings','bindings','slots','observed_execution','provenance'):
        if result[key]!=definition[key]:
            raise ValueError('Displacement changed a locked musical owner')
    report['changed']=result!=definition
    return result,report
