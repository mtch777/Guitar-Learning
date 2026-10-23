"""Research query-local bass likelihood; unchanged PC sequence inference.

P(K_t|all PC masks,B_t) is proportional to the existing PC posterior times
P(B_t|K_t,current mask), under explicit conditional independence. This is NOT
joint inference over every bass event, a bass-is-tonic rule or a product model.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import math
import random
from tonal_context_observations import rotate

FIELDS={'piece','observation_ref','start_q','end_q','status','lowest_midi','lowest_pc','lowest_note_refs','active_note_refs','unknown_note_refs'}


def validate_feature(feature,mask):
    if type(mask) is not int or not 0<=mask<4096:raise ValueError('Typed observed PC mask required')
    if type(feature) is not dict or set(feature)!=FIELDS:raise ValueError('Only label-free typed bass evidence accepted')
    if type(feature['piece']) is not str or type(feature['observation_ref']) not in (str,int):raise ValueError('Typed source identity required')
    for key in ('start_q','end_q'):
        if type(feature[key]) is not str or str(F(feature[key]))!=feature[key]:raise ValueError('Canonical source clock required')
    if F(feature['end_q'])<=F(feature['start_q']):raise ValueError('Positive source interval required')
    for key in ('lowest_note_refs','active_note_refs','unknown_note_refs'):
        refs=feature[key]
        if type(refs) is not list or any(type(r) is not str or not r for r in refs) or len(refs)!=len(set(refs)):raise ValueError('Exact unique source witnesses required')
    active=set(feature['active_note_refs'])
    if not set(feature['lowest_note_refs'])<=active or not set(feature['unknown_note_refs'])<=active:raise ValueError('Witness outside active source notes')
    if feature['status']=='KNOWN':
        pitch=feature['lowest_midi'];pc=feature['lowest_pc']
        if type(pitch) is not int or not 0<=pitch<=127 or type(pc) is not int or pc!=pitch%12 or not mask&(1<<pc) or not feature['lowest_note_refs'] or feature['unknown_note_refs']:raise ValueError('Contradictory known lowest-pitch evidence')
    elif feature['status'] in ('EMPTY','UNRESOLVED'):
        if feature['lowest_midi'] is not None or feature['lowest_pc'] is not None or feature['lowest_note_refs']:raise ValueError('Missing bass cannot carry an invented lowest note')
        if feature['status']=='EMPTY' and (active or mask):raise ValueError('Empty support contradicts observed mask')
        if feature['status']=='UNRESOLVED' and not feature['unknown_note_refs']:raise ValueError('Unresolved bass needs unknown source witnesses')
    else:raise ValueError('Unknown feature availability')


def fit(pieces,features,shuffle=False,seed=9427):
    if not pieces or any(p['split']!='train' for p in pieces) or len({p['piece'] for p in pieces})!=len(pieces):raise ValueError('Unique training pieces only')
    rows=[]
    for piece in pieces:
        observed=[r for r in piece['rows'] if not r['quarantine_reasons']]
        inventory=features[piece['piece']]
        source_ids={r['id'] for r in piece['source_observations']}
        if len(source_ids)!=len(piece['source_observations']) or set(inventory)!=source_ids or not {r['id'] for r in observed}<=source_ids:raise ValueError('Complete source-only feature denominator required')
        for source in piece['source_observations']:
            feature=inventory[source['id']];validate_feature(feature,source['mask'])
            if feature['piece']!=piece['piece'] or feature['observation_ref']!=source['id'] or (feature['start_q'],feature['end_q'])!=(source['start_q'],source['end_q']):raise ValueError('Source feature join differs')
        for row in observed:
            feature=inventory[row['id']];validate_feature(feature,row['mask'])
            if feature['piece']!=piece['piece'] or feature['observation_ref']!=row['id'] or (feature['start_q'],feature['end_q'])!=(row['start_q'],row['end_q']):raise ValueError('Source feature join differs')
            state=row['target']['state']
            if type(state) is not int or not 0<=state<24:raise ValueError('Typed supervised training state required')
            rows.append(dict(piece=piece['piece'],work=piece['work'],id=row['id'],mask=row['mask'],state=state,status=feature['status'],bass=feature['lowest_pc']))
    control=[]
    if shuffle:
        groups=defaultdict(list)
        for row in rows:
            if row['status']=='KNOWN':groups[row['work'],row['mask']].append(row)
        rng=random.Random(seed)
        for group_key,group in sorted(groups.items()):
            donors=list(group);rng.shuffle(donors);values=[d['bass'] for d in donors]
            for receiver,donor,bass in zip(group,donors,values):
                control.append(dict(receiver=[receiver['piece'],receiver['id']],donor=[donor['piece'],donor['id']],work=group_key[0],mask=group_key[1]))
                receiver['bass']=bass
    marginal=[[0]*12 for _ in range(2)];contexts=[{},{}];availability=defaultdict(int)
    for row in rows:
        availability[row['status']]+=1
        if row['status']!='KNOWN':continue
        mode,tonic=divmod(row['state'],12);mask=rotate(row['mask'],tonic);bass=(row['bass']-tonic)%12
        marginal[mode][bass]+=1;key=str(mask)
        counts=contexts[mode].setdefault(key,[0]*12);counts[bass]+=1
    return dict(schema='query-local-bass-likelihood/1',marginal=marginal,contexts=contexts,availability=dict(availability),
                training_pieces=sorted(p['piece'] for p in pieces),training_works=sorted({p['work'] for p in pieces}),
                shuffled_control=bool(shuffle),shuffle_seed=seed,control_donors=control,
                semantics='Conditional lowest written pitch PC given current PC mask and candidate major/minor state; no authored role or preferred tonic'),rows


def probability(model,mask,bass_pc,state,alpha):
    if model.get('schema')!='query-local-bass-likelihood/1' or type(state) is not int or not 0<=state<24 or type(bass_pc) is not int or not 0<=bass_pc<12 or type(alpha) not in (int,float) or not math.isfinite(alpha) or alpha<=0:raise ValueError('Typed finite conditional query required')
    relative=rotate(mask,state%12);bass=(bass_pc-state%12)%12;support=[pc for pc in range(12) if relative&(1<<pc)]
    if bass not in support:raise ValueError('Bass must be a member of observed PC set')
    mode=state//12;prior=model['marginal'][mode];denominator=math.fsum(prior[pc]+1/12 for pc in support)
    backoff=(prior[bass]+1/12)/denominator
    counts=model['contexts'][mode].get(str(relative),[0]*12);total=sum(counts)
    return (counts[bass]+alpha*backoff)/(total+alpha)


def update(model,posterior,mask,feature,alpha):
    validate_feature(feature,mask)
    if model.get('schema')!='query-local-bass-likelihood/1' or type(alpha) not in (int,float) or not math.isfinite(alpha) or alpha<=0:raise ValueError('Declared finite conditional model/alpha required')
    if type(posterior) is not list or len(posterior)!=24 or any(type(p) not in (int,float) or not math.isfinite(p) or p<0 or p>1 for p in posterior) or abs(math.fsum(posterior)-1)>1e-10:raise ValueError('Normalized existing PC posterior required')
    if feature['status']!='KNOWN':return dict(posterior=deepcopy(posterior),likelihoods=[1.]*24,status='NEUTRAL_UNAVAILABLE_BASS_EVIDENCE')
    likelihoods=[probability(model,mask,feature['lowest_pc'],state,alpha) for state in range(24)]
    values=[p*l for p,l in zip(posterior,likelihoods)];total=math.fsum(values)
    return dict(posterior=[v/total for v in values],likelihoods=likelihoods,status='QUERY_LOCAL_CONDITIONAL_BASS_UPDATE')
