"""Source notation semantics with exact rational time; no inferred artistic labels."""
from collections import Counter, defaultdict
from fractions import Fraction as F
import json


def number(x):
    return F(str(x))


def marker_text(marker):
    return str(marker.get('text') or '(unannotated)') if isinstance(marker,dict) else str(marker or '(unannotated)')


def whole_measure_rest(measure, voice):
    """Recognize the explicit API whole-measure-rest sentinel, not any long rest."""
    beats=voice.get('beats',[])
    if not measure.get('rest') or not voice.get('rest') or len(beats)!=1:return False
    beat=beats[0];notes=beat.get('notes',[])
    return (beat.get('rest') is True and beat.get('type')==1 and beat.get('duration')==[1,1]
            and bool(notes) and all(n.get('rest') is True for n in notes)
            and not any(beat.get(k) for k in ('graceNote','dots','tuplet','tupletStart','tupletStop')))


def filled(measure):
    # A whole-measure rest supplies no independent evidence of pickup length.
    return max((sum((F(*b['duration'])*4 for b in v.get('beats',[]) if not b.get('graceNote') and b.get('duration')),F(0)) for v in measure.get('voices',[]) if not whole_measure_rest(measure,v)),default=F(0))


def layout(parts):
    headers=[];warnings=[];offset=F(0);sig=[4,4]
    count=max((len(t.get('measures',[])) for t in parts),default=0)
    pickup=any(t.get('anacrusis') for t in parts)
    pickup_span=max((filled(t['measures'][0]) for t in parts if t.get('measures')),default=F(0))
    for i in range(count):
        measures=[t['measures'][i] for t in parts if i<len(t.get('measures',[]))]
        signatures={tuple(m['signature']) for m in measures if m.get('signature')}
        if len(signatures)>1:warnings.append(dict(bar=i+1,reason='conflicting_track_meter'))
        if signatures:sig=list(sorted(signatures)[0])
        nominal=F(4*sig[0],sig[1]);span=nominal
        if i==0 and pickup and 0<pickup_span<nominal:span=pickup_span
        repeats={int(m['repeat']) for m in measures if m.get('repeat')}
        endings={tuple(m['alternateEnding']) for m in measures if m.get('alternateEnding')}
        if len(repeats)>1 or len(endings)>1:warnings.append(dict(bar=i+1,reason='conflicting_track_repeat'))
        headers.append(dict(bar=i+1,start_q=str(offset),span_q=str(span),signature=sig[:],
                            pickup=span!=nominal,repeat_start=any(m.get('repeatStart') for m in measures),
                            repeat_count=max(repeats,default=0),endings=list(sorted(endings)[0]) if endings else []))
        offset+=span
    return headers,warnings


def playback_order(headers,limit=10000):
    stack=[];regions={};warnings=[]
    for i,h in enumerate(headers):
        if h['repeat_start']:stack.append(i)
        if h['repeat_count']:
            start=stack.pop() if stack else 0
            regions.setdefault(start,[]).append((i,max(1,h['repeat_count'])))
    if stack:warnings.append('unclosed_repeat_start')
    pc=0;frames=[];order=[];last_pass=1;steps=0
    while pc<len(headers):
        steps+=1
        if steps>limit:return dict(order=order,complete=False,warnings=warnings+['repeat_expansion_limit'])
        if pc in regions:
            # Outer regions enter first; nested repeat starts can share a bar.
            for end,count in sorted(regions[pc],reverse=True):
                if not any(f['start']==pc and f['end']==end for f in frames):frames.append(dict(start=pc,end=end,count=count,iteration=1))
        iteration=frames[-1]['iteration'] if frames else last_pass
        h=headers[pc]
        if not h['endings'] or iteration in h['endings']:order.append(dict(bar=pc+1,pass_number=iteration))
        if frames and frames[-1]['end']==pc:
            frame=frames[-1]
            if frame['iteration']<frame['count']:
                frame['iteration']+=1;pc=frame['start'];continue
            last_pass=frame['iteration'];frames.pop()
        elif not h['endings'] and not frames:last_pass=1
        pc+=1
    return dict(order=order,complete=True,warnings=warnings)


