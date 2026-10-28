"""Typed reversible owners for recognized source technique declarations.

One scalar/unit relationship is solved in either direction. This is not a generic
unknown-field codec: unsupported structures remain unlifted, never hidden here.
"""
from copy import deepcopy
from fractions import Fraction as F
import math
import re
from source_fact_tier1 import validate

NOTE_EFFECTS=frozenset(('hp','bend','slide','harmonic','harmonicFret','ghost','staccato','accentuated','tremolo','vibrato','wideVibrato','leftHandVibrato','velocity','pickScrape'))
BEAT_EFFECTS=frozenset(('palmMute','tapping','letRing','brushStroke','arpeggio','downStroke','downArpeggio','upStroke','pickStroke','fadeIn','tremoloBar','vibrato','wideVibrato','leftHandVibrato','vibratoWithTremoloBar','tremolo','harmonic','gradualVelocity','velocity'))
_UNSET=object()


def scalar_relation(source_type,*,source=_UNSET,parameter=_UNSET,unit='1'):
    """SAME equation source = unit * normalized, plus exact categorical choices."""
    if (source is _UNSET)==(parameter is _UNSET):raise ValueError('Exactly one side of observation relationship required')
    types={'integer':int,'float':float,'boolean':bool,'string':str,'null':type(None)}
    if source_type not in types:raise ValueError('Registered scalar source type required')
    if source is not _UNSET:
        if type(source) is not types[source_type]:raise ValueError('Exact source scalar type differs')
        if source_type in ('integer','float'):
            if not math.isfinite(source):raise ValueError('Finite observation required')
            return dict(normalized=str(F(str(source))/F(unit)),negative_zero=source_type=='float' and source==0 and math.copysign(1,source)<0)
        return dict(symbol=source)
    if source_type in ('integer','float'):
        if set(parameter)!={'normalized','negative_zero'} or type(parameter['negative_zero']) is not bool:raise ValueError('Invalid numerical observation parameter')
        raw=F(parameter['normalized'])*F(unit)
        if str(F(parameter['normalized']))!=parameter['normalized']:raise ValueError('Canonical rational observation required')
        if source_type=='integer':
            if raw.denominator!=1 or parameter['negative_zero']:raise ValueError('Integer observation conflict')
            return int(raw)
        if parameter['negative_zero'] and raw:raise ValueError('Negative zero conflicts with nonzero observation')
        value=-0.0 if parameter['negative_zero'] else float(raw)
        if not math.isfinite(value) or F(str(value))!=raw:raise ValueError('Source float cannot exactly realize rational observation')
        return value
    if set(parameter)!={'symbol'} or type(parameter['symbol']) is not types[source_type]:raise ValueError('Typed categorical observation conflict')
    return parameter['symbol']


def identify(row):
    if not re.fullmatch(r'track-\d+\.json',row['document']):return None
    match=re.fullmatch(r'(/measures/\d+/voices/\d+/beats/\d+)(/notes/\d+)?/([^/]+)',row['pointer'])
    if match is None:return None
    beat,note,field=match.groups();scope='note' if note else 'beat'
    if field not in (NOTE_EFFECTS if note else BEAT_EFFECTS):return None
    return dict(scope=scope,field=field,owner_ref=row['document']+'#'+beat+(note or ''))



def supported_structure(owner,root,rows):
    """One registered shape contract, used for both lift and realization."""
    index={r['id']:r for r in rows}
    if len(index)!=len(rows):return False
    visited=[];seen=set()
    def walk(row):
        if row['id'] in seen:return False
        seen.add(row['id']);visited.append(row['id'])
        if row['type'] not in ('object','array'):return 'children' not in row
        if type(row.get('children')) is not list:return False
        slots=[]
        for i,ident in enumerate(row['children']):
            child=index.get(ident)
            if child is None:return False
            slot=child['slot']
            if row['type']=='object' and type(slot) is not str:return False
            if row['type']=='array' and (type(slot) is not int or slot!=i):return False
            if slot in slots:return False
            slots.append(slot)
            escaped=slot.replace('~','~0').replace('/','~1') if type(slot) is str else str(slot)
            if child['parent']!=row['id'] or child['pointer']!=row['pointer']+'/'+escaped:return False
            if not walk(child):return False
        return True
    if not walk(root) or visited!=[r['id'] for r in rows]:return False
    field=owner['field']
    # Captured direction is a declaration, not a pitched trajectory or a
    # performance model. Future structures/types still require explicit review.
    if field=='pickScrape':return len(rows)==1 and root['type']=='string'
    if field=='downArpeggio':return len(rows)==1 and root['type']=='integer'
    if field=='arpeggio':
        # Registered source declaration only. Duration/shift units and performed
        # note offsets are not established by these literal field names.
        types={'direction':'string','duration':'integer','shift':'integer'}
        return root['type']=='object' and all(
            r['parent']==root['id'] and r['slot'] in types and r['type']==types[r['slot']]
            for r in rows[1:])
    if root['type'] not in ('object','array'):return len(rows)==1
    if field in ('bend','tremoloBar'):
        if root['type']!='object':return False
        for row in rows[1:]:
            tail=row['pointer'][len(root['pointer']):]
            if tail=='/points':
                if row['type']!='array':return False
            elif re.fullmatch(r'/points/\d+',tail):
                if row['type']!='object':return False
            elif tail=='/tone' or re.fullmatch(r'/points/\d+/(?:tone|position|precisePosition|vibrato)',tail):
                if row['type'] in ('object','array'):return False
            else:return False
        return True
    if field=='brushStroke':
        return root['type']=='object' and all(r['pointer'][len(root['pointer']):] in ('/direction','/duration','/shift') and r['type'] not in ('object','array') for r in rows[1:])
    if field=='tremolo':return root['type']=='array' and len(root['children'])==2 and all(r['type'] not in ('object','array') for r in rows[1:])
    return False


