"""Reversible register coordinates around an explicitly declared chord root.

This relation does not select notes or activate a creative policy.
"""
from fractions import Fraction as F
from chord_degree_definitions import degree_definitions
from chord_degree_relations import pitch_from_degree


def pitches(root_pc,kind,roles):
    definitions={d['token']:d for d in degree_definitions(kind)}
    if type(roles)is not list or not roles:raise ValueError('Nonempty ordered degree roles required')
    result=[]
    for role in roles:
        if type(role)is not dict or set(role)!={'degree_token','relative_octaves'} or type(role['degree_token'])is not str or type(role['relative_octaves'])is not int or role['degree_token']not in definitions:raise ValueError('Typed source degree/register required')
        result.append(F(pitch_from_degree(root_pc,kind,dict(definitions[role['degree_token']],relative_octaves=role['relative_octaves']))))
    return result


def frame_for(root_pc,kind,roles):
    return (min(pitches(root_pc,kind,roles))-root_pc)//12


def relationship(root_pc,kind,*,roles=None,framed=None):
    """Exactly one direction; register = frame + offset in both directions."""
    if (roles is None)==(framed is None):raise ValueError('Exactly one side required')
    if roles is not None:
        frame=frame_for(root_pc,kind,roles)
        return dict(frame_octave=frame,components=[dict(degree_token=r['degree_token'],octave_offset=r['relative_octaves']-frame) for r in roles])
    if type(framed)is not dict or set(framed)!={'frame_octave','components'} or type(framed['frame_octave'])is not int or type(framed['components'])is not list or not framed['components']:raise ValueError('Typed canonical frame required')
    frame=framed['frame_octave'];result=[]
    for item in framed['components']:
        if type(item)is not dict or set(item)!={'degree_token','octave_offset'} or type(item['degree_token'])is not str or type(item['octave_offset'])is not int:raise ValueError('Typed frame component required')
        result.append(dict(degree_token=item['degree_token'],relative_octaves=frame+item['octave_offset']))
    if frame_for(root_pc,kind,result)!=frame:raise ValueError('Noncanonical root frame')
    return result
