"""Repeatable GP technique/pattern observations. No AI labels or model inference."""
from collections import Counter,defaultdict
from fractions import Fraction as F
import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from exact_score import extract_score,validate_events
from bend_analysis import tie_chains


def enabled(xml,name):
    p=ET.fromstring(xml).find(f"./Properties/Property[@name='{name}']")
    return p is not None and p.find('Enable') is not None


def classify_group(rows):
    """Nonexclusive written-pitch labels; no inferred chord roots or function."""
    if len(rows)<2 or any(r['midi'] is None or r['string'] is None for r in rows):return []
    if len({r['string'] for r in rows})!=len(rows):return []
    pitches=sorted(r['midi'] for r in rows);root=pitches[0];pcs={p%12 for p in pitches}
    core={root%12,(root+7)%12};labels=[]
    if len(rows)==2:
        labels.append('double_stop')
        if pitches[1]-pitches[0] in (1,2):labels.append('close_interval_texture')
    if pcs==core:labels.append('power_chord')
    elif core<=pcs and len(pcs-core)==1:labels.append('extended_power_chord')
    return labels


def hopo_pairs(rows):
    lanes=defaultdict(list);observed=[];eligible=[];warnings=[];matched_dest=set()
    for r in rows:
        if r['string'] is not None:lanes[r['voice'],r['string']].append(r)
    for lane in lanes.values():
        lane.sort(key=lambda r:(F(r['onset_q']),r['order']))
        for i,a in enumerate(lane):
            if a['tie_destination']:continue
            # Follow explicit same-string ties before looking for the next attack.
            j=i;end=F(a['onset_q'])+F(a['duration_q'])
            while j+1<len(lane) and lane[j]['tie_origin'] and lane[j+1]['tie_destination'] and F(lane[j+1]['onset_q'])==end and lane[j]['midi']==lane[j+1]['midi'] and lane[j]['fret']==lane[j+1]['fret']:
                j+=1;end+=F(lane[j]['duration_q'])
            b=lane[j+1] if j+1<len(lane) else None
            reason=None
            if b is None:reason='no_next_same_string_note'
            elif F(b['onset_q'])!=end:reason='gap_or_overlap'
            elif b['tie_destination']:reason='unresolved_tied_destination'
            elif a['fret'] is None or b['fret'] is None:reason='missing_fret'
            elif a['fret']==b['fret']:reason='same_fret'
            origins=[r for r in lane[i:j+1] if r['hopo_origin']]
            if reason:
                for r in origins:warnings.append(dict(origin=r['occurrence'],reason=reason))
                continue
            direction='hammer_on' if b['fret']>a['fret'] else 'pull_off'
            open_kind='from_open' if a['fret']==0 else 'to_open' if b['fret']==0 else 'fretted'
            record=dict(origin=a['occurrence'],destination=b['occurrence'],direction=direction,
                        context=open_kind,fret_distance=abs(b['fret']-a['fret']),
                        origin_fret=a['fret'],destination_fret=b['fret'],string=a['string'],
                        source_bar=a['bar'],destination_bar=b['bar'],
                        annotation_status='paired_markers' if origins and b['hopo_destination'] else 'eligibility_only',
                        origin_markers=[r['occurrence'] for r in origins])
            eligible.append(record)
            if origins and b['hopo_destination']:observed.append(record);matched_dest.add(b['occurrence'])
            elif origins:
                warnings.append(dict(origin=origins[0]['occurrence'],reason='destination_marker_missing'))
    for r in rows:
        if r['hopo_destination'] and r['occurrence'] not in matched_dest:warnings.append(dict(destination=r['occurrence'],reason='unmatched_destination_marker'))
    return observed,eligible,warnings


