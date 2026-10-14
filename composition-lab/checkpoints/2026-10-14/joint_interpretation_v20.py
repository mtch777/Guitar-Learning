"""Non-destructive joint harmonic / phrase hypotheses from GP observations.

Candidate harmonies are probabilities rather than certain chord assertions. A
sequence-level transition prior is coupled with observed sonorities; potential
harmonic transitions and repeated interval motifs inform phrase boundaries.
This does NOT promote hypotheses to the conservative GP editing anchors.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
from math import exp, log
from harmonic_inference import CHORDS
from automatic_harmony_control import candidate_chords
from phrase_discovery_v19 import discover, pitched


def _events(score, track):
    return sorted((e for m in score['tracks'][track]['measures'] for v in m['voices'] for e in v),
                  key=lambda e:(F(e['onset_q']),e['voice_index']))


def sonorities(score, track):
    """Collect sounding note pitch classes at every attack, including held notes."""
    evs=_events(score, track)
    attacks=sorted({F(e['onset_q']) for e in evs if pitched(e)})
    observations=[]
    for t in attacks:
        sounding=[n for e in evs if F(e['onset_q'])<=t<F(e['onset_q'])+F(e['duration_q'])
                  for n in pitched(e)]
        # Explicit simultaneous observations, not inferred chords.
        if sounding:
            observations.append({'onset':t,'pcs':frozenset(n%12 for n in sounding),
                                 'bass_pc':min(sounding)%12,
                                 'midi':tuple(sounding)})
    return observations


def _candidates(obs, max_candidates=8):
    pcs=obs['pcs']; bass=obs['bass_pc']
    if not pcs:return []
    choices=[]
    for root in range(12):
        for quality,intervals in CHORDS.items():
            template={(root+i)%12 for i in intervals}
            overlap=len(pcs & template)
            if not overlap:continue
            precision=overlap/len(pcs)
            recall=overlap/len(template)
            # Modest bass evidence; favor parsimonious explanation, but leave
            # explicit uncertainty for single-note / incomplete observations.
            score=2.0*precision + 0.7*recall - 0.025*len(template)
            if bass==root:score+=0.12
            elif bass in template:score+=0.03
            choices.append(((root,quality),score))
    return sorted(choices,key=lambda c:(-c[1],c[0]))[:max_candidates]


def interpret(score, track, *, max_candidates=8, transition_penalty=0.35, temperature=0.35):
    """Top chord hypotheses per attack with forward/backward smoothing.

    State space: candidate union across attacks. Emissions from observed
    pitch-class match; transition penalty favors continuity but never makes
    an ambiguous single note a verified chord. Returns marginal probabilities.
    """
    if max_candidates<2 or temperature<=0 or transition_penalty<0:
        raise ValueError('Invalid interpretation parameters')
    obs=sonorities(score,track)
    if not obs:return []
    local=[_candidates(x,max_candidates) for x in obs]
    def lse(vals):
        mx=max(vals)
        return mx+log(sum(exp(v-mx) for v in vals))
    emit=[{c:s/temperature for c,s in row} for row in local]
    fw=[]
    for i,e in enumerate(emit):
        if i==0:fw.append(dict(e));continue
        fw.append({ch:value+lse([fw[-1][prev]-(transition_penalty if prev!=ch else 0) for prev in fw[-1]]) for ch,value in e.items()})
    bw=[None]*len(emit);bw[-1]={ch:0 for ch in emit[-1]}
    for i in range(len(emit)-2,-1,-1):
        bw[i]={ch:lse([emit[i+1][nxt]+bw[i+1][nxt]-(transition_penalty if ch!=nxt else 0) for nxt in emit[i+1]]) for ch in emit[i]}
    output=[]
    for i,row in enumerate(local):
        combined={ch:fw[i][ch]+bw[i][ch] for ch,_ in row}
        z=lse(list(combined.values()))
        ranked=sorted(({'root':ch[0],'quality':ch[1],'probability':exp(v-z)} for ch,v in combined.items()),
                      key=lambda x:-x['probability'])
        exact=candidate_chords(obs[i]['midi'])
        supported=bool(exact)
        output.append({**obs[i], 'candidates':ranked,'confidence':ranked[0]['probability'],
                       'observed_anchor':(exact[0][1] if supported else None),
                       'unresolved':not supported})
    return output


def _motif_starts(score, track, size=3):
    """Repeated interval gestures, transposition invariant, in each voice."""
    starts=defaultdict(list)
    for _,segment in discover(score,track):
        for i in range(len(segment)-size+1):
            group=segment[i:i+size]
            if any(len(pitched(e))!=1 for e in group):continue
            ps=[pitched(e)[0] for e in group]
            durations=tuple(F(e['duration_q']) for e in group)
            key=(tuple(b-a for a,b in zip(ps,ps[1:])),durations)
            starts[key].append(F(group[0]['onset_q']))
    return {t for times in starts.values() if len(set(times))>1 for t in times}


def boundary_evidence(score, track, *, harmonic_weight=0.5, motif_weight=0.5):
    """Join observed gesture segmentation, motif recurrence, and chord marginals.

    A change score is probability the most likely chord at the preceding attack
    differs from the most likely chord at the next attack, approximated using
    independent marginals (not an exact HMM transition posterior).
    No changes to source events and no assertion that scores are calibrated.
    """
    post=interpret(score,track)
    motifs=_motif_starts(score,track)
    gesture_starts={F(seg[0]['onset_q']) for _,seg in discover(score,track) if seg}
    results=[]
    for i,item in enumerate(post):
        onset=item['onset']
        if i:
            prev_anchor=post[i-1]['observed_anchor']
            next_anchor=item['observed_anchor']
            # Only independently verified sonorities contribute hard harmonic
            # boundary evidence. Distributions that spread over many chord
            # candidates do NOT count as chord changes.
            change=(1.0 if (prev_anchor is not None and next_anchor is not None
                            and (prev_anchor.root%12,prev_anchor.degrees)!=
                                (next_anchor.root%12,next_anchor.degrees)) else 0.0)
        else:change=0.0
        # Explain each evidence source, keeping boundary score descriptive.
        motif=onset in motifs
        observed=onset in gesture_starts
        score=min(1.0,(0.5 if observed else 0) +harmonic_weight*change +(motif_weight if motif else 0))
        results.append({'onset':onset,'boundary_score':score,'observed_gesture_start':observed,
                        'motif_recurrence':motif,'harmonic_change_evidence':round(change,5),
                        'top_chord':item['candidates'][0], 'unresolved':item['unresolved']})
    return results


def summary(score,track):
    interpretation=interpret(score,track)
    boundaries=boundary_evidence(score,track)
    return {'observed_attacks':len(interpretation),
            'unresolved_attacks':sum(x['unresolved'] for x in interpretation),
            'verified_sonorities':sum(x['observed_anchor'] is not None for x in interpretation),
            'motif_supported_boundaries':sum(x['motif_recurrence'] for x in boundaries),
            'harmonic_change_boundaries':sum(x['harmonic_change_evidence']>=0.5 for x in boundaries),
            'candidate_boundaries':sum(x['boundary_score']>=0.75 for x in boundaries)}


def joint_phrase_windows(score,track,*,min_size=2,max_size=8,threshold=0.75):
    """V19 gestures refined with independent motif and verified harmony evidence.

    All windows contain monophonic contiguous events; changing a note in one
    cannot rewrite timing or chord definitions. The refinement is optional.
    """
    if min_size<2 or max_size<min_size or not 0<=threshold<=1:
        raise ValueError('Invalid joint phrase constraints')
    cut={x['onset'] for x in boundary_evidence(score,track)
         if x['boundary_score']>=threshold}
    for _,segment in discover(score,track):
        chunks=[];current=[]
        for e in segment:
            if current and F(e['onset_q']) in cut:
                chunks.append(current);current=[]
            current.append(e)
        if current:chunks.append(current)
        for chunk in chunks:
            for size in range(min(max_size,len(chunk)),min_size-1,-1):
                for i in range(len(chunk)-size+1):
                    group=chunk[i:i+size]
                    if any(len(pitched(e))!=1 for e in group):continue
                    if any(F(a['onset_q'])+F(a['duration_q'])!=F(b['onset_q'])
                           for a,b in zip(group,group[1:])):continue
                    yield group