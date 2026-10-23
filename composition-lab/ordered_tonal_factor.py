"""Research-only learned ordered-sonority factor; no artist or generation rules.

Categorical set emissions and transposition-equivariant key transitions. Fitting
requires explicit labelled train pieces; external annotations never enter infer.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from math import log,isfinite
from fractions import Fraction as F
import random
from tonal_context_observations import rotate


def fit(pieces,kind,alpha=1,tau=1,seed=9427):
    if kind not in ('marginal','ordered','shuffled_predecessor') or not isfinite(alpha) or not isfinite(tau) or alpha<=0 or tau<=0:raise ValueError('Declared model/grid required')
    if not pieces or any(p['split']!='train' for p in pieces):raise ValueError('Training partition only')
    if len({p['piece'] for p in pieces})!=len(pieces):raise ValueError('Duplicate training piece')
    data=deepcopy(pieces)
    if kind=='shuffled_predecessor':
        bywork=defaultdict(list)
        for piece in data:
            for row in piece['rows']:
                if not row['quarantine_reasons'] and row['previous_mask'] is not None:bywork[piece['work']].append(row)
        rng=random.Random(seed)
        for work,rows in sorted(bywork.items()):
            previous=[r['previous_mask'] for r in rows];rng.shuffle(previous)
            for row,value in zip(rows,previous):row['previous_mask']=value
    marginal=[Counter(),Counter()];contexts=[defaultdict(Counter),defaultdict(Counter)];transitions=[Counter(),Counter()];starts=Counter();totals=[0,0];n=0
    for piece in data:
        previous=None
        for row in piece['rows']:
            if row['quarantine_reasons']:previous=None;continue
            state=row['target']['state']
            if type(state) is not int or not 0<=state<24:raise ValueError('Invalid declared target state')
            tonic=state%12;mode=state//12
            current=rotate(row['mask'],tonic);marginal[mode][current]+=1;totals[mode]+=1;n+=1
            if row['previous_mask'] is not None:contexts[mode][rotate(row['previous_mask'],tonic)][current]+=1
            if previous is None or previous['sequence']!=row['sequence']:starts[mode]+=1
            else:
                prior=previous['target']['state'];transitions[prior//12][(mode,(tonic-prior%12)%12)]+=1
            previous=row
    if any(t==0 for t in totals):raise ValueError('Both declared modes require training support')
    return dict(schema='ordered-sonority-key-factor/1',kind=kind,alpha=alpha,tau=tau,shuffle_seed=seed,training_pieces=sorted(p['piece'] for p in pieces),training_works=sorted({p['work'] for p in pieces}),training_cells=n,
                marginal=[{str(k):v for k,v in c.items()} for c in marginal],mode_totals=totals,
                contexts=[{str(k):{str(j):v for j,v in c.items()} for k,c in mode.items()} for mode in contexts],
                context_totals=[{str(k):sum(c.values()) for k,c in mode.items()} for mode in contexts],
                key_transitions=[{f'{m}:{d}':v for (m,d),v in c.items()} for c in transitions],start_modes={str(k):v for k,v in starts.items()},
                vocabulary=dict(masks=4096,states=24,mode_order=['major','minor'],unmodelled_modes=['dorian','phrygian','lydian','mixolydian','locrian']),
                interpretation='Research distribution under major/minor annotation vocabulary; not a verified key or general modal inference')


def emission(model,current,previous,state):
    tonic=state%12;mode=state//12;current=rotate(current,tonic)
    base=(model['marginal'][mode].get(str(current),0)+1/4096)/(model['mode_totals'][mode]+1)
    if model['kind']=='marginal' or previous is None:return base,False
    context=model['contexts'][mode].get(str(rotate(previous,tonic)),{})
    return (context.get(str(current),0)+model['alpha']*base)/(model['context_totals'][mode].get(str(rotate(previous,tonic)),0)+model['alpha']),not bool(context)


def key_transition(model,left,right):
    mode=left//12;key=f'{right//12}:{(right%12-left%12)%12}';counts=model['key_transitions'][mode]
    return (counts.get(key,0)+model['tau']/24)/(sum(counts.values())+model['tau'])


def infer(model,observations):
    """No target, corpus path, artist or analysis labels are inference inputs."""
    import numpy as np
    if model.get('schema')!='ordered-sonority-key-factor/1':raise ValueError('Unknown factor')
    for r in observations:
        if set(r)!={'id','mask','previous_mask','sequence','start_q','end_q'}:raise ValueError('Inference accepts declared label-free observations only')
    previous=None
    for r in observations:
        rotate(r['mask'],0)
        if r['previous_mask'] is not None:rotate(r['previous_mask'],0)
        if any(type(r[k]) is not str or str(F(r[k]))!=r[k] for k in ('start_q','end_q')) or F(r['end_q'])<=F(r['start_q']):raise ValueError('Canonical positive written interval required')
        if previous is not None and r['sequence']==previous['sequence']:
            if r['start_q']!=previous['end_q'] or r['previous_mask']!=previous['mask']:raise ValueError('Broken source sequence/previous observation')
        elif r['previous_mask'] is not None:raise ValueError('Sequence start has hidden predecessor')
        previous=r
    if len({r['id'] for r in observations})!=len(observations):raise ValueError('Duplicate observation')
    def lse(a,axis=None):
        maximum=np.max(a,axis=axis,keepdims=True);result=maximum+np.log(np.exp(a-maximum).sum(axis=axis,keepdims=True))
        return np.squeeze(result,axis=axis)
    logtrans=np.array([[log(key_transition(model,a,b)) for b in range(24)] for a in range(24)])
    total=sum(model['start_modes'].values());initial=np.array([log((model['start_modes'].get(str(s//12),0)+model['tau']/2)/(total+model['tau'])/12) for s in range(24)])
    result=[];joint_log_likelihood=0.;start=0
    while start<len(observations):
        end=start+1
        while end<len(observations) and observations[end]['sequence']==observations[start]['sequence']:end+=1
        rows=observations[start:end];E=np.array([[log(emission(model,r['mask'],r['previous_mask'],s)[0]) for s in range(24)] for r in rows]);n=len(rows);forward=np.empty((n,24));backward=np.zeros((n,24));viterbi=np.empty((n,24));parents=np.zeros((n,24),dtype=int)
        forward[0]=initial+E[0];z=float(lse(forward[0]));forward[0]-=z;joint_log_likelihood+=z;viterbi[0]=initial+E[0]
        for t in range(1,n):
            forward[t]=E[t]+lse(forward[t-1,:,None]+logtrans,axis=0);z=float(lse(forward[t]));forward[t]-=z;joint_log_likelihood+=z
            scores=viterbi[t-1,:,None]+logtrans;parents[t]=np.argmax(scores,axis=0);viterbi[t]=scores[parents[t],np.arange(24)]+E[t]
        for t in range(n-2,-1,-1):
            backward[t]=lse(logtrans+E[t+1]+backward[t+1],axis=1);backward[t]-=float(lse(backward[t]))
        posterior=forward+backward;posterior-=lse(posterior,axis=1)[:,None];posterior=np.exp(posterior)
        path=[int(np.argmax(viterbi[-1]))]
        for t in range(n-1,0,-1):path.append(int(parents[t,path[-1]]))
        path.reverse()
        for i,row in enumerate(rows):
            probabilities=list(map(float,posterior[i]));result.append(dict(observation_ref=row['id'],start_q=row['start_q'],end_q=row['end_q'],posterior=probabilities,viterbi_witness_state=path[i],marginal_map_state=int(np.argmax(posterior[i])),no_supported_mode_inference_outside_training_vocabulary=True))
        start=end
    return dict(schema='ordered-tonal-context-evidence/1',rows=result,observation_log_likelihood=joint_log_likelihood,inference='offline_forward_backward_not_causal',interpretation='Model-conditioned probabilities and one MAP path witness, not annotated truth or calibrated guitar-domain confidence')


def public_observations(rows):
    return [{k:r[k] for k in ('id','mask','previous_mask','sequence','start_q','end_q')} for r in rows if not r['quarantine_reasons']]
