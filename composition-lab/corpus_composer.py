"""Multi-song empirical phrase/role baseline, with no hardcoded artist pitches.

Learns meter/rhythm/voicing/interval and recurrence observations from eligible
development work families. This is an explicit statistical prototype, not a
claim of learned harmonic function, emotional purpose, or listening acceptance.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from fractions import Fraction as F
import hashlib,json,random
from pathlib import Path
from controlled_generation import position_chord
from generation_freedom import validate


def role_for(track,raw):
    program=raw.get('instrumentId',25);name=(track.get('name') or '').casefold()
    if 32<=program<=39:return 'bass','MIDI bass program'
    if any(k in name for k in ('rhythm','ritm','rtm','chug')):return 'harmony','declared rhythm track name'
    if any(k in name for k in ('lead','solo','melody')):return 'melody','declared lead track name'
    grouped=defaultdict(list)
    for n in track['rows']:
        if not n['tie_destination']:grouped[n['onset_q']].append(n)
    poly=sum(len(ns)>1 for ns in grouped.values())/max(1,len(grouped))
    return ('harmony','coattack-density fallback') if poly>=.2 else ('melody','monophonic fallback')


def learn(report,corpus,artist):
    from artist_profiles import connected_families
    family=connected_families(report['songs']);parts={r:defaultdict(list) for r in ('harmony','melody','bass')}
    plans=[];exclusions=Counter();source_sequences=[];training=set()
    for song in report['songs']:
        if song.get('artist')!=artist or song['provisional_partition']!='development' or song.get('ai_generated') is not False or song.get('is_junk') is not False:continue
        for track in song['tracks']:
            if not track.get('guitar_or_bass') or not track.get('temporal_relationships_eligible'):continue
            raw=json.loads((corpus/str(song['song_id'])/f"track-{track['part_id']}.json").read_text(encoding='utf-8-sig'))
            role,reason=role_for(track,raw);tuning=[int(p+(raw.get('capo') or 0)) for p in raw['tuning']]
            if not tuning:continue
            rows=[n for n in track['rows'] if n['voice']==0]
            byid={n['occurrence']:n for n in rows};tied_bars=set()
            for chain in track.get('sustain_relationships',{}).get('chains',[]):
                if len(chain['members'])>1:
                    tied_bars.update(byid[i]['bar'] for i in chain['members'] if i in byid)
            grouped=defaultdict(list)
            for n in rows:grouped[n['bar']].append(n)
            roots=[];patterns=[];section_patterns=defaultdict(list);transitions=Counter();previous_attack=None;segment=0
            for header in song['shared_layout']:
                bar=header['bar'];notes=grouped[bar];span=F(header['span_q']);base=F(header['start_q'])
                if not notes:previous_attack=None;segment+=1;continue
                if bar in tied_bars or any(n['tie_destination'] or n['midi'] is None for n in notes):
                    exclusions['bar_with_tie_or_unknown']+=1;previous_attack=None;segment+=1;continue
                attacks=defaultdict(list)
                for n in notes:attacks[F(n['onset_q'])].append(n)
                cursor=base;events=[];valid=True;bar_roots=[];contour=[]
                for q,ns in sorted(attacks.items()):
                    ds={F(n['duration_q']) for n in ns}
                    if len(ds)!=1 or q<cursor or q+next(iter(ds))>base+span:valid=False;break
                    if q>cursor:events.append(dict(duration_q=str(q-cursor),intervals=[]))
                    ps=sorted(n['midi'] for n in ns);root=min(ps)
                    events.append(dict(duration_q=str(next(iter(ds))),intervals=[p-root for p in ps]))
                    bar_roots.append(dict(root=root,onset_q=str(q),end_q=str(q+next(iter(ds))),section=ns[0]['section_start']))
                    contour.append(root);cursor=q+next(iter(ds))
                if not valid:exclusions['ambiguous_bar']+=1;previous_attack=None;segment+=1;continue
                if cursor<base+span:events.append(dict(duration_q=str(base+span-cursor),intervals=[]))
                if span!=F(header['signature'][0]*4,header['signature'][1]):exclusions['pickup_training_bar']+=1;previous_attack=None;segment+=1;continue
                for current in bar_roots:
                    if previous_attack and previous_attack['end_q']==current['onset_q'] and previous_attack['section']==current['section']:
                        transitions[current['root']-previous_attack['root']]+=1
                    previous_attack=current
                roots.extend(bar_roots)
                record=dict(song_id=song['song_id'],part_id=track['part_id'],bar=bar,
                    meter='/'.join(map(str,header['signature'])),events=events,tuning=tuning,program=raw.get('instrumentId',25),
                    role_evidence=reason,root_center=sum(min(n['midi'] for n in ns) for ns in attacks.values())/len(attacks),
                    root_events=[dict(local_q=str(F(n['onset_q'])-base),duration_q=str(F(n['end_q'])-F(n['onset_q'])),root=n['root']) for n in bar_roots],
                    tempo_bpm=next((p['quarter_bpm'] for p in song['timeline']['tempo'] if F(p['onset_q'])==0),'120'))
                parts[role][family[song['song_id']]].append(record);patterns.append(record);training.add(song['song_id'])
                # Structural recurrence uses a source-normalized bar fingerprint;
                # output pitches are generated afresh, not copied from this bar.
                signature=json.dumps([[(e['duration_q'],e['intervals']) for e in events],[p-contour[0] for p in contour]],separators=(',',':'))
                section_patterns[notes[0]['section_start'],segment].append(signature)
            for record in patterns:record['root_steps']={str(k):v for k,v in transitions.items()}
            for signatures in section_patterns.values():
                seen={};sequence=[]
                for sig in signatures:
                    if sig not in seen:seen[sig]=len(seen)
                    sequence.append(seen[sig])
                if sequence:plans.append(dict(family=family[song['song_id']],song_id=song['song_id'],role=role,sequence=sequence))
            source_sequences.append(dict(song_id=song['song_id'],part_id=track['part_id'],roots=roots))
    if any(not parts[r] for r in parts):raise ValueError('Training corpus lacks one required role; no invented fallback role')
    # Joint observations use aligned source bars, not unrelated songs/keys.
    indexed={r:defaultdict(list) for r in parts}
    for role,fs in parts.items():
        for fam,records in fs.items():
            for record in records:indexed[role][record['song_id'],record['bar']].append((fam,record))
    joint={r:defaultdict(lambda:defaultdict(Counter)) for r in ('melody','bass')}
    for key,hs in indexed['harmony'].items():
        # Select one deterministic representative of duplicated part layouts;
        # retain the approximation rather than claiming adjudicated role truth.
        fam,h=min(hs,key=lambda x:x[1]['part_id'])
        for role in joint:
            if key not in indexed[role]:continue
            _,other=min(indexed[role][key],key=lambda x:x[1]['part_id'])
            for e in other['root_events']:
                active=[n for n in h['root_events'] if F(n['local_q'])<=F(e['local_q'])<F(n['local_q'])+F(n['duration_q'])]
                if active:joint[role][fam][key[0]][str(e['root']-active[-1]['root'])]+=1
    return dict(schema='empirical-corpus-composer-v1',artist=artist,training_songs=sorted(training),
        parts={r:dict(fs) for r,fs in parts.items()},plans=plans,excluded=dict(exclusions),source_sequences=source_sequences,
        joint_offsets={r:{f:{str(song):dict(c) for song,c in ss.items()} for f,ss in fs.items()} for r,fs in joint.items()},
        limitations=['Track roles use declared names/programs and a density fallback; not validated musical intent.',
            'Main written voice only; tie/unknown/ambiguous bars excluded from vocabulary, never erased from source.',
            'Voicing intervals and recurrence/rhythm are observed; root-step model is first-order, not learned harmonic function.',
            'Performance applied separately; plain generated core does not silently claim source techniques.'])


def choose_family(rng,entries):
    family=rng.choice(sorted(entries));songs=defaultdict(list)
    for e in entries[family]:songs[e['song_id']].append(e)
    song=rng.choice(sorted(songs));return rng.choice(songs[song])


def generate(model,bars=32,seed=1):
    if not isinstance(bars,int) or bars<1:raise ValueError('Positive bar count required')
    rng=random.Random(seed);roles=['harmony','melody','bass']
    available=[{(p['song_id'],p['bar']) for ps in model['parts'][r].values() for p in ps} for r in roles]
    common=set.intersection(*available)
    if not common:raise ValueError('No aligned cross-role source configuration; no invented fallback')
    configurations=defaultdict(list)
    for family,ps in model['parts']['harmony'].items():
        for song,bar in sorted(common & {(p['song_id'],p['bar']) for p in ps}):configurations[family].append(dict(song_id=song,bar=bar))
    chosen=choose_family(rng,configurations)
    config={r:rng.choice([p for ps in model['parts'][r].values() for p in ps if p['song_id']==chosen['song_id'] and p['bar']==chosen['bar']]) for r in roles}
    # One observed meter is shared by all roles; no hardcoded 4/4 or pulse grid.
    meter=config['harmony']['meter'];num,den=map(int,meter.split('/'));span=F(num*4,den)
    pools={r:{f:[p for p in ps if p['meter']==meter] for f,ps in model['parts'][r].items() if any(p['meter']==meter for p in ps)} for r in roles}
    if any(not p for p in pools.values()):raise ValueError('No cross-role support for sampled meter')
    plan=[];plan_families=defaultdict(list)
    for p in model['plans']:plan_families[p['family']].append(p)
    while len(plan)<bars:
        source=choose_family(rng,plan_families)
        # A source form sample contributes recurrence relationships only. Cap at
        # requested length, not a fixed invented phrase size.
        start=len(plan);sequence=source['sequence'][:bars-start]
        for motif in sequence:plan.append((start,motif))
    score=dict(source_file='development-only empirical corpus generation',tempo_bpm=config['harmony']['tempo_bpm'],tracks=[]);manifest=[];repairs=Counter()
    harmony_events=[]
    for ti,role in enumerate(roles):
        c=config[role];tuning=c['tuning'];track=dict(index=ti,name=role,program=c['program'],tunings=[tuning],measures=[])
        motifs={};root=round(c['root_center']);previous=()
        for bi,key in enumerate(plan):
            if key in motifs:
                local=deepcopy(motifs[key]);reused=True
                final=next((e['notes'] for e in reversed(local) if e['notes']),None)
                if final:
                    root=min(n['midi'] for n in final);previous=[(n['string'],n['fret']) for n in final]
            else:
                pattern=choose_family(rng,pools[role]);local=[];cursor=F(0);reused=False
                steps=pattern['root_steps'] or {'0':1}
                for source_event in pattern['events']:
                    notes=[]
                    if source_event['intervals']:
                        step=rng.choices(list(steps),weights=list(steps.values()),k=1)[0];target=root+int(step)
                        if role in model.get('joint_offsets',{}):
                            active=[e for e in harmony_events if F(e['onset_q'])<=bi*span+cursor<F(e['onset_q'])+F(e['duration_q']) and e['notes']]
                            support=model['joint_offsets'][role]
                            if active and support:
                                family=rng.choice(sorted(support));song=rng.choice(sorted(support[family]));counter=support[family][song]
                                anchor=min(n['midi'] for n in active[-1]['notes'])
                                candidates=[anchor+int(k) for k in counter]
                                target=rng.choices(candidates,weights=[counter[k]/(1+abs(p-target)) for k,p in zip(counter,candidates)],k=1)[0]
                                repairs['joint_conditioned_attacks']+=1
                            else:repairs['joint_context_backoffs']+=1
                        positions=None
                        for shift in sorted(range(-5,6),key=lambda x:(abs(x),x)):
                            pitches=[target+d+12*shift for d in source_event['intervals']]
                            try:
                                positions=[(p,s,f) for p,(s,f) in zip(pitches,position_chord(pitches,tuning,max_span=4,previous=previous))]
                                break
                            except ValueError:pass
                        if positions is None:raise ValueError('Observed voicing cannot fit chosen target tuning; resample explicitly')
                        fitted=min(p for p,s,f in positions);repairs['octave_refits']+=int(fitted!=target);root=fitted
                        previous=[(s,f) for p,s,f in positions]
                        notes=[dict(midi=p,string=s,fret=f,tie=None,technique_tags=[]) for p,s,f in positions]
                    local.append(dict(local_onset_q=str(cursor),onset_q=str(cursor),duration_q=source_event['duration_q'],notes=notes));cursor+=F(source_event['duration_q'])
                motifs[key]=deepcopy(local)
                manifest.append(dict(track=ti,bar=bi+1,training_song=pattern['song_id'],training_part=pattern['part_id'],training_bar=pattern['bar'],method='resampled observed rhythm/voicing; resynthesized root steps'))
            for e in local:e['onset_q']=str(F(e['local_onset_q'])+bi*span)
            track['measures'].append(dict(number=bi+1,onset_q=str(bi*span),time_signature=meter,voices=[local]))
        score['tracks'].append(track)
        if role=='harmony':harmony_events=[e for m in track['measures'] for v in m['voices'] for e in v]
    validate(score)
    return score,dict(seed=seed,bars=bars,meter=meter,roles=roles,recurrence_plan=plan,sources=manifest,
        repairs=dict(repairs),training_songs=model['training_songs'],limitations=model['limitations'])
