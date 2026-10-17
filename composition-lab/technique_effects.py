"""Normalize explicit GP effects without guessing missing performance parameters."""
from xml.etree import ElementTree as ET


def normalize_effect(effect):
    root=ET.fromstring(effect['xml']);name=effect['name'];scope=effect['scope']
    base=dict(raw_name=name,scope=scope,raw_xml=effect['xml'],status='mapped',
              rate_hz=None,width_cents=None,rate_provenance='not specified by this marker')
    if name=='Vibrato' and root.tag=='Vibrato' and scope=='note':
        return dict(base,family='finger_vibrato',strength=root.text,source_semantics='note-level GP vibrato')
    if name=='VibratoWTremBar' and scope=='beat':
        return dict(base,family='arm_vibrato',strength=root.findtext('Strength'),source_semantics='beat-level GP tremolo-bar vibrato')
    if name=='Tremolo' and scope=='beat':
        code=(root.text or '').strip();marks={'1/2':1,'1/4':2,'1/8':3}.get(code)
        return dict(base,family='tremolo_picking',notation_code=code,marks=marks,
                    status='mapped' if marks else 'unsupported_notation_value',
                    source_semantics='GP slash count; not interpreted as absolute picking period')
    if name.startswith('Whammy'):
        return dict(base,family='arm_pitch_curve',component=name,source_semantics='curve component; combine at beat level')
    if name=='PickStroke':return dict(base,family='pick_direction',direction=root.findtext('Direction'))
    if name=='Trill':return dict(base,family='trill',source_semantics='retain raw trill target/subdivision; not tremolo picking')
    return dict(base,family='unknown',status='unsupported_effect')


def normalize_report(report):
    from copy import deepcopy
    from collections import Counter
    out=deepcopy(report)
    for track in out['tracks']:
        track['normalized_effects']=[dict(normalize_effect(e),provenance={k:v for k,v in e.items() if k not in ('xml','name')}) for e in track['effects']]
        track['normalized_effect_counts']=dict(Counter(e['family'] for e in track['normalized_effects']))
    out['effect_mapping_version']='gp-explicit-effects-v1'
    return out
