"""Relative approach direction and evidence for corresponding occurrences.

The relationship chooses an existing original/flip realization; it owns no
pitches, clocks or copied note stream. Structural correspondence is evidence for
an intentional control, not a claim about the composer's intended motif.
"""
from copy import deepcopy
from fractions import Fraction as F

import material_approaches as approaches
import melodic_arrival_relation as arrival
from source_observation_evidence import digest
from technique_observation_relations import scalar_relation

SCHEMA = 'live-relative-approach/1'
MODES = ('independent', 'same', 'opposite')
FIELDS = {'schema','source_use','return_use','mode','independent_mode','correspondence'}


def direction_relation(*, source_original_direction, source_mode,
                       return_original_direction, independent_mode, mode):
    if (type(source_original_direction) is not int or source_original_direction not in (-1,1)
            or type(return_original_direction) is not int or return_original_direction not in (-1,1)
            or source_mode not in ('original','flip') or independent_mode not in ('original','flip')
            or mode not in MODES):
        raise ValueError('Explicit signed directions and approach intentions required')
    if mode == 'independent':
        return independent_mode
    direction = source_original_direction * (1 if source_mode == 'original' else -1)
    target = direction * (1 if mode == 'same' else -1)
    return 'original' if target == return_original_direction else 'flip'


def _use(t3, uid):
    matches=[u for u in t3['uses'] if u['id']==uid]
    if len(matches)!=1:
        raise ValueError('One stable approach-use identity required')
    return matches[0]


def annotation_digest(t3):
    lower=t3['lower_tier']
    def relevant(ref):
        return '/marker' in ref or '/signature' in ref or ref.endswith('#/measures')
    return digest(dict(
        structure=[r for r in lower['source_structure']['facts'] if relevant(r['id'])],
        choices=[r for r in lower['owned_parameters']['source_choices'] if relevant(r['fact_ref'])]))


def section_from_annotations(t3, scope):
    """Read only existing marker/meter owners, without reconstructing notes."""
    lower=t3['lower_tier'];facts={r['id']:r for r in lower['source_structure']['facts']}
    choices={r['fact_ref']:r['parameter']for r in lower['owned_parameters']['source_choices']}
    def value(ref):
        row=facts[ref]
        if row['type']=='object':return {facts[r]['slot']:value(r)for r in row['children']}
        if row['type']=='array':return [value(r)for r in row['children']]
        if ref not in choices:raise ValueError('Section annotation has no retained scalar owner')
        return scalar_relation(row['type'],parameter=choices[ref])
    first,last=scope['first_bar'],scope['last_bar']
    if type(first)is not int or type(last)is not int or not 1<=first<=last:
        raise ValueError('Positive complete section scope required')
    consensus=None;clock=None;parts=set()
    for ref,row in facts.items():
        if not ref.startswith('track-')or not ref.endswith('.json#/measures'):continue
        part=int(ref.split('.json#',1)[0].split('-')[1]);parts.add(part)
        measures=row['children'];markers=[]
        if row['type']!='array'or len(measures)<last:raise ValueError('Incomplete annotated source section')
        for bar,measure in enumerate(measures,1):
            marker=measure+'/marker'
            if marker not in facts:continue
            annotation=value(marker)
            if type(annotation)is not dict or type(annotation.get('text'))is not str or not annotation['text'].strip():
                raise ValueError('Section marker text is missing or ambiguous')
            markers.append((bar,annotation['text']))
        prior=[m for m in markers if m[0]<=first]
        if not prior:raise ValueError('No retained source annotation encloses the approach')
        start,label=prior[-1];end=next((b-1 for b,_ in markers if b>start),len(measures))
        if last>end:raise ValueError('Approach crosses an annotated section boundary')
        current=(start,end,label)
        if consensus is not None and current!=consensus:raise ValueError('Retained section annotations disagree')
        consensus=current
        if part==scope['parts'][0]:
            at=F(0);meter=None;bounds={1:at}
            for bar,measure in enumerate(measures,1):
                if measure+'/signature'in facts:meter=value(measure+'/signature')
                if (type(meter)is not list or len(meter)!=2 or any(type(v)is not int or v<=0 for v in meter)):
                    raise ValueError('Explicit positive source meter is required')
                at+=4*F(*meter);bounds[bar+1]=at
            clock=(str(bounds[start]),str(bounds[end+1]-bounds[start]))
    if consensus is None or not set(scope['parts'])<=parts or clock is None:
        raise ValueError('Complete annotated source tracks required')
    return dict(first_bar=consensus[0],last_bar=consensus[1],label=consensus[2],start_q=clock[0],span_q=clock[1])