def lift(tier1):
    validate(tier1);index={r['id']:r for r in tier1['facts']};groups=[];unsupported=[]
    def descend(ident):
        row=index[ident];return [row]+[r for child in row.get('children',[]) for r in descend(child)]
    for root in tier1['facts']:
        owner=identify(root)
        if owner is None:continue
        rows=descend(root['id']);curve=owner['field'] in ('bend','tremoloBar')
        valid=supported_structure(owner,root,rows)
        if not valid:
            unsupported.append(dict(source_fact_ref=root['id'],field=owner['field'],reason='UNREGISTERED_TECHNIQUE_STRUCTURE'));continue
        structure=[];parameters=[]
        for row in rows:
            shape={k:deepcopy(v) for k,v in row.items() if k!='value'};structure.append(shape)
            if 'value' not in row:continue
            token=row['pointer'].split('/')[-1];unit={'tone':'50','position':'60','precisePosition':'100'}.get(token,'1') if curve else '1'
            if row['type'] not in ('integer','float'):unit='1'
            parameters.append(dict(fact_ref=row['id'],unit=unit,parameter=scalar_relation(row['type'],source=row['value'],unit=unit)))
        groups.append(dict(id='technique:'+root['id'],source_fact_ref=root['id'],**owner,structure=structure,parameters=parameters,meaning='Source technique declaration; numerical units normalized, unspecified execution remains unknown'))
    return dict(schema='technique-observation-relations/1',groups=groups,unsupported=unsupported)


def realize(model):
    if set(model)!={'schema','groups','unsupported'} or model['schema']!='technique-observation-relations/1':raise ValueError('Unknown observation relation interface')
    rows=[];used=set()
    for group in model['groups']:
        if set(group)!={'id','source_fact_ref','scope','field','owner_ref','structure','parameters','meaning'} or group['id']!='technique:'+group['source_fact_ref'] or group['meaning']!='Source technique declaration; numerical units normalized, unspecified execution remains unknown':raise ValueError('Undeclared technique group payload')
        shape_index={r['id']:r for r in group['structure']}
        if len(shape_index)!=len(group['structure']) or group['source_fact_ref'] not in shape_index:raise ValueError('Invalid observation structure')
        root=shape_index[group['source_fact_ref']];owner=identify(root)
        if owner!={k:group[k] for k in ('scope','field','owner_ref')}:raise ValueError('Technique scope/owner mismatch')
        if not supported_structure(owner,root,group['structure']):raise ValueError('Unregistered technique structure')
        params={r['fact_ref']:r for r in group['parameters']}
        if len(params)!=len(group['parameters']):raise ValueError('Duplicate observation parameter')
        scalar_refs=set()
        for shape in group['structure']:
            ident=shape['id']
            if ident in used or 'value' in shape:raise ValueError('Duplicate/raw observation payload')
            base={'id','document','pointer','parent','slot','type'}
            if set(shape)!=base|({'children'} if shape['type'] in ('object','array') else set()):raise ValueError('Undeclared observation structure fields')
            if shape['document']!=root['document'] or not (shape['pointer']==root['pointer'] or shape['pointer'].startswith(root['pointer']+'/')):raise ValueError('Observation escaped source owner')
            if shape['id']!=shape['document']+'#'+shape['pointer']:raise ValueError('Observation source identity differs')
            used.add(ident);row=deepcopy(shape)
            if row['type'] not in ('object','array'):
                scalar_refs.add(ident);p=params[ident]
                if set(p)!={'fact_ref','unit','parameter'}:raise ValueError('Undeclared observation parameter fields')
                curve=group['field'] in ('bend','tremoloBar');token=row['pointer'].split('/')[-1]
                unit={'tone':'50','position':'60','precisePosition':'100'}.get(token,'1') if curve and row['type'] in ('integer','float') else '1'
                if p['unit']!=unit:raise ValueError('Registered source unit cannot be changed')
                row['value']=scalar_relation(row['type'],parameter=p['parameter'],unit=p['unit'])
            rows.append(row)
        if scalar_refs!=set(params):raise ValueError('Unowned observation parameter')
    return rows