def curve(source,duration_q):
    """Raw tone/25 is quarter-tone units, so semitones are tone/50.

    precisePosition/100 is the observed percent encoding. Coarse position/60
    is retained for comparison, never rounded. Unknown shapes remain flagged.
    """
    points=[];warnings=[]
    for p in (source or {}).get('points',[]):
        if 'tone' not in p or ('position' not in p and 'precisePosition' not in p):
            warnings.append('incomplete_curve_point');continue
        precise=p.get('precisePosition')
        offset=number(precise)/100 if precise is not None else number(p['position'])/60
        if not 0<=offset<=1:warnings.append('curve_offset_out_of_range')
        points.append(dict(offset_fraction=str(offset),semitones=str(number(p['tone'])/50),
                           coarse_fraction=str(number(p['position'])/60) if p.get('position') is not None else None,
                           position_source='precise_percent' if precise is not None else 'coarse_sixtieths',
                           point_vibrato=p.get('vibrato'),raw=p))
    if any(F(b['offset_fraction'])<F(a['offset_fraction']) for a,b in zip(points,points[1:])):warnings.append('nonmonotonic_curve_offsets')
    if not points:return dict(points=[],warnings=warnings+['empty_curve'],valid=False)
    vals=[F(p['semitones']) for p in points];peak=max(vals);duration=F(duration_q)
    slopes=[]
    for a,b in zip(points,points[1:]):
        span=F(b['offset_fraction'])-F(a['offset_fraction']);change=F(b['semitones'])-F(a['semitones'])
        if span==0 and change:warnings.append('instantaneous_pitch_step')
        if span>0 and duration>0:slopes.append(str(change/(span*duration)))
    declared=source.get('tone')
    return dict(points=points,peak_semitones=str(peak),minimum_semitones=str(min(vals)),
                initial_semitones=str(vals[0]),final_semitones=str(vals[-1]),
                excursion_semitones=str(max(vals)-min(vals)),
                declared_peak_agrees=number(declared)/50==peak if declared is not None else None,
                first_peak_fraction=next(p['offset_fraction'] for p in points if F(p['semitones'])==peak),
                slopes_semitones_per_quarter=slopes,point_vibrato_flags=sum(bool(p['point_vibrato']) for p in points),
                warnings=warnings,valid=not any(w in warnings for w in ('incomplete_curve_point','nonmonotonic_curve_offsets','curve_offset_out_of_range')))


def curve_at(shape,fraction):
    if not shape or not shape.get('valid'):return None
    points=shape['points'];q=F(fraction);value=F(points[0]['semitones'])
    for i,p in enumerate(points):
        x=F(p['offset_fraction']);y=F(p['semitones'])
        if q<x:
            if i==0:return y
            a=points[i-1];ax=F(a['offset_fraction']);ay=F(a['semitones'])
            return ay+(y-ay)*(q-ax)/(x-ax)
        value=y
    return value


def rests(part,headers):
    out=[];warnings=[]
    for mi,m in enumerate(part.get('measures',[])):
        h=headers[mi];span=F(h['span_q']);base=F(h['start_q'])
        voices=m.get('voices',[]) or ([dict(rest=True)] if m.get('rest') else [])
        if m.get('rest') and any(not n.get('rest') for v in voices for b in v.get('beats',[]) for n in b.get('notes',[])):
            warnings.append(dict(bar=mi+1,reason='measure_rest_conflicts_with_notes'))
        for vi,v in enumerate(voices):
            beats=v.get('beats',[]);local=F(0)
            if not beats and (v.get('rest') or m.get('rest')):
                out.append(dict(bar=mi+1,voice=vi,onset_q=str(base),duration_q=str(span),source='whole_rest_flag'));continue
            if v.get('rest') and any(not n.get('rest') for b in beats for n in b.get('notes',[])):
                warnings.append(dict(bar=mi+1,voice=vi,reason='voice_rest_conflicts_with_notes'))
            for bi,b in enumerate(beats):
                if b.get('graceNote'):continue
                if not b.get('duration'):break
                written=F(*b['duration'])*4
                d=span if whole_measure_rest(m,v) else written;pitched=any(not n.get('rest') for n in b.get('notes',[]))
                if b.get('rest') and pitched:warnings.append(dict(bar=mi+1,voice=vi,beat=bi,reason='beat_rest_conflicts_with_notes'))
                if not pitched:
                    record=dict(bar=mi+1,voice=vi,onset_q=str(base+local),duration_q=str(d),source='explicit_rest_beat')
                    if whole_measure_rest(m,v):record.update(written_duration_q=str(written),duration_semantics='whole_measure_rest')
                    out.append(record)
                local+=d
    return out,warnings