def validate_thematic_mapping(t3, correspondence, source_use, return_use):
    """The melodic relation belongs to the existing T5 section correspondence."""
    for name,uid in (('source_section',source_use),('return_section',return_use)):
        slot=t3['slots'][_use(t3,uid)['slot_ref']]
        if section_from_annotations(t3,slot['scope'])!=correspondence[name]:
            raise ValueError('Melodic correspondence differs from the existing thematic sections')


def _replace(value, mapping):
    if isinstance(value,str):
        for before,after in sorted(mapping.items(),key=lambda x:len(x[0]),reverse=True):
            value=value.replace(before,after)
        return value
    if isinstance(value,list):return [_replace(v,mapping)for v in value]
    if isinstance(value,dict):return {k:_replace(v,mapping)for k,v in value.items()}
    return value


def _technique_signature(declaration, note, beat):
    """Relocate owned addresses, retaining technique values and structure."""
    out=_replace(declaration,{note:'NOTE',beat:'BEAT'})
    prefixes=sorted(((ref.split('#',1)[1],alias)for ref,alias in((note,'NOTE'),(beat,'BEAT'))),
                    key=lambda pair:len(pair[0]),reverse=True)
    for row in out['structure']:
        pointer=row['pointer']
        for prefix,alias in prefixes:
            if pointer==prefix or pointer.startswith(prefix+'/'):
                row['pointer']=alias+pointer[len(prefix):]
                break
        else:raise ValueError('Technique structure lies outside its approach member')
    return out


def signature(definition, slot, section):
    spec=definition['approach'];relation=spec['relation']
    arrival.validate(relation)
    if (definition['schema']!=approaches.SCHEMA or len(slot['scope']['parts'])!=1
            or not section['first_bar']<=slot['scope']['first_bar']<=slot['scope']['last_bar']<=section['last_bar']):
        raise ValueError('One complete melodic line within its declared section required')
    rows=approaches._bindings(definition,spec['path_ref'])
    bindings={b['attack']:b for b in definition['bindings'] if b['pitch_path_ref']==spec['path_ref']}
    slots={s['beat_ref']:s for s in definition['slots']}
    pulses=[F(0)]
    for share in definition['pulse_shares']:pulses.append(pulses[-1]+F(share)*F(definition['span_q']))
    starts=[];ends=[];mapping={};voices=set();flags=[]
    positions={r['occurrence_ref']:r['fact_ref'].rsplit('/',1)[0]for r in definition['lower_tier']['physical_positions']}
    for attack_index,group in enumerate(spec['attack_groups']):
        previous=None;member_flags=[]
        for i in group:
            ref=rows[i][1];beat=bindings[i]['beat_ref'];s=slots[beat]
            if previous is not None and previous!=s['from_pulse']:
                raise ValueError('Tied approach members must retain a contiguous clock')
            previous=s['to_pulse'];voices.add(int(ref.split(':')[4]))
            note=positions[ref];mapping[ref]=f'event:{i}';mapping[note]=f'note:{i}';mapping[beat]=f'beat:{i}'
            # Physical positions, notation and dynamics may differ between
            # occurrences. Their technique/attack meanings must correspond.
            choices=[]
            for choice in definition['lower_tier']['source_choices']:
                fact=choice['fact_ref'];suffix=fact[len(note):] if fact.startswith(note+'/') else None
                if suffix is not None and suffix not in ('/string','/fret'):
                    choices.append(_replace(choice,{note:'NOTE'}))
                elif fact.startswith(beat+'/') and '/notes/' not in fact:
                    field=fact[len(beat)+1:].split('/')[0]
                    if field not in ('duration','type','dots','velocity'):
                        choices.append(_replace(choice,{beat:'BEAT'}))
            techniques=[_technique_signature(r,note,beat)for r in definition['lower_tier']['technique_declarations']
                if r['owner_ref']in (note,beat)]
            member_flags.append(dict(choices=choices,techniques=techniques))
        first=slots[bindings[group[0]]['beat_ref']];last=slots[bindings[group[-1]]['beat_ref']]
        starts.append(pulses[first['from_pulse']]);ends.append(pulses[last['to_pulse']]);flags.append(member_flags)
    if len(voices)!=1 or len(starts)!=relation['count']:
        raise ValueError('Complete stable approach attacks and voice required')
    extent=ends[-1]-starts[0];section_span=F(section['span_q'])
    if extent<=0 or section_span<=0:raise ValueError('Positive approach and section span required')
    return dict(part_id=slot['scope']['parts'][0],voice=next(iter(voices)),count=relation['count'],
        section_position_q=str((F(slot['start_q'])+starts[0]-F(section['start_q']))/section_span),
        section_extent=str(extent/section_span),
        onsets=[str((v-starts[0])/extent)for v in starts],
        durations=[str((b-a)/extent)for a,b in zip(starts,ends)],
        degree_step_magnitudes=[1]*(relation['count']-1),
        tie_members=[len(g)for g in spec['attack_groups']],techniques=flags,
        execution=_replace(definition['observed_execution'],mapping))


