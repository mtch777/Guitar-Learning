"""V8: empirical section-length and recurrence learning for GP symbolic scores.

Section labels are *annotations* supplied in GP files, not genre templates.
When absent, entire songs are treated as one unsegmented example and the
model reports that structural learning is unsupported by that source.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from pathlib import Path
import copy,json,random,re,zipfile
from xml.etree import ElementTree as ET
from extract import extract_score
from sequence_model import SequenceModel
from sequence_generator_balanced import generate,export_score
from motif_development_v7 import learn_relations,develop


def section_identity(label):
    """Normalize prime markings and trailing parenthesized timestamps, not genre names."""
    label=(label or '').strip().lower().replace('’',"'")
    label=re.sub(r'\s*\([^)]*\d+:\d+[^)]*\)\s*$','',label)
    label=re.sub(r"[\s'′’]+(?=\]$)",'',label)
    label=re.sub(r"[\s'′’]+$",'',label)
    return re.sub(r'\s+',' ',label).strip()


def sections(score):
    """Read explicit annotations; no assumption about 4/8/16-bar phrases."""
    n=score['measure_count']
    if not n:return []
    measures=score['tracks'][0]['measures'] if score['tracks'] else []
    starts=[(m['number'],m['section']) for m in measures if m.get('section')]
    if not starts or starts[0][0]!=1:starts.insert(0,(1,None))
    result=[];seen={}
    for i,(start,label) in enumerate(starts):
        end=(starts[i+1][0]-1) if i+1<len(starts) else n
        if end<start:continue
        identity=section_identity(label)
        if identity and identity in seen:
            relationship='return';reference=seen[identity]
        else:
            relationship='new';reference=None
        if identity and identity not in seen:seen[identity]=len(result)
        result.append({'bars':end-start+1,'relationship':relationship,
                       'reference':reference,'label':label,'start':start,'end':end})
    return result


def train_structure(scores):
    """Corpus-derived section counts, observed durations and recurrence distances.

    No fixed alphabet, intro/chorus ordering, bars per phrase, or ending policy.
    """
    transitions=defaultdict(Counter);durations=defaultdict(Counter)
    initial=Counter();examples=[];songs=0;annotated=0
    for score in scores:
        parts=sections(score)
        if not parts:continue
        songs+=1
        annotated+=int(any(x.get('section') for x in score['tracks'][0]['measures']))
        for i,p in enumerate(parts):
            act=p['relationship']
            durations[act][p['bars']]+=1
            if i==0:initial[act]+=1
            else:transitions[parts[i-1]['relationship']][act]+=1
        examples.append({'song':score['source_file'], 'sections':len(parts),
                         'lengths':[p['bars'] for p in parts],
                         'relationships':[p['relationship'] for p in parts],
                         'source_sections':parts})
    return {'examples':examples,'songs':songs,'annotated_songs':annotated,
            'initial':dict(initial),'transitions':{k:dict(v) for k,v in transitions.items()},
            'durations':{k:dict(v) for k,v in durations.items()}}


def weighted_choice(rng,counts):
    keys=sorted(k for k,v in counts.items() if v>0)
    if not keys:raise ValueError('No observations')
    return rng.choices(keys,weights=[counts[k] for k in keys],k=1)[0]


def plan(model,bars,seed=17):
    if bars<1:raise ValueError('bars must be positive')
    if not model['examples']:raise ValueError('No source sections')
    rng=random.Random(seed)
    # Empirical section transitions; fall back to the observed overall frequency.
    all_actions=Counter(x['relationship'] for e in model['examples'] for x in e['source_sections'])
    result=[];families=[];used=0
    while used<bars:
        last=result[-1]['relationship'] if result else None
        choices=Counter(model['transitions'].get(last,{})) if last else Counter(model['initial'])
        if not choices:choices=all_actions.copy()
        if not families:choices.pop('return',None)
        elif 'return' in choices and not families:choices.pop('return',None)
        if not choices:choices=Counter({'new':1})
        action=weighted_choice(rng,choices)
        if action=='return' and not families:action='new'
        duration_counts=model['durations'].get(action) or model['durations'].get('new')
        length=weighted_choice(rng,duration_counts)
        size=min(length,bars-used)  # explicit requested length can truncate a section
        if action=='return':
            # Favor the empirical return-distance distribution, when available.
            distances=Counter()
            for e in model['examples']:
                for i,x in enumerate(e['source_sections']):
                    if x['relationship']=='return' and x['reference'] is not None:
                        distances[i-x['reference']]+=1
            dist=weighted_choice(rng,distances) if distances else 1
            ref=max(0,len(result)-dist)
            # If referenced section is itself a return, follow its original family.
            family=result[ref]['family']
        else:
            family=len(families)
            families.append(family)
            ref=None
        result.append({'start':used+1,'bars':size,'relationship':action,
                       'family':family,'reference_section':ref})
        used+=size
    return result


def compose(template,output,sources,bars=32,meter='4/4',track_index=0,seed=17,order=4,max_fret=14):
    scores=[extract_score(p) for p in sources]
    structure=train_structure(scores)
    with zipfile.ZipFile(template) as z:root=ET.fromstring(z.read('Content/score.gpif'))
    tracks=root.findall('./Tracks/Track')
    if not 0<=track_index<len(tracks):raise ValueError('Invalid track index')
    tuning_text=tracks[track_index].findtext("./Staves/Staff/Properties/Property[@name='Tuning']/Pitches")
    if not tuning_text:raise ValueError('Output instrument lacks tuning')
    tuning=[int(p) for p in tuning_text.split()]
    seq_model=SequenceModel.from_scores(scores,max_order=order)
    relation_model=learn_relations(scores)
    structure_plan=plan(structure,bars,seed)
    sections_generated=[];counts={'new':0,'return':0};diagnostics=[]
    for i,item in enumerate(structure_plan):
        if item['relationship']=='return':
            original=sections_generated[item['reference_section']]
            # Reuse a self-generated earlier section, never a source passage.
            # Adapt duration by cycling complete generated measures.
            part=[copy.deepcopy(original[j%len(original)]) for j in range(item['bars'])]
            counts['return']+=1
        else:
            part,info=generate(seq_model,tuning,item['bars'],meter,seed+1009*(i+1),max_fret)
            # Learned local relationship transformations, only where compatible.
            part,dev=develop(part,relation_model,tuning,seed+1009*(i+1)+1,max_fret)
            diagnostics.append({'section':i+1,'sampling':info,'motif_operations':len(dev['operations'])})
            counts['new']+=1
        sections_generated.append(part)
    generated=[bar for part in sections_generated for bar in part]
    exported=export_score(template,output,generated,meter,track_index,'Composition V8 — Learned Sections')
    exported.update({'seed':seed,'source_songs':len(scores),
                     'annotated_source_songs':structure['annotated_songs'],
                     'training_events':seq_model.event_count,'structure_plan':structure_plan,
                     'section_counts':counts,'section_details':diagnostics,
                     'learned_durations':structure['durations'],
                     'learned_transitions':structure['transitions'],
                     'limitations':['section discovery currently uses explicit GP section annotations',
                                    'returns repeat earlier generated section measures, not learned detailed transformation',
                                    'source event learner restricted to eligible quantized 4/4 material',
                                    'single selected output instrument and voice; articulations not learned']})
    return exported


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--sources',nargs='+',type=Path,required=True)
    p.add_argument('--template',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bars',type=int,default=32)
    p.add_argument('--meter',default='4/4')
    p.add_argument('--track-index',type=int,default=0)
    p.add_argument('--seed',type=int,default=17)
    p.add_argument('--order',type=int,default=4)
    p.add_argument('--max-fret',type=int,default=14)
    a=p.parse_args()
    report=compose(a.template,a.output,a.sources,a.bars,a.meter,a.track_index,a.seed,a.order,a.max_fret)
    Path(str(a.output)+'.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()