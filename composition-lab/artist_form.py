"""Author-marked section-length/return baseline, not inferred musical form.

Uses exact supplied marker equality within a song. Absent labels never establish
recurrence. Counts of measures do not assert equal duration across source meters.
Generated studies require one fixed meter and explicitly requested target length.
"""
from collections import defaultdict,Counter
from copy import deepcopy
from fractions import Fraction as F
import math,random
from artist_profiles import connected_families,stable_hash
from generation_freedom import validate


def observations(report,composer):
    families=connected_families(report['songs']);parts=defaultdict(Counter)
    for records in composer['parts']['harmony'].values():
        for p in records:parts[p['song_id']][p['part_id']]+=1
    out=[];excluded=Counter()
    for song in report['songs']:
        if song['song_id'] not in parts:continue
        part=min(parts[song['song_id']],key=lambda p:(-parts[song['song_id']][p],p))
        track=next(t for t in song['tracks'] if t['part_id']==part)
        sections=track.get('sections',[])
        if len(sections)<2:excluded['fewer_than_two_source_marked_sections']+=1;continue
        sequence=[];seen={};last={}
        for section in sections:
            bars=[h['bar'] for h in song['shared_layout'] if F(section['start_q'])<=F(h['start_q'])<F(section['end_q'])]
            if not bars:continue
            label=' '.join(str(section.get('label') or '').casefold().split())
            identity=seen.setdefault(label,len(seen)) if label else len(seen)+len(sequence)
            # Unlabelled sections are unique and cannot collide with named IDs.
            identity=('named',identity) if label else ('unknown',len(sequence))
            lag=len(sequence)-last[identity] if identity in last else 0;last[identity]=len(sequence)
            sequence.append(dict(length=len(bars),return_lag=lag,known_label=bool(label)))
        if len(sequence)<2:continue
        out.append(dict(song_id=song['song_id'],family=families[song['song_id']],artist=song.get('artist'),
            partition=song['provisional_partition'],flagged=not(song.get('ai_generated') is False and song.get('is_junk') is False),sections=sequence))
    return out,dict(excluded)


def fit(forms,artist):
    train=[f for f in forms if f['artist']==artist and f['partition']=='development' and not f['flagged']]
    if not train:raise ValueError('No source-marked development forms; no invented fallback')
    groups=defaultdict(list)
    for f in train:groups[f['family']].append(f)
    tables=defaultdict(lambda:defaultdict(float));vocabulary=set();return_coverage=Counter()
    for family,songs in groups.items():
        for song in songs:
            seq=song['sections'];weight=1/len(groups)/len(songs)
            known_returns=[i for i,s in enumerate(seq) if i and s.get('content_identity_supported',True)]
            tables['initial'][str(seq[0]['length'])]+=weight
            tables['section_count'][str(len(seq))]+=weight
            for i,section in enumerate(seq):
                length=str(section['length']);vocabulary.add(length)
                tables['length'][length]+=weight/len(seq)
                if i:
                    known=i in known_returns;return_coverage['supported' if known else 'unsupported']+=1
                    if known:tables['return_lag'][str(section['return_lag'])]+=weight/len(known_returns)
                if i:tables['after:'+str(seq[i-1]['length'])][length]+=weight/(len(seq)-1)
    return dict(schema='author-marker-form-v1',artist=artist,tables={k:dict(v) for k,v in tables.items()},
        vocabulary=sorted(vocabulary,key=int),training_songs=sorted(f['song_id'] for f in train),
        training_families=sorted(groups),training_sha256=stable_hash(train),
        return_opportunity_coverage=dict(return_coverage),
        limitations=['Author-marker equality only; no validated thematic identity or functional section labels.',
            'Length in source measures; source meter/tempo differences are not equivalent seconds.',
            'Zero return lag means no supported prior match, not proven musical novelty.',
            'Unknown current content is excluded from return evidence; missing content may bias observed recurrence rates.',
            'Fixed half conditional/half marginal length mixture is an experimental baseline.'])


def probability(model,length,previous=None,conditional=True):
    vocabulary=model['vocabulary'];key=str(length) if str(length) in vocabulary else '?';alpha=.001
    def p(table):
        total=sum(table.values());return (table.get(key,0)+alpha)/(total+alpha*(len(vocabulary)+1))
    marginal=p(model['tables']['length']);table=model['tables'].get('after:'+str(previous))
    weight=model.get('length_weight',.5)
    return (1-weight)*marginal+weight*p(table) if conditional and table else marginal


def select_length_weight(forms,artist):
    train=[f for f in forms if f['artist']==artist and f['partition']=='development' and not f['flagged']]
    families=sorted({f['family'] for f in train})
    if len(families)<2:raise ValueError('Independent development families required')
    assignment={f:i%min(5,len(families)) for i,f in enumerate(sorted(families,key=stable_hash))}
    losses=defaultdict(lambda:defaultdict(list))
    for fold in sorted(set(assignment.values())):
        m=fit([f for f in train if assignment[f['family']]!=fold],artist)
        for form in train:
            if assignment[form['family']]!=fold:continue
            for weight in (0,.25,.5,.75,1):
                m['length_weight']=weight;loss=0
                for i,s in enumerate(form['sections']):loss-=math.log(probability(m,s['length'],form['sections'][i-1]['length'] if i else None))
                losses[weight][form['family']].append(loss/len(form['sections']))
    scores={w:sum(sum(v)/len(v) for v in fs.values())/len(fs) for w,fs in losses.items()}
    model=fit(train,artist);model['length_weight']=min(scores,key=lambda w:(scores[w],w));model['length_selection']=dict(folds=assignment,nll=scores,metric='development family→song mean length NLL')
    return model


