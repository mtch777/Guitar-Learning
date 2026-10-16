"""Audited playable GP projection of external events; raw output stays separate."""
from collections import Counter,defaultdict
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
from xml.etree import ElementTree as ET
import io,zipfile
from gp_author import write_gp
from source_ablations import fit_pitches


def project(rows,instruments,bars):
    """rows=(onset_q,duration_q,pitch,program); time already quantized by caller."""
    lanes=defaultdict(list);repairs=Counter();previous={}
    for start,duration,pitch,program in sorted(rows,key=lambda r:(r[0],r[3],r[2])):
        start,duration=F(start),F(duration)
        if program==128:repairs['percussion_notes_excluded_from_gp']+=1;continue
        if start<0 or duration<=0:raise ValueError('Invalid external timing')
        if start>=bars*4:continue
        end=min(start+duration,F(bars*4))
        if end<start+duration:repairs['notes_clipped_at_excerpt_end']+=1
        tuning=instruments[program]['tunings'][0]
        fitted=fit_pitches([pitch],tuning)
        p,s,f=fitted[0];repairs['octave_adjusted_notes']+=int(p!=pitch)
        choices=lanes[program];lane=next((l for l in choices if l['end']<=start),None)
        if lane is None:lane=dict(end=F(0),notes=[]);choices.append(lane)
        lane['notes'].append((start,end,dict(midi=p,string=s,fret=f,tie=None,technique_tags=[])));lane['end']=end
    score=dict(source_file='external-model-projection',tracks=[])
    for program,parts in sorted(lanes.items()):
        for first in range(0,len(parts),4):
            track=dict(index=len(score['tracks']),name=instruments[program]['name']+(' '+str(first//4+1) if len(parts)>4 else ''),program=instruments[program].get('program',program),tunings=deepcopy(instruments[program]['tunings']),measures=[])
            for bar in range(bars):
                voices=[];left,right=F(bar*4),F((bar+1)*4)
                for lane in parts[first:first+4]:
                    voice=[];cursor=left
                    for start,end,note in lane['notes']:
                        a,b=max(left,start),min(right,end)
                        if a>=b:continue
                        if a>cursor:voice.append(dict(onset_q=str(cursor),local_onset_q=str(cursor-left),duration_q=str(a-cursor),notes=[]))
                        n=deepcopy(note)
                        if a>start or b<end:n['tie']=dict(origin=str(b<end).lower(),destination=str(a>start).lower())
                        voice.append(dict(onset_q=str(a),local_onset_q=str(a-left),duration_q=str(b-a),notes=[n]));cursor=b
                    if cursor<right:voice.append(dict(onset_q=str(cursor),local_onset_q=str(cursor-left),duration_q=str(right-cursor),notes=[]))
                    voices.append(voice)
                track['measures'].append(dict(number=bar+1,onset_q=str(left),time_signature='4/4',voices=voices))
            score['tracks'].append(track)
    if not score['tracks']:raise ValueError('No pitched model output')
    if len(score['tracks'])>15:raise ValueError('External projection exceeds 15 supported pitched channels')
    return score,dict(repairs)


def write_projected_gp(score,path):
    """Author ordinary notes, then attach only generated cross-bar tie flags."""
    clean=deepcopy(score);ties=[]
    # GP author creates occurrences in measure/track/voice/beat/note order.
    for mi in range(len(clean['tracks'][0]['measures'])):
        for t in clean['tracks']:
            for v in t['measures'][mi]['voices']:
                for e in v:
                    for n in e['notes']:ties.append(n.pop('tie',None))
    write_gp(clean,path,title=Path(path).stem)
    with zipfile.ZipFile(path) as z:assets={n:z.read(n) for n in z.namelist()}
    name=next(n for n in assets if n.endswith('.gpif'));root=ET.fromstring(assets[name]);notes=list(root.find('Notes'))
    if len(notes)!=len(ties):raise AssertionError('Occurrence mismatch attaching generated ties')
    for n,tie in zip(notes,ties):
        if tie:ET.SubElement(n,'Tie',tie)
    assets[name]=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in assets.items():z.writestr(name,data)


def opening_key(notes,seconds=4,part=None,relative=False):
    selected=sorted((n for n in notes if n['start']<seconds and (part is None or n['part']==part)),key=lambda n:(n['start'],n['pitch'],n['end']))
    anchor=selected[0]['pitch'] if selected and relative else 0
    return tuple((round(n['start'],5),round(min(n['end'],seconds),5),n['pitch']-anchor,n['part']) for n in selected)
