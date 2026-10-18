"""Reference-freedom controls for NEW canonical scores, not source GP editing.

The proposal is generated independently before mixing. No request forces a
difference. Literal locks are checked semantically; incompatible event topology
is rejected. Source GP technique/XML edits use the separate occurrence writers.
"""
from copy import deepcopy
from fractions import Fraction as F
from technique_strength import released

DIMENSIONS=('form','instrumentation','harmony','melody','bass','rhythm','performance')


def validate(score):
    tracks=score['tracks']
    if not tracks or not tracks[0]['measures']:raise ValueError('Empty score')
    count=len(tracks[0]['measures'])
    for ti,track in enumerate(tracks):
        if track['index']!=ti or len(track['measures'])!=count or len(track['tunings'])!=1:
            raise ValueError('Invalid track layout')
        tuning=track['tunings'][0];program=track.get('program',25)
        if not tuning or len(tuning)>12 or any(isinstance(p,bool) or not isinstance(p,int) or not 0<=p<=127 for p in tuning):raise ValueError('Invalid tuning')
        if isinstance(program,bool) or not isinstance(program,int) or not 0<=program<=127:raise ValueError('Invalid MIDI program')
        q=F(0)
        for mi,m in enumerate(track['measures']):
            if any(k not in ('number','onset_q','time_signature','voices','section') for k in m):raise ValueError('Unsupported generated measure metadata')
            numerator,denominator=map(int,m['time_signature'].split('/'));span=F(numerator*4,denominator)
            if span<=0 or F(m['onset_q'])!=q:raise ValueError('Invalid meter/global onset')
            if m['number']!=mi+1 or not any(m['voices']):raise ValueError('Invalid measure number/empty voices')
            if m['time_signature']!=tracks[0]['measures'][mi]['time_signature']:raise ValueError('Cross-track meter conflict')
            for voice in m['voices']:
                if not voice:continue
                local=F(0)
                for e in voice:
                    if set(e)-{'onset_q','local_onset_q','duration_q','notes'}:raise ValueError('Use source occurrence writer for preserved metadata')
                    if F(e['local_onset_q'])!=local or F(e['onset_q'])!=q+local:raise ValueError('Non-contiguous event/global onset')
                    duration=F(e['duration_q'])
                    if duration<=0:raise ValueError('Nonpositive event duration')
                    local+=duration;strings=set()
                    for n in e['notes']:
                        if set(n)-{'midi','string','fret','tie','technique_tags'}:raise ValueError('Unsupported source note metadata')
                        p,s,f=(n[k] for k in ('midi','string','fret'))
                        if n.get('tie') is not None or n.get('technique_tags'):raise ValueError('Performance requires separate verified occurrence editing')
                        if not all(isinstance(v,int) and not isinstance(v,bool) for v in (p,s,f)):raise ValueError('Non-integer fingering')
                        if not 0<=p<=127 or not 0<=s<len(track['tunings'][0]) or not 0<=f<=24 or track['tunings'][0][s]+f!=p or s in strings:
                            raise ValueError('Invalid fingering or duplicate string')
                        strings.add(s)
                    fretted=[n['fret'] for n in e['notes'] if n['fret']>0]
                    if fretted and max(fretted)-min(fretted)>4:raise ValueError('Fretted chord exceeds engineering hand-span bound')
                if local!=span:raise ValueError('Voice does not fill meter')
            q+=span
    return True


def facets(score,roles):
    if len(roles)!=len(score['tracks']) or set(roles)-{'harmony','melody','bass'}:raise ValueError('Explicit supported role per track required')
    out={k:{} for k in DIMENSIONS}
    out['form']['layout']=[[(m['time_signature'],len(m['voices']),m.get('section')) for m in t['measures']] for t in score['tracks']]
    for ti,t in enumerate(score['tracks']):
        out['instrumentation'][str(ti)]=(t['name'],t.get('program'),t['tunings'])
        for mi,m in enumerate(t['measures']):
            for vi,voice in enumerate(m['voices']):
                key=f'{ti}:{mi}:{vi}'
                out['rhythm'][key]=[(e['local_onset_q'],e['duration_q'],bool(e['notes'])) for e in voice]
                out[roles[ti]][key]=[[(n['midi'],n['string'],n['fret']) for n in e['notes']] for e in voice]
                out['performance'][key]=[[(n.get('tie'),n.get('technique_tags',[])) for n in e['notes']] for e in voice]
    return out


