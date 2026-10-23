"""Shared theoretical chord-degree relation; no source spelling or function guess."""
from fractions import Fraction as F
import musical_tier2 as music
from chord_degree_definitions import degree_definitions


def note_role(pitch,label):
    if label is None:return dict(status='NO_SCORED_CHORD',degree_relationships=[])
    if type(pitch) is bool:raise ValueError('Boolean is not a written pitch')
    if type(label.get('root_pc')) is not int or not 0<=label['root_pc']<12 or type(label.get('kind')) is not str or type(label.get('formula')) not in (list,tuple) or any(type(v) is not int or not 0<=v<12 for v in label['formula']):raise ValueError('Typed theoretical chord label required')
    if pitch is None or F(pitch).denominator!=1:return dict(status='UNKNOWN_WRITTEN_PITCH_ROLE',degree_relationships=[])
    relation=music.relation(anchor=label['root_pc'],pitch=pitch);pc=int(F(relation['interval'])%12)
    definitions=degree_definitions(label['kind'])
    if set(label['formula'])!={d['pitch_class'] for d in definitions}:raise ValueError('Chord label contradicts pinned degree definitions')
    matches=[]
    for definition in definitions:
        if definition['pitch_class']!=pc:continue
        octaves=(F(relation['interval'])-definition['theoretical_semitones'])/12
        if octaves.denominator!=1:raise ValueError('Nonintegral chord-degree octave')
        matches.append(dict(**definition,relative_octaves=int(octaves)))
    return dict(status='TEMPLATE_CHORD_TONE' if matches else 'TEMPLATE_NONMEMBER',degree_relationships=matches,
                root_interval_relationship=relation,
                meaning='Role under this chord definition; not authored spelling, key function or intended tension')


def pitch_from_degree(root_pc,kind,degree_relationship):
    """The SAME additive relationship; definition and register choose exact pitch."""
    keys={'token','degree','alteration','theoretical_semitones','pitch_class','relative_octaves'}
    if type(degree_relationship) is not dict or set(degree_relationship)!=keys or type(degree_relationship['token']) is not str or any(type(degree_relationship[k]) is not int for k in keys-{'token'}):raise ValueError('Exact typed degree relationship required')
    if type(root_pc) is not int or not 0<=root_pc<12:raise ValueError('Typed root/register required')
    base={k:v for k,v in degree_relationship.items() if k!='relative_octaves'}
    if base not in degree_definitions(kind):raise ValueError('Relationship contradicts chord definition')
    return music.relation(anchor=root_pc,interval=degree_relationship['theoretical_semitones']+12*degree_relationship['relative_octaves'])['pitch']