def evaluate(model,forms):
    held=[f for f in forms if f['artist']==model['artist'] and f['partition']=='held_out' and not f['flagged']]
    if any(f['family'] in model['training_families'] or f['song_id'] in model['training_songs'] for f in held):raise ValueError('Form family leakage')
    records=[]
    for form in held:
        scores=Counter();unknown=0
        for i,section in enumerate(form['sections']):
            previous=form['sections'][i-1]['length'] if i else None
            unknown+=str(section['length']) not in model['vocabulary']
            for method in ('conditional','marginal'):scores[method]-=math.log(probability(model,section['length'],previous,method=='conditional'))
        records.append(dict(song_id=form['song_id'],sections=len(form['sections']),unknown_lengths=unknown,
            nll={m:v/len(form['sections']) for m,v in scores.items()}))
    return dict(by_song=records,equal_song_nll={m:sum(r['nll'][m] for r in records)/len(records) for m in ('conditional','marginal')} if records else {},
        interpretation='Author-marked length prediction only; does not validate generated whole-song structure.')


def plan(model,bars,seed=17):
    if isinstance(bars,bool) or not isinstance(bars,int) or bars<1:raise ValueError('Positive requested bar count required')
    if not model.get('tables',{}).get('return_lag'):raise ValueError('No supported return evidence')
    rng=random.Random(seed);sections=[];cursor=0
    def choose(table):return int(rng.choices(list(table),weights=list(table.values()),k=1)[0])
    while cursor<bars:
        returns={k:v for k,v in model['tables']['return_lag'].items() if int(k)==0 or int(k)<=len(sections)}
        lag=choose(returns) if sections else 0
        if lag:
            original=sections[-lag];identity=original['identity'];length=original['length']
        else:
            table=model['tables']['initial'] if not sections else model['tables']['length']
            if sections and rng.random()<model.get('length_weight',.5):table=model['tables'].get('after:'+str(sections[-1]['length']),table)
            length=choose(table);identity=len(sections)
        length=min(length,bars-cursor)
        sections.append(dict(start=cursor,length=length,identity=identity,return_lag=lag));cursor+=length
    return sections


def full_plan(model,seed=17):
    """Sample a complete source-supported section count, without 32-bar crop."""
    if not model.get('tables',{}).get('return_lag'):raise ValueError('No supported return evidence')
    rng=random.Random(seed);counter=model['tables']['section_count'];count=int(rng.choices(list(counter),weights=list(counter.values()),k=1)[0])
    # Sample the same mechanism as the bounded planner without clipping: a
    # sufficiently long temporary horizon is NOT used, so no unused decisions.
    sections=[];cursor=0
    def choose(table):return int(rng.choices(list(table),weights=list(table.values()),k=1)[0])
    for index in range(count):
        returns={k:v for k,v in model['tables']['return_lag'].items() if int(k)==0 or int(k)<=index}
        lag=choose(returns) if index else 0
        if lag:original=sections[-lag];identity=original['identity'];length=original['length']
        else:
            table=model['tables']['initial'] if not index else model['tables']['length']
            if index and rng.random()<model.get('length_weight',.5):table=model['tables'].get('after:'+str(sections[-1]['length']),table)
            length=choose(table);identity=index
        sections.append(dict(start=cursor,length=length,identity=identity,return_lag=lag));cursor+=length
    return sections


def arrange(independent_core,sections):
    validate(independent_core);out=deepcopy(independent_core);total=len(out['tracks'][0]['measures'])
    if sum(s['length'] for s in sections)!=total:raise ValueError('Plan must cover requested bars exactly')
    cursor=0
    for section in sections:
        if section['start']!=cursor or section['length']<=0:raise ValueError('Contiguous positive section plan required')
        cursor+=section['length']
    meters={m['time_signature'] for t in out['tracks'] for m in t['measures']}
    if len(meters)!=1:raise ValueError('Form baseline requires fixed generated meter')
    num,den=map(int,next(iter(meters)).split('/'));span=F(num*4,den);bank={};source_cursor=0
    for section in sections:
        identity=section['identity'];length=section['length']
        if identity not in bank:
            bank[identity]=[[deepcopy(m) for m in t['measures'][source_cursor:source_cursor+length]] for t in independent_core['tracks']];source_cursor+=length
        material=bank[identity]
        if any(len(ms)<length for ms in material):raise ValueError('Return longer than established generated section')
        for ti,t in enumerate(out['tracks']):
            for offset,m in enumerate(deepcopy(material[ti][:length])):
                bi=section['start']+offset;m.update(number=bi+1,onset_q=str(bi*span),section=f'Generated section {identity+1}')
                for voice in m['voices']:
                    for e in voice:e['onset_q']=str(bi*span+F(e['local_onset_q']))
                t['measures'][bi]=m
    validate(out);return out