def _clock(documents, section, part):
    track=documents[f'track-{part}.json'];at=F(0);signature_value=None;bounds={1:at}
    for bar,item in enumerate(track['measures'],1):
        signature_value=item.get('signature',signature_value)
        if not signature_value:raise ValueError('Explicit meter is required for section correspondence')
        at+=4*F(*signature_value);bounds[bar+1]=at
    return dict(section,start_q=str(bounds[section['first_bar']]),
                span_q=str(bounds[section['last_bar']+1]-bounds[section['first_bar']]))


def fit_correspondence(t3, source_id, return_id, requested, documents):
    from return_approach_control import source_section
    if type(requested)is not dict or set(requested)!={'source_section','return_section'}:
        raise ValueError('Explicit source and return section correspondence required')
    source=_use(t3,source_id);target=_use(t3,return_id);sections={}
    for name,use in (('source_section',source),('return_section',target)):
        slot=t3['slots'][use['slot_ref']]
        section=source_section(documents,slot['scope'])
        brief={k:section[k]for k in ('first_bar','last_bar','label')}
        if requested[name]!=brief:raise ValueError('Declared correspondence differs from source annotations')
        sections[name]=_clock(documents,brief,slot['scope']['parts'][0])
        if sections[name]!=section_from_annotations(t3,slot['scope']):
            raise ValueError('Section annotations disagree across the preceding tier')
    if (sections['source_section']['label']!=sections['return_section']['label']
            or sections['source_section']['last_bar']>=sections['return_section']['first_bar']):
        raise ValueError('Distinct ordered source-labelled corresponding sections required')
    definitions=[t3['materials'][u['material_ref']]for u in (source,target)]
    signatures=[signature(d,t3['slots'][u['slot_ref']],sections[name])for d,u,name in zip(
        definitions,(source,target),('source_section','return_section'))]
    if signatures[0]!=signatures[1]:raise ValueError('Approach occurrences do not share the declared musical structure')
    # Validate both available directions in each occurrence's own collection.
    for definition in definitions:
        for mode in ('original','flip'):arrival.realize(definition['approach']['relation'],mode)
    return dict(sections,signature=signatures[0],source_definition_sha256=digest(definitions[0]),
        return_definition_sha256=digest(definitions[1]),annotation_sha256=annotation_digest(t3))


def validate_and_solve(t3, relationship):
    if (type(relationship)is not dict or set(relationship)!=FIELDS or relationship['schema']!=SCHEMA
            or relationship['source_use']==relationship['return_use']):
        raise ValueError('Closed distinct live approach relationship required')
    source=_use(t3,relationship['source_use']);target=_use(t3,relationship['return_use'])
    if 'approach_mode'not in source or 'approach_mode'in target:
        raise ValueError('T5 must solely own the return approach direction')
    correspondence=relationship['correspondence']
    required={'source_section','return_section','signature','source_definition_sha256','return_definition_sha256','annotation_sha256'}
    if type(correspondence)is not dict or set(correspondence)!=required:
        raise ValueError('Closed immutable correspondence evidence required')
    definitions=[t3['materials'][u['material_ref']]for u in (source,target)]
    for definition,use,name,seal in zip(definitions,(source,target),('source_section','return_section'),
            ('source_definition_sha256','return_definition_sha256')):
        section=correspondence[name]
        if type(section)is not dict or set(section)!={'first_bar','last_bar','label','start_q','span_q'}:
            raise ValueError('Closed section mapping required')
        if section!=section_from_annotations(t3,t3['slots'][use['slot_ref']]['scope']):
            raise ValueError('Saved correspondence differs from retained source annotations')
        if digest(definition)!=correspondence[seal] or signature(definition,t3['slots'][use['slot_ref']],section)!=correspondence['signature']:
            raise ValueError('Bound approach definition or correspondence changed')
    if annotation_digest(t3)!=correspondence['annotation_sha256']:
        raise ValueError('Section annotations or meter changed; correspondence needs reconsideration')
    a,b=correspondence['source_section'],correspondence['return_section']
    if a['label']!=b['label']or a['last_bar']>=b['first_bar']:
        raise ValueError('Distinct ordered corresponding sections required')
    return direction_relation(source_original_direction=definitions[0]['approach']['relation']['original_direction'],
        source_mode=source['approach_mode'],return_original_direction=definitions[1]['approach']['relation']['original_direction'],
        independent_mode=relationship['independent_mode'],mode=relationship['mode'])