def pedal_runs(sustains):
    """Exact alternating-return evidence, not a claim of phrase or musical purpose."""
    lanes=defaultdict(list);out=[]
    for s in sustains:lanes[s['voice']].append(s)
    for voice,lane in lanes.items():
        lane.sort(key=lambda n:(F(n['onset_q']),n['occurrence']))
        # Exclude simultaneous events: no arbitrary highest-note melody projection.
        times=Counter(n['onset_q'] for n in lane)
        for i in range(len(lane)-5):
            group=lane[i:i+6]
            if any(times[n['onset_q']]!=1 or n['midi'] is None for n in group):continue
            if any(F(b['onset_q'])<F(a['onset_q'])+F(a['duration_q']) for a,b in zip(group,group[1:])):continue
            ps=[n['midi'] for n in group];anchor=ps[0]
            if ps[::2]!=[anchor]*3 or any(p==anchor for p in ps[1::2]):continue
            if sum(p>=anchor for p in ps[1::2])<2:continue
            offsets=[str(F(n['onset_q'])-F(group[0]['onset_q'])) for n in group]
            out.append(dict(voice=voice,anchor_midi=anchor,members=[n['occurrence'] for n in group],
                            contrast_intervals=[p-anchor for p in ps[1::2]],onset_offsets_q=offsets,
                            durations_q=[n['duration_q'] for n in group],
                            source_bar=group[0]['bar'],section=group[0]['section'],
                            interpretation='six-event alternating-return candidate; overlapping windows, not phrase truth'))
    signatures=defaultdict(list)
    for i,r in enumerate(out):
        key=(tuple(r['contrast_intervals']),tuple(r['onset_offsets_q']),tuple(r['durations_q']))
        signatures[key].append(i)
    return out,[v for v in signatures.values() if len(v)>1]


def effect_inventory(xml):
    root=ET.fromstring(xml);result=[]
    for p in root.findall('./Properties/Property'):
        name=p.get('name','')
        if any(s in name.lower() for s in ('vibra','trem','trill','whammy','pickstroke')):
            result.append(dict(name=name,xml=ET.tostring(p,encoding='unicode')))
    for child in root:
        if any(s in child.tag.lower() for s in ('vibra','trem','trill','whammy')):
            result.append(dict(name=child.tag,xml=ET.tostring(child,encoding='unicode')))
    return result