def mix(reference,proposal,freedom,roles):
    """Mix independent proposals with nested deterministic release masks.

    Rhythm units are voices within bars; pitch/performance use the same units so
    changes cannot silently erase locked events. Instrumentation/form are whole
    dimensions because tuning/layout changes couple to every fingering.
    """
    if set(freedom)-set(DIMENSIONS):raise ValueError('Unknown freedom dimension')
    amounts={k:freedom.get(k,0) for k in DIMENSIONS}
    for k,v in amounts.items():
        if isinstance(v,bool) or not isinstance(v,int) or not 0<=v<=100:raise ValueError('Integer freedom 0–100 required')
    validate(reference)
    if not any(amounts.values()):
        facets(reference,roles)
        return deepcopy(reference),dict(requested=amounts,all_locked=True,forced_difference=False)
    validate(proposal)
    old=facets(reference,roles);new=facets(proposal,roles)
    if amounts['form']:
        if any(v!=100 for v in amounts.values()):raise ValueError('Form change requires explicit full freedom in coupled dimensions')
        return deepcopy(proposal),dict(requested=amounts,all_proposal=True,forced_difference=False)
    if old['form']!=new['form']:raise ValueError('Proposal layout conflicts with locked form')
    if amounts['instrumentation'] not in (0,100):raise ValueError('Instrumentation supports atomic 0/100 freedom')
    out=deepcopy(reference)
    if amounts['instrumentation']==100:
        for a,b in zip(out['tracks'],proposal['tracks']):
            for k in ('name','program','tunings'):a[k]=deepcopy(b[k])
    release_counts={k:dict(released=0,opportunities=0,changed=0) for k in DIMENSIONS}
    release_counts['form']=dict(released=0,opportunities=1,changed=0)
    release_counts['instrumentation']=dict(released=int(amounts['instrumentation']==100),opportunities=1,
        changed=int(old['instrumentation']!=facets(out,roles)['instrumentation']))
    for ti,t in enumerate(out['tracks']):
        for mi,m in enumerate(t['measures']):
            for vi,ref_voice in enumerate(m['voices']):
                key=f'{ti}:{mi}:{vi}';candidate=proposal['tracks'][ti]['measures'][mi]['voices'][vi]
                pitch_dim=roles[ti]
                flags={d:released((d,key),amounts[d]) for d in ('rhythm',pitch_dim,'performance')}
                target=deepcopy(candidate if flags['rhythm'] else ref_voice)
                pitch_source=candidate if flags[pitch_dim] else ref_voice
                expression_source=candidate if flags['performance'] else ref_voice
                if not(len(target)==len(pitch_source)==len(expression_source)):
                    raise ValueError('Event-count change conflicts with locked pitch/performance topology')
                for e,p,x in zip(target,pitch_source,expression_source):
                    if bool(e['notes'])!=bool(p['notes']):raise ValueError('Rest change conflicts with pitch lock/proposal')
                    notes=deepcopy(p['notes'])
                    if len(notes)!=len(x['notes']):raise ValueError('Voicing-size change conflicts with performance lock/proposal')
                    for n,nx in zip(notes,x['notes']):
                        for field in ('tie','technique_tags'):
                            if field in nx:n[field]=deepcopy(nx[field])
                            else:n.pop(field,None)
                    e['notes']=notes
                m['voices'][vi]=target
                for d in flags:
                    release_counts[d]['opportunities']+=1;release_counts[d]['released']+=int(flags[d])
    validate(out);actual=facets(out,roles)
    for dimension in DIMENSIONS:
        if amounts[dimension]==0 and old[dimension]!=actual[dimension]:raise AssertionError('Literal lock violated: '+dimension)
        if dimension in ('harmony','melody','bass','rhythm','performance'):
            release_counts[dimension]['changed']=sum(v!=actual[dimension].get(k) for k,v in old[dimension].items())
    return out,dict(requested=amounts,units=release_counts,forced_difference=False,
        contract='Release opportunities, not percent musical/perceptual difference; coincidence is allowed.')