def mechanics(rows):
    records=[];values=defaultdict(Counter)
    for r in rows:
        n,b=r['raw_note'],r['raw_beat_effects'];record=dict(occurrence=r['occurrence'])
        if n.get('bend'):
            record['bend']=curve(n['bend'],r['duration_q']);shape=record['bend']
            if shape.get('points'):
                for key in ('peak_semitones','excursion_semitones','first_peak_fraction'):
                    values['bend_'+key][shape[key]]+=1
                for slope in shape['slopes_semitones_per_quarter']:values['bend_slope_semitones_per_quarter'][slope]+=1
        if b.get('tremoloBar'):
            record['whammy']=curve(b['tremoloBar'],r['duration_q'])
            if record['whammy'].get('points'):
                for key in ('peak_semitones','minimum_semitones','excursion_semitones'):
                    values['whammy_'+key][record['whammy'][key]]+=1
        trem=n.get('tremolo',b.get('tremolo'))
        if isinstance(trem,list) and len(trem)==2:
            try:
                period=F(*trem)*4
                if period<=0:raise ValueError('nonpositive tremolo period')
                record['tremolo_period_q']=str(period);record['tremolo_attacks_per_quarter']=str(1/period)
                values['tremolo_period_q'][str(period)]+=1
            except (ValueError,ZeroDivisionError):record['tremolo_error']='invalid_fraction'
        brush=b.get('brushStroke')
        if isinstance(brush,dict):
            effective='up' if b.get('upStroke') else brush.get('direction')
            record['brush']=dict(direction=brush.get('direction'),effective_direction=effective,direction_source='upStroke_override' if b.get('upStroke') else 'brushStroke.direction',duration_native=brush.get('duration'),shift_native=brush.get('shift'),time_unit='unverified_native_unit')
            values['brush_effective_direction'][str(effective)]+=1
            for key in ('direction','duration','shift'):values['brush_'+key][str(brush.get(key))]+=1
        if len(record)>1:records.append(record)
    return records,{k:dict(v) for k,v in values.items()}


def timeline(parts,headers):
    tempo={};warnings=[];sounds=[]
    def add(q,event,where):
        if not event.get('bpm'):return
        unit=event.get('type') or 4
        if unit not in (1,2,4,8,16,32,64):warnings.append(dict(reason='unknown_tempo_unit',source=where));return
        bpm=number(event['bpm'])*4/unit
        if bpm<=0:warnings.append(dict(reason='nonpositive_tempo',source=where));return
        point=dict(onset_q=str(q),quarter_bpm=str(bpm),linear=bool(event.get('linear')),source=where)
        if q in tempo and (tempo[q]['quarter_bpm'],tempo[q]['linear'])!=(point['quarter_bpm'],point['linear']):
            warnings.append(dict(reason='conflicting_tempo',onset_q=str(q)))
        else:tempo[q]=point
    for ti,t in enumerate(parts):
        for event in (t.get('automations') or {}).get('tempo',[]):
            mi=int(event.get('measure',0))
            if not 0<=mi<len(headers):warnings.append(dict(reason='tempo_outside_score'));continue
            q=F(headers[mi]['start_q'])+number(event.get('position') or 0)*4
            add(q,event,'automation')
        for mi,m in enumerate(t.get('measures',[])):
            local=F(0)
            for v in m.get('voices',[]):
                local=F(0)
                for b in v.get('beats',[]):
                    if b.get('tempo'):add(F(headers[mi]['start_q'])+local,b['tempo'],'beat')
                    if b.get('duration') and not b.get('graceNote'):local+=F(*b['duration'])*4
        catalog=t.get('sounds') or []
        for event in (t.get('trackAutomations') or {}).get('trackSoundAutomations',[]):
            mi=int(event.get('measure',0));sid=int(event.get('soundId',-1))
            if not 0<=mi<len(headers) or not 0<=sid<len(catalog):warnings.append(dict(reason='invalid_sound_change',track=ti));continue
            sounds.append(dict(track=ti,onset_q=str(F(headers[mi]['start_q'])+number(event.get('position') or 0)/960),
                               sound_id=sid,program=catalog[sid].get('instrumentId'),label=catalog[sid].get('label')))
    return dict(tempo=sorted(tempo.values(),key=lambda x:F(x['onset_q'])),sound_changes=sounds,warnings=warnings,
                units=dict(tempo_position='whole_note_fraction',sound_position='960_ticks_per_quarter'),
                linear_ramp_status='unresolved_source_convention' if any(e['linear'] for e in tempo.values()) else 'no_linear_ramps')