def analyze(score):
    tracks=[]
    for t in score['tracks']:
        rows=[];effects=[];section='(unlabeled)';order=0;inventory=defaultdict(Counter)
        for m in t['measures']:
            if m['section']:section=m['section']
            for vi,v in enumerate(m['voices']):
                for ei,e in enumerate(v):
                    beat_root=ET.fromstring(e['beat_xml'])
                    inventory['beat_properties'].update(p.get('name') for p in beat_root.findall('./Properties/Property'))
                    inventory['beat_tags'].update(c.tag for c in beat_root if c.tag not in ('Notes','Rhythm','Properties'))
                    for effect in effect_inventory(e['beat_xml']):effects.append(dict(scope='beat',bar=m['number'],voice=vi,beat=e['beat_id'],**effect))
                    for ni,n in enumerate(e['notes']):
                        inventory['note_properties'].update(n['property_names'])
                        inventory['note_tags'].update(n['technique_tags'])
                        tie=n['tie'] or {};order+=1
                        r=dict(occurrence=f"{t['index']}:{m['number']}:{vi}:{ei}:{ni}",order=order,
                               note_id=n['note_id'],bar=m['number'],section=section,voice=vi,
                               onset_q=n['onset_q'],duration_q=n['duration_q'],midi=n['midi'],
                               string=n['string'],fret=n['fret'],tie_destination=tie.get('destination')=='true',
                               tie_origin=tie.get('origin')=='true',hopo_origin=enabled(n['note_xml'],'HopoOrigin'),
                               hopo_destination=enabled(n['note_xml'],'HopoDestination'),
                               pitch_effects=any(x in n['property_names'] for x in ('Bended','HarmonicType')) or any(s in e['beat_xml'] for s in ('Whammy','Vibrato')),
                               grace_type=n['grace_type'])
                        rows.append(r)
                        for effect in effect_inventory(n['note_xml']):effects.append(dict(scope='note',occurrence=r['occurrence'],**effect))
        observed,eligible,warnings=hopo_pairs(rows)
        chains,unresolved,dangling=tie_chains(rows)
        sustains=[]
        for c in chains:
            if c[0]['tie_destination']:continue
            sustains.append(dict(c[0],duration_q=str(sum((F(r['duration_q']) for r in c),F(0))),
                                 pitch_effects=any(r['pitch_effects'] for r in c),members=[r['occurrence'] for r in c]))
        groups=[];hist=Counter();starts=defaultdict(list);live={};boundaries=set()
        for r in sustains:
            if F(r['duration_q'])>0:
                q=F(r['onset_q']);starts[q].append(r);boundaries.update((q,q+F(r['duration_q'])))
        boundaries=sorted(boundaries)
        for qi,q in enumerate(boundaries[:-1]):
            live={ident:(r,end) for ident,(r,end) in live.items() if end>q}
            for r in starts[q]:live[r['occurrence']]=(r,q+F(r['duration_q']))
            active=[r for r,end in live.values()]
            labels=classify_group(active) if not t['is_percussion'] else []
            if labels:
                coattack=all(F(r['onset_q'])==q for r in active)
                groups.append(dict(onset_q=str(q),end_q=str(boundaries[qi+1]),labels=labels,coattack=coattack,
                                   requires_pitch_effect_resolution=any(r['pitch_effects'] for r in active),
                                   members=[r['occurrence'] for r in active]))
                hist.update(labels)
        pedal,recurrences=pedal_runs(sustains)
        section_counts=defaultdict(Counter)
        by_occurrence={r['occurrence']:r for r in rows}
        for p in observed:section_counts[by_occurrence[p['origin']]['section']].update([p['direction']+'_'+p['context']])
        direction_counts=Counter(r['direction']+'_'+r['context'] for r in observed)
        transition_count=len(eligible)
        tracks.append(dict(index=t['index'],name=t['name'],program=t['program'],is_percussion=t['is_percussion'],
                           technique_scope='guitar_or_bass' if t['program'] is not None and 24<=t['program']<=39 else 'source_notation_only',
                           occurrence_count=len(rows),attack_count=sum(not r['tie_destination'] for r in rows),
                           hopo_origin_markers=sum(r['hopo_origin'] for r in rows),hopo_destination_markers=sum(r['hopo_destination'] for r in rows),
                           explicit_hopo=observed,eligible_transitions=eligible,hopo_warnings=warnings,
                           hopo_counts=dict(direction_counts),hopo_counts_by_source_section={k:dict(v) for k,v in section_counts.items()},
                           marked_hopo_share_of_eligible_transitions=dict(numerator=len(observed),denominator=transition_count,percent=100*len(observed)/transition_count if transition_count else None),
                           raw_occurrence_inventory={k:dict(v) for k,v in inventory.items()},
                           effects=effects,effect_counts=dict(Counter(e['scope']+':'+e['name'] for e in effects)),
                           simultaneous_groups=groups,group_label_counts=dict(hist),
                           pedal_candidates=pedal,pedal_recurrence_groups=recurrences,
                           unresolved_ties=unresolved,unmatched_tie_origins=dangling))
    return dict(schema='gp-technique-analysis-v1',source_sha256=score['source_sha256'],source_file=score['source_file'],
                measure_count=score['measure_count'],voice_meter_discrepancies=len(validate_events(score)),tracks=tracks,
                limitations=['Written score order, repeats not unfolded','HOPO eligibility does not prove use or physical feasibility',
                             'Double-stop/tremolo scope definitions remain provisional pending user reply',
                             'Simultaneous labels use notated base MIDI pitches, not bend/harmonic-adjusted audio',
                             'Effect XML preserved; marker absence and unspecified speed/width remain unknown',
                             'Pedal candidates use three alternating returns, not validated musical-role/phrase inference',
                             'Group counts are exact constant-membership intervals within tracks, across voices; cross-track ensemble dyads separate',
                             'No technique playback or musical quality claim'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=analyze(extract_score(a.source));a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print(json.dumps(dict(source=r['source_file'],tracks=len(r['tracks']),hopo=sum(len(t['explicit_hopo']) for t in r['tracks']),warnings=sum(len(t['hopo_warnings']) for t in r['tracks']))))
