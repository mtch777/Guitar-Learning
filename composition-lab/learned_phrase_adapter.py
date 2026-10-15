"""Explicit lossy view for an external monophonic REMI phrase model.

Canonical source is never modified. Highest note of voice 0 is an experimental
projection, not voice/role inference. Unsupported windows fail rather than
silently dropping timing tokens. No external source code is copied here.
"""
from fractions import Fraction as F
from copy import deepcopy
import json
from pathlib import Path
from source_ablations import fit_pitches


def token_time(value,vocab,prefix):
    value=F(value)
    # Match the upstream float-string convention where aliases exist (notably
    # Position_0 and Position_0.0). Lexical tie-breaking can create a spurious
    # adaptation gain by teaching a rare spelling rather than music.
    canonical=prefix+'_'+str(float(value))
    if canonical in vocab:return canonical,F(0)
    options=[(abs(F(k.split('_',1)[1])-value),k) for k in vocab if k.startswith(prefix+'_')]
    error,token=min(options)
    if error>F(1,200):raise ValueError(f'Unrepresentable {prefix}: {value}')
    return token,error


def view(track,start,count=2):
    notes=[];audit=dict(grace_excluded=0,extra_chord_notes_excluded=0,other_voice_events_excluded=0,tie_continuations_excluded=0)
    measures=track['measures'][start:start+count]
    if len(measures)!=count or any(m['time_signature']!='4/4' for m in measures):raise ValueError('Window requires two 4/4 bars')
    for bar,m in enumerate(measures):
        for vi,v in enumerate(m['voices']):
            if vi:audit['other_voice_events_excluded']+=len(v);continue
            for e in v:
                if e.get('grace_type'):audit['grace_excluded']+=1;continue
                pitched=[n for n in e['notes'] if n['midi'] is not None]
                if not pitched:continue
                n=max(pitched,key=lambda n:n['midi']);audit['extra_chord_notes_excluded']+=len(pitched)-1
                # Attack-only projection: do not invent a new attack at tie destinations.
                # Written attack duration is retained; sustained extensions are not learned.
                if (n.get('tie') or {}).get('destination')=='true':
                    audit['tie_continuations_excluded']+=1;continue
                notes.append(dict(bar=bar,position=F(e['local_onset_q']),duration=F(e['duration_q']),pitch=n['midi']))
    if len(notes)<4:raise ValueError('Insufficient melodic material')
    return notes,audit


def encode(notes,vocab):
    result=[];bar=-1;quantized=0;max_error=F(0)
    for n in notes:
        while bar<n['bar']:result+=['Bar_None','TimeSig_4/4'];bar+=1
        pos,pe=token_time(n['position'],vocab,'Position');dur,de=token_time(n['duration'],vocab,'Duration')
        if F(n['position'])+F(n['duration'])>4:raise ValueError('Cross-bar duration unsupported in this view')
        quantized+=int(bool(pe))+int(bool(de));max_error=max(max_error,pe,de)
        result+=[pos,f"Pitch_{n['pitch']}",dur]
    if any(t not in vocab or vocab[t]>=510 for t in result):raise ValueError('Unknown/out-of-checkpoint-vocabulary token')
    return result,dict(quantized_fields=quantized,max_error_q=str(max_error))


def encoder_tokens(context):
    # Matches official inference ordering without target-derived key/length labels.
    return ['BOS']+context+['SEP','CA_False','SEP','EOS']


def examples(score,track_index,vocab,max_examples=None):
    out=[];rejected=[]
    track=score['tracks'][track_index]
    for start in range(0,len(track['measures'])-3,4):
        try:
            c,ca=view(track,start);t,ta=view(track,start+2)
            ct,cq=encode(c,vocab);tt,tq=encode(t,vocab)
            if len(ct)>350 or len(tt)>250:raise ValueError('Window exceeds experiment token limit')
            out.append(dict(start_bar=start+1,context=ct,target=tt+['EOS'],projection=[ca,ta],quantization=[cq,tq]))
            if max_examples and len(out)>=max_examples:break
        except ValueError as e:rejected.append(dict(start_bar=start+1,reason=str(e)))
    return out,rejected


def rational_token(token):
    raw=F(token.split('_',1)[1]);q=raw.limit_denominator(24)
    if abs(raw-q)>F(1,200):raise ValueError('Timing outside supported rational grid')
    # GP author supports standard dotted/tuplet rational durations, not arbitrary denominators.
    if q.denominator not in (1,2,3,4,6,8,12,16,24):raise ValueError('Non-notatable timing')
    return q


def decode(tokens):
    notes=[];bar=-1;position=None;pitch=None;last_end=F(0)
    for token in tokens:
        if token in ('BOS','EOS','PAD'):continue
        if token=='Bar_None':bar+=1;position=None;last_end=F(0)
        elif token.startswith('TimeSig_'):
            if token!='TimeSig_4/4':raise ValueError('Unexpected generated meter')
        elif token.startswith('Position_'):
            position=rational_token(token)
            if position<last_end or not 0<=position<4:raise ValueError('Nonmonophonic/out-of-bar onset')
        elif token.startswith('Pitch_'):pitch=int(token.split('_')[1])
        elif token.startswith('Duration_'):
            d=rational_token(token)
            if bar<0 or position is None or pitch is None or d<=0 or position+d>4:raise ValueError('Incomplete/out-of-bar note')
            notes.append(dict(bar=bar,position=position,duration=d,pitch=pitch));last_end=position+d;position=None;pitch=None
        else:raise ValueError('Unexpected generated token '+token)
    if not notes or position is not None or pitch is not None:raise ValueError('Incomplete generation')
    return notes


def make_score(notes,track):
    count=max(n['bar'] for n in notes)+1;out=dict(source_file='learned-phrase-continuation',tracks=[])
    t=dict(index=0,name='Learned continuation',tunings=deepcopy(track['tunings']),program=track['program'],measures=[])
    previous=()
    for bar in range(count):
        cursor=F(0);events=[]
        def emit(pos,duration,notes):return dict(onset_q=str(4*bar+pos),local_onset_q=str(pos),duration_q=str(duration),notes=notes)
        for n in [n for n in notes if n['bar']==bar]:
            if n['position']>cursor:events.append(emit(cursor,n['position']-cursor,[]))
            fitted=fit_pitches([n['pitch']],t['tunings'][0],previous)
            if fitted[0][0]!=n['pitch']:raise ValueError('Generated pitch requires octave alteration')
            p,s,f=fitted[0];previous=[(s,f)]
            events.append(emit(n['position'],n['duration'],[dict(midi=p,string=s,fret=f,tie=None,technique_tags=[])]));cursor=n['position']+n['duration']
        if cursor<4:events.append(emit(cursor,4-cursor,[]))
        t['measures'].append(dict(number=bar+1,onset_q=str(bar*4),time_signature='4/4',voices=[events]))
    out['tracks']=[t];return out