def seconds_between(start,end,time):
    start,end=F(start),F(end);points=time['tempo']
    if not points or time['warnings'] or any(p['linear'] for p in points):return None
    if start<F(points[0]['onset_q']) or end<start:return None
    seconds=F(0)
    for i,p in enumerate(points):
        a=max(start,F(p['onset_q']));b=min(end,F(points[i+1]['onset_q']) if i+1<len(points) else end)
        if b>a:seconds+=(b-a)*60/F(p['quarter_bpm'])
    return float(seconds)


def unpitched_tie_continuity(rows):
    """Explicit dead-note notation links, separate from pitched/sounding chains.

    Exact time, lane and fret equality establish written continuity only. Neither
    a sounding pitch nor an acoustic duration is assigned to a muted gesture.
    """
    lanes=defaultdict(list);links=[];unresolved=[];chains=[];chain_by_end={}
    for r in rows:
        string=r.get('string')
        if isinstance(string,int) and not isinstance(string,bool) and string>=0:
            lanes[r['voice'],string].append(r)
        elif r.get('tie_destination') and r.get('midi') is None:
            unresolved.append(dict(occurrence=r['occurrence'],reason='invalid_or_missing_string'))
    for lane in lanes.values():
        groups=defaultdict(list)
        for r in lane:groups[F(r['onset_q'])].append(r)
        previous=None
        for q,group in sorted(groups.items()):
            if len(group)!=1:
                for r in group:
                    if r.get('tie_destination') and r.get('midi') is None:unresolved.append(dict(occurrence=r['occurrence'],reason='ambiguous_same_lane_onset'))
                previous=None;continue
            r=group[0];dead='dead' in r.get('effects',[]) and r.get('raw_note',{}).get('dead') is True
            if r.get('tie_destination') and (r.get('midi') is None or (previous and previous.get('midi') is None)):
                prior_dead=previous is not None and 'dead' in previous.get('effects',[]) and previous.get('raw_note',{}).get('dead') is True
                fret=r.get('fret');valid_fret=isinstance(fret,(int,float)) and not isinstance(fret,bool) and 0<=fret<float('inf')
                match=(previous is not None and F(previous['onset_q'])+F(previous['duration_q'])==q
                       and previous.get('fret')==fret and valid_fret and dead and prior_dead
                       and r.get('midi') is None and previous.get('midi') is None and F(r['duration_q'])>0)
                if match:
                    link=dict(origin=previous['occurrence'],destination=r['occurrence'],kind='explicit_dead_tie_notation',sounding_pitch=None)
                    links.append(link)
                    chain=chain_by_end.pop(previous['occurrence'],None)
                    if chain is None:
                        chain=dict(origin=previous['occurrence'],members=[previous['occurrence']],onset_q=previous['onset_q'],
                                   voice=r['voice'],string=r['string'],fret=fret,sounding_pitch=None,
                                   origin_is_tie_destination=bool(previous.get('tie_destination')))
                        chains.append(chain)
                    chain['members'].append(r['occurrence']);chain['written_end_q']=str(q+F(r['duration_q']))
                    chain_by_end[r['occurrence']]=chain
                else:
                    reason=('dead_to_pitched' if prior_dead and r.get('midi') is not None else
                            'pitched_to_dead' if dead and previous and previous.get('midi') is not None else
                            'unknown_pitch_without_explicit_dead' if not dead or not prior_dead else 'noncontiguous_or_different_fret')
                    unresolved.append(dict(occurrence=r['occurrence'],reason=reason))
            previous=r
    return dict(schema='source-unpitched-tie-notation-v1',links=links,chains=chains,unresolved=unresolved,
                limitation='Written dead-note continuity only; no pitched sustain, sounding duration or invented frequency')


