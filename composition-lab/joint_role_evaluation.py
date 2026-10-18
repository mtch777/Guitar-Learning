"""Held-out written-root prediction; no harmonic-function/quality claim.

Compare aligned written-minimum-pitch offsets against an absolute-pitch marginal
and within-song shuffled harmony. Training vocabulary is frozen for all methods.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
import argparse,json,math,random
from pathlib import Path
from copy import deepcopy
from corpus_composer import learn
from artist_profiles import connected_families


def balanced(groups):
    result=defaultdict(float)
    for songs in groups.values():
        for counts in songs.values():
            total=sum(counts.values())
            for value,count in counts.items():result[int(value)]+=count/total/len(songs)/len(groups)
    return dict(result)


def evaluate(model,held):
    if set(model['training_songs'])&set(held['training_songs']):raise ValueError('Training/held-out song leakage')
    index={r:defaultdict(list) for r in held['parts']};marginals={};offsets={}
    for role in ('melody','bass'):
        groups=defaultdict(lambda:defaultdict(Counter))
        for family,records in model['parts'][role].items():
            for record in records:
                for e in record['root_events']:groups[family][record['song_id']][str(e['root'])]+=1
        marginals[role]=balanced(groups);offsets[role]=balanced(model['joint_offsets'][role])
    for role,fs in held['parts'].items():
        for records in fs.values():
            for record in records:index[role][record['song_id'],record['bar']].append(record)
    events=defaultdict(list)
    for key,records in index['harmony'].items():
        harmony=min(records,key=lambda p:p['part_id'])
        for role in ('melody','bass'):
            if key not in index[role]:continue
            other=min(index[role][key],key=lambda p:p['part_id'])
            for e in other['root_events']:
                active=[h for h in harmony['root_events'] if F(h['local_q'])<=F(e['local_q'])<F(h['local_q'])+F(h['duration_q'])]
                if active:events[role,key[0]].append((int(active[-1]['root']),int(e['root'])))
    results=[];alpha=1e-4
    for (role,song),pairs in sorted(events.items()):
        anchors=[a for a,b in pairs];random.Random(f'heldout-shuffle:{role}:{song}').shuffle(anchors)
        sums=Counter();unsupported=0
        for (anchor,target),shuffled in zip(pairs,anchors):
            if not(0<=target<=127 and 0<=anchor<=127):unsupported+=1;continue
            def joint(a):
                support=offsets[role];total=sum(v for d,v in support.items() if 0<=a+d<=127)
                return (support.get(target-a,0)+alpha)/(total+128*alpha)
            probabilities=dict(joint=joint(anchor),shuffled_harmony=joint(shuffled),
                absolute_marginal=(marginals[role].get(target,0)+alpha)/(sum(marginals[role].values())+128*alpha))
            for method,p in probabilities.items():sums[method]-=math.log(p)
        n=len(pairs)-unsupported
        results.append(dict(role=role,song_id=song,events=n,unsupported=unsupported,
            shuffled_anchor_changed=sum(a!=s for (a,b),s in zip(pairs,anchors)),
            training_offset_vocabulary=len(offsets[role]),training_marginal_vocabulary=len(marginals[role]),
            nll={k:v/n for k,v in sums.items()} if n else {}))
    return dict(schema='heldout-written-role-root-v1',by_song=results,
        equal_song={role:{method:sum(r['nll'][method] for r in results if r['role']==role and r['events'])/sum(r['role']==role and r['events']>0 for r in results)
            for method in ('joint','shuffled_harmony','absolute_marginal')} for role in ('melody','bass') if any(r['role']==role and r['events'] for r in results)},
        limitations=['Written minimum pitches and heuristic track roles, not functional harmony or intended melody.',
            'Excluded tied/unknown/ambiguous bars; eligibility restricts this evaluation population.',
            'Annotation likelihood only; does not establish full generated-composition quality.',
            'Within-song shuffled anchors can coincide; no forced-difference control.'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','report','corpus','out'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private results only')
    if a.out.exists():p.error('Output exists')
    report=json.loads(a.report.read_text(encoding='utf-8'));connected_families(report['songs'])
    held=deepcopy(report);held['songs']=[s for s in held['songs'] if s['provisional_partition']=='held_out']
    for s in held['songs']:s['provisional_partition']='development'
    model=json.loads(a.model.read_text(encoding='utf-8'));result=evaluate(model,learn(held,a.corpus,model['artist']))
    a.out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result['equal_song']))
