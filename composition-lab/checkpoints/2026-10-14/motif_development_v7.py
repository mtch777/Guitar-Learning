"""Step 7: learn recurrent bar patterns and transposed/varied relationships.

All motif choices arise from source events; no hardcoded chord, genre, root,
phrase length or section form. The maximum analysis span is a resource limit.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
from fractions import Fraction
import json
from pathlib import Path
import random
import zipfile
from xml.etree import ElementTree as ET
from extract import extract_score
from sequence_generator_v6 import generate, playable_positions, export_score
from sequence_model import SequenceModel, event_token


def source_bars(score):
    """Return eligible contiguous 4/4 sequences, preserving pitch sets and rests."""
    sequences=[];seen=set()
    for tr in score['tracks']:
        if not any(tr.get('tunings',[])):continue
        signature=repr([(m['time_signature'],m['voices']) for m in tr['measures']])
        if signature in seen:continue
        seen.add(signature)
        for vi in range(max((len(m['voices']) for m in tr['measures']),default=0)):
            block=[];previous=None
            for m in tr['measures']:
                if m['time_signature']!='4/4' or vi>=len(m['voices']):
                    if block:sequences.append(block)
                    block=[];previous=None;continue
                voice=m['voices'][vi]
                if sum((Fraction(b['duration_q']) for b in voice),Fraction())!=4:
                    if block:sequences.append(block)
                    block=[];previous=None;continue
                events=[];valid=True
                for beat in voice:
                    token,previous=event_token(beat,previous)
                    if token is None:valid=False;break
                    pitches=tuple(sorted(n['midi'] for n in beat['notes'] if n['midi'] is not None))
                    events.append((token[0],pitches))
                if valid:block.append(tuple(events))
                else:
                    if block:sequences.append(block)
                    block=[];previous=None
            if block:sequences.append(block)
    return sequences


def relation(a,b):
    """Aligned rhythmic/voicing skeleton; learn actual transposition/variation."""
    aa=[e for bar in a for e in bar];bb=[e for bar in b for e in bar]
    if len(aa)!=len(bb):return None
    if not aa:return None
    if any(x[0]!=y[0] or len(x[1])!=len(y[1]) for x,y in zip(aa,bb)):return None
    changes=[]
    for x,y in zip(aa,bb):
        if x[1]:
            # Preserve each chord's shape. Chord-shape changes are unsupported in MVP.
            dx=tuple(p-x[1][0] for p in x[1]);dy=tuple(p-y[1][0] for p in y[1])
            if dx!=dy:return None
            changes.append(y[1][0]-x[1][0])
        else:changes.append(None)
    sounding=[x for x in changes if x is not None]
    if not sounding:return None
    main=Counter(sounding).most_common(1)[0][0]
    deviations=sum(v!=main for v in sounding)
    if deviations>max(1,round(len(sounding)*0.25)):return None
    kind='repeat' if not deviations and main==0 else 'transpose' if not deviations else 'vary'
    return {'kind':kind,'offsets':tuple(changes),'transpose':main,'deviations':deviations}


def learn_relations(scores,max_span=4,max_gap=16):
    """Find naturally recurring contiguous source passages, including transpositions."""
    learned=[];tested=0;related_targets=0;eligible_targets=0
    for score in scores:
        for seq in source_bars(score):
            for span in range(1,min(max_span,len(seq)//2)+1):
                for end in range(span,len(seq)-span+1):
                    eligible_targets+=1
                    found=False
                    for start in range(max(0,end-max_gap-span),end-span+1):
                        if end+span>len(seq):continue
                        tested+=1
                        r=relation(seq[start:start+span],seq[end:end+span])
                        if r is not None:
                            found=True
                            learned.append({'span':span,'distance':end-start,**r})
                    related_targets+=int(found)
    return {'relations':learned,'counts':dict(Counter(r['kind'] for r in learned)),
            'tested_pairs':tested,'source_sequences':sum(len(source_bars(x)) for x in scores),
            'max_span':max_span,'max_gap':max_gap,
            'recurrence_rate':related_targets/max(1,eligible_targets)}


def apply_relation(source,rule,tuning,max_fret):
    """Transform an existing generated passage using source-learned interval offsets."""
    flat=[event for bar in source for event in bar]
    if len(flat)!=len(rule['offsets']):return None
    updated=copy.deepcopy(source);out=[event for bar in updated for event in bar]
    for event,offset in zip(out,rule['offsets']):
        if (offset is None)!=(not event['positions']):return None
        if offset is None:continue
        positions=event['positions'];p0=positions[0][0]
        shape=tuple(p-p0 for p,_,_ in positions)
        arranged=playable_positions(p0+offset,shape,tuning,max_fret)
        if arranged is None:return None
        event['positions']=arranged
    return updated


def develop(measures,model,tuning,seed=17,max_fret=14,max_operations=None):
    """Learn recurrence choices, then transform generated passages without copying originals.

    Candidate relation timing and type derive from source; skip unplayable or
    event-incompatible operations. No forced A/B/reprise or specific genre.
    """
    rng=random.Random(seed);output=copy.deepcopy(measures)
    relations=model['relations'];results=[]
    if not relations:return output,{'operations':[],'relation_counts':model['counts']}
    # One decision per target window. We must NOT offer thousands of source
    # pairings as repeated chances to force the same destination to repeat.
    probability=model.get('recurrence_rate',0)
    occupied=set();limit=max_operations if max_operations is not None else len(output)
    compatible_tried=0
    for end in range(1,len(output)):
        if len(results)>=limit:break
        if end in occupied or rng.random()>probability:continue
        options=[]
        for r in relations:
            span=r['span'];start=end-r['distance']
            if start<0 or start+span>end or end+span>len(output):continue
            if any(i in occupied for i in range(end,end+span)):continue
            source_events=[x for bar in output[start:start+span] for x in bar]
            if len(source_events)!=len(r['offsets']):continue
            if any((off is None)!=(not x['positions']) for x,off in zip(source_events,r['offsets'])):continue
            options.append((start,r))
        if not options:continue
        rng.shuffle(options)
        for start,r in options[:25]:
            compatible_tried+=1
            transformed=apply_relation(output[start:start+r['span']],r,tuning,max_fret)
            if transformed is None:continue
            output[end:end+r['span']]=transformed
            occupied.update(range(end,end+r['span']))
            results.append({'source_start_bar':start+1,'target_start_bar':end+1,'span':r['span'],
                            'type':r['kind'],'transpose':r['transpose'],'deviations':r['deviations']})
            break
    return output,{'operations':sorted(results,key=lambda x:x['target_start_bar']),
                   'relation_counts':model['counts'],'candidates_tried':compatible_tried,
                   'source_relationship_probability':probability}


def compose(template,output,sources,bars=16,meter='4/4',track_index=0,seed=17,order=4,max_fret=14):
    with zipfile.ZipFile(template) as z:root=ET.fromstring(z.read('Content/score.gpif'))
    track=root.findall('./Tracks/Track')[track_index]
    tuning_txt=track.findtext("./Staves/Staff/Properties/Property[@name='Tuning']/Pitches")
    if not tuning_txt:raise ValueError('Selected output track lacks tuning')
    tuning=[int(x) for x in tuning_txt.split()]
    scores=[extract_score(p) for p in sources]
    model=SequenceModel.from_scores(scores,max_order=order)
    generated,info=generate(model,tuning,bars,meter,seed,max_fret)
    relations=learn_relations(scores)
    generated,development=develop(generated,relations,tuning,seed+1,max_fret)
    report=export_score(template,output,generated,meter,track_index,'Composition V7 — Learned Motif Relationships')
    report.update(info);report.update(development)
    report.update({'seed':seed,'training_events':model.event_count,'learned_relationships':len(relations['relations']),
                   'limitations':['source relations require matching rhythm/event count/chord shape',
                                  'training only eligible quantized 4/4 sections',
                                  'whole-song structure not yet learned',
                                  'articulation not yet modeled']})
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--sources',type=Path,nargs='+',required=True)
    p.add_argument('--template',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bars',type=int,default=16)
    p.add_argument('--meter',default='4/4')
    p.add_argument('--track-index',type=int,default=0)
    p.add_argument('--seed',type=int,default=17)
    p.add_argument('--order',type=int,default=4)
    p.add_argument('--max-fret',type=int,default=14)
    args=p.parse_args()
    report=compose(args.template,args.output,args.sources,args.bars,args.meter,args.track_index,args.seed,args.order,args.max_fret)
    Path(str(args.output)+'.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()