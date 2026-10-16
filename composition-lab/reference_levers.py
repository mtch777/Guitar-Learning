"""Fail-closed property edits and reference-freedom bend experiment. No models."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import zipfile
from xml.etree import ElementTree as ET
from bend_analysis import analyze, extract_score, tie_chains

BEND_PROPERTIES = frozenset(('Bended','BendOriginOffset','BendOriginValue',
    'BendMiddleOffset1','BendMiddleOffset2','BendMiddleValue',
    'BendDestinationOffset','BendDestinationValue'))


def properties(note, names):
    return [ET.tostring(p,encoding='unicode') for p in note.findall('./Properties/Property') if p.get('name') in names]


def strip_allowed(root, allowed):
    out=deepcopy(root)
    for note in out.findall('./Notes/Note'):
        props=note.find('Properties')
        if props is not None:
            for p in list(props):
                if p.get('name') in allowed.get(note.get('id'),()):props.remove(p)
    return ET.tostring(out)


def write_property_edits(source, destination, edits, allowed):
    """Generic note-property transaction. Reject any undeclared or structural edit."""
    source,destination=Path(source),Path(destination)
    if destination.exists():raise FileExistsError(destination)
    if set(edits)-set(allowed):raise ValueError('Undeclared occurrence')
    with zipfile.ZipFile(source) as src:
        original=ET.fromstring(src.read('Content/score.gpif'))
        root=deepcopy(original)
        notes={n.get('id'):n for n in root.findall('./Notes/Note')}
        for ident,replacement in edits.items():
            if ident not in notes:raise ValueError('Unknown note')
            names=set(allowed[ident])
            parsed=[ET.fromstring(x) for x in replacement]
            if any(p.tag!='Property' or p.get('name') not in names for p in parsed):
                raise ValueError('Attempt to modify locked field')
            props=notes[ident].find('Properties')
            if props is None:raise ValueError('Missing property container')
            old=properties(notes[ident],names)
            if old==replacement:continue
            for p in list(props):
                if p.get('name') in names:props.remove(p)
            props.extend(parsed)
        if strip_allowed(original,allowed)!=strip_allowed(root,allowed):raise AssertionError('Locked XML changed')
        destination.parent.mkdir(parents=True,exist_ok=True)
        if ET.tostring(root)==ET.tostring(original):
            shutil.copyfile(source,destination)
        else:
            with zipfile.ZipFile(destination,'w') as dst:
                for member in src.infolist():
                    dst.writestr(member,ET.tostring(root,encoding='utf-8',xml_declaration=True)
                                 if member.filename=='Content/score.gpif' else src.read(member.filename))
    with zipfile.ZipFile(source) as src,zipfile.ZipFile(destination) as dst:
        if src.namelist()!=dst.namelist():raise AssertionError('Archive membership changed')
        for name in src.namelist():
            if name!='Content/score.gpif' and src.read(name)!=dst.read(name):raise AssertionError('Locked member changed')
        if strip_allowed(ET.fromstring(dst.read('Content/score.gpif')),allowed)!=strip_allowed(original,allowed):raise AssertionError('Export lock violation')
    return {'locked_xml_verified':True,'other_archive_members_verified':True,
            'byte_identity':source.read_bytes()==destination.read_bytes(),
            'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}


def curve(peak):
    if not peak:return []
    values={'Bended':None,'BendOriginOffset':0,'BendOriginValue':0,
            'BendMiddleOffset1':50,'BendMiddleOffset2':75,'BendMiddleValue':peak*50,
            'BendDestinationOffset':100,'BendDestinationValue':peak*50}
    result=[]
    for name,value in values.items():
        p=ET.Element('Property',name=name)
        ET.SubElement(p,'Enable' if value is None else 'Float').text=None if value is None else str(value)
        result.append(ET.tostring(p,encoding='unicode'))
    return result


def propose(context,method,seed,reference=None,strength=100):
    """Context deliberately contains no bend annotations. Seed stable per sustain."""
    if set(context)-{'id','duration','string','fret','monophonic'}:raise ValueError('Unexpected context field')
    if not 0<strength<=100:raise ValueError('Use literal identity path for zero')
    if strength==100 and reference is not None:raise ValueError('Reference prohibited at 100')
    if method=='removed':return None
    if method not in ('frequency','contextual'):raise ValueError('Unknown method')
    rng=random.Random(f'{seed}:{context["id"]}')
    # Deliberately generic test prior, not fitted to Time or an artist.
    probability=.25
    if method=='contextual':
        probability=.45 if context['duration']>=1 else .10
        if not context['monophonic']:probability=0
    candidates=[None,1,2]
    weights=[1-probability,probability*.3,probability*.7]
    # Keep original as a candidate at intermediate strengths, including complex curves.
    if reference is not None:
        candidates.append('reference');weights.append(.25)
    logs=[math.log(max(w,1e-300)) for w in weights]
    if reference is not None:logs[-1]+=4*(100-strength)/strength
    top=max(logs);weights=[math.exp(w-top) for w in logs]
    return rng.choices(candidates,weights)[0]


def apply_bends(source,destination,track_index,strength,method='contextual',seed=17):
    if not 0<=strength<=100:raise ValueError('Strength outside 0..100')
    score=extract_score(source);report=analyze(score)
    if not 0<=track_index<len(report['tracks']):raise ValueError('Track index')
    track=report['tracks'][track_index]
    chains,unresolved,dangling=tie_chains(track['occurrences'])
    if unresolved or dangling:raise ValueError('Unresolved ties')
    counts={}
    for t in report['tracks']:
        for r in t['occurrences']:counts[r['note_id']]=counts.get(r['note_id'],0)+1
    selected=track['occurrences']
    if any(counts[r['note_id']]!=1 for r in selected):raise ValueError('Shared note definitions require occurrence cloning')
    with zipfile.ZipFile(source) as z:root=ET.fromstring(z.read('Content/score.gpif'))
    notes={n.get('id'):n for n in root.findall('./Notes/Note')}
    allowed={r['note_id']:BEND_PROPERTIES for r in selected}
    edits={};decisions=[]
    starts={}
    for r in selected:starts[r['onset_q']]=starts.get(r['onset_q'],0)+1
    from fractions import Fraction as F
    for chain in chains:
        first=chain[0]
        context={'id':first['occurrence'],'duration':float(sum((F(r['duration_q']) for r in chain),F(0))),
                 'string':first['string'],'fret':first['fret'],'monophonic':starts[first['onset_q']]==1}
        ref=[properties(notes[r['note_id']],BEND_PROPERTIES) for r in chain]
        choice='reference' if strength==0 else propose(context,method,seed,
                         reference=ref if strength<100 else None,strength=strength)
        for index,r in enumerate(chain):
            if choice=='reference':replacement=ref[index]
            elif choice is None:replacement=[]
            else:
                # A tied sustain rises on its first segment, then holds the target.
                replacement=curve(choice)
                if index:
                    replacement=[x.replace('<Float>0</Float>',f'<Float>{choice*50}</Float>')
                                 if 'name="BendOriginValue"' in x else x for x in replacement]
            edits[r['note_id']]=replacement
        decisions.append({'occurrence':first['occurrence'],'choice':choice})
    audit=write_property_edits(source,destination,edits,allowed)
    return {**audit,'method':method,'strength':strength,'seed':seed,'decisions':decisions,
            'reference_passed_to_proposer':0<strength<100,'scope':'Only selected track note bend properties editable'}