def sustain_context(rows,mechanical):
    by_id={m['occurrence']:m for m in mechanical};lanes=defaultdict(list);chains=[];warnings=[]
    for r in rows:
        if r['string'] is not None:lanes[r['voice'],r['string']].append(r)
    for lane in lanes.values():
        previous=None
        for r in sorted(lane,key=lambda x:(F(x['onset_q']),x['occurrence'])):
            q=F(r['onset_q']);end=q+F(r['duration_q'])
            matches=previous is not None and F(previous['end_q'])==q and previous['midi']==r['midi'] and previous['fret']==r['fret'] and r['midi'] is not None
            if r['tie_destination'] and matches:
                previous['end_q']=str(end);previous['members'].append(r['occurrence']);continue
            if r['tie_destination']:warnings.append(dict(occurrence=r['occurrence'],reason='unresolved_tied_destination'))
            previous=dict(origin=r['occurrence'],members=[r['occurrence']],onset_q=str(q),end_q=str(end),midi=r['midi'],fret=r['fret'],string=r['string'],voice=r['voice'],orphan_tie=r['tie_destination'])
            chains.append(previous)
    events=sorted(chains,key=lambda c:F(c['onset_q']));live=[];contexts=[]
    row_lookup={r['occurrence']:r for r in rows}
    def center_pitch(c,q):
        if c['midi'] is None:return None
        carried=F(0)
        for ident in c['members']:
            segment=row_lookup[ident];sq=F(segment['onset_q']);duration=F(segment['duration_q'])
            if sq>q:break
            effects=segment['effects']
            if any(k in effects for k in ('harmonic','vibrato','wideVibrato','leftHandVibrato')):return None
            shape=by_id.get(ident,{}).get('bend')
            if shape:
                if any(p['point_vibrato'] for p in shape['points']):return None
                carried=curve_at(shape,min(F(1),(q-sq)/duration))
                if carried is None:return None
            whammy=by_id.get(ident,{}).get('whammy')
            extra=curve_at(whammy,min(F(1),(q-sq)/duration)) if whammy else F(0)
            if extra is None:return None
            if sq+duration>q:return F(c['midi'])+carried+extra
        return F(c['midi'])+carried
    for c in events:
        q=F(c['onset_q']);live=[p for p in live if F(p['end_q'])>q]
        r=row_lookup[c['origin']]
        held=[p for p in live if F(p['onset_q'])<q]
        if r['effects']:
            neighbors=[]
            for p in held:
                a,b=center_pitch(p,q),center_pitch(c,q)
                neighbors.append(dict(origin=p['origin'],written_interval_from_target=p['midi']-c['midi'] if p['midi'] is not None and c['midi'] is not None else None,
                                      notated_center_interval_from_target=str(a-b) if a is not None and b is not None else None,
                                      unresolved_reason='unknown_pitch_harmonic_or_vibrato' if a is None or b is None else None))
            contexts.append(dict(occurrence=c['origin'],effects=r['effects'],sustain_duration_q=str(F(c['end_q'])-q),
                                 held_neighbors=neighbors,
                                 tie_members=len(c['members'])))
        live.append(c)
    return dict(chains=chains,technique_contexts=contexts,warnings=warnings,
                held_neighbor_contexts=sum(bool(c['held_neighbors']) for c in contexts),
                limitations=['Notated pitch centers with linear curve interpolation, not performed sound; harmonics/vibrato remain unresolved','Let-ring beyond written duration is not guessed'])
