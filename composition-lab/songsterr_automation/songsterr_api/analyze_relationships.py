"""Deterministic source observations and conditional summaries; no learned labels.

Raw occurrence reports are private. --aggregate writes counts only for publication.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from technique_analysis import classify_group
from pedal_patterns import detect_bursts

NOTE_FIELDS = ('hp', 'bend', 'slide', 'harmonic', 'dead', 'ghost', 'staccato',
               'accentuated', 'tremolo', 'vibrato', 'wideVibrato', 'leftHandVibrato')
BEAT_FIELDS = ('palmMute', 'tapping', 'letRing', 'brushStroke', 'upStroke',
               'pickStroke', 'fadeIn', 'tremoloBar', 'vibrato', 'wideVibrato',
               'leftHandVibrato', 'tremolo', 'harmonic', 'gradualVelocity')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def family(meta):
    # A leakage precaution, NOT an assertion that these are the same composition.
    title = re.sub(r'\([^)]*\)|\[[^]]*\]', '', meta.get('title', '').casefold())
    title = re.sub(r'\b(?:ver(?:sion)?\.?\s*\d+|official|tab)\b', '', title)
    title = re.sub(r'\W+', ' ', title).strip()
    return meta.get('artist', '').casefold().strip() + ':' + title


def ratio(n, d):
    return dict(numerator=n, denominator=d, percent=100*n/d if d else None)


def pitch(part, n):
    tuning = part.get('tuning') or []
    s, f = n.get('string'), n.get('fret')
    if n.get('dead') or not isinstance(s, int) or not isinstance(f, (int, float)) or not 0 <= s < len(tuning):
        return None
    return tuning[s] + f + (part.get('capo') or 0)


def occurrences(part):
    rows, grace, warnings, sections = [], [], [], []
    offset, signature, section = F(0), [4, 4], None
    for mi, measure in enumerate(part.get('measures', []), 1):
        signature = measure.get('signature') or signature
        span = F(4*signature[0], signature[1])
        if section is None or measure.get('marker'):
            section = dict(id=mi, label=measure.get('marker') or '(unannotated)', start_q=str(offset))
            sections.append(section)
        for vi, voice in enumerate(measure.get('voices', [])):
            local = F(0)
            for bi, beat in enumerate(voice.get('beats', [])):
                raw_duration = beat.get('duration')
                if not raw_duration:
                    warnings.append(dict(bar=mi, voice=vi, beat=bi, reason='missing_duration'))
                    # Subsequent onsets in this voice cannot be known.
                    break
                duration = F(*raw_duration)*4
                if duration <= 0:
                    warnings.append(dict(bar=mi, voice=vi, beat=bi, reason='nonpositive_duration'))
                    break
                for ni, note in enumerate(beat.get('notes', [])):
                    if note.get('rest'):
                        continue
                    effects = set(k for k in NOTE_FIELDS if note.get(k))
                    effects.update(k for k in BEAT_FIELDS if beat.get(k))
                    row = dict(occurrence=f'{part.get("partId", 0)}:{mi}:{vi}:{bi}:{ni}',
                               bar=mi, voice=vi, beat=bi, note=ni, section=section['label'],
                               section_start=section['id'], onset_q=str(offset+local),
                               duration_q=str(duration), bar_offset_q=str(local),
                               bar_span_q=str(span), string=note.get('string'), fret=note.get('fret'),
                               midi=pitch(part, note), tie_destination=bool(note.get('tie')),
                               effects=sorted(effects), raw_note=note, raw_beat_effects={k:v for k,v in beat.items() if k!='notes'},
                               pitch_effects=bool(note.get('bend') or note.get('harmonic') or beat.get('tremoloBar')))
                    (grace if beat.get('graceNote') else rows).append(row)
                if not beat.get('graceNote'):
                    local += duration
            if local > span:
                warnings.append(dict(bar=mi, voice=vi, reason='voice_overflows_bar', duration_q=str(local), span_q=str(span)))
        offset += span
    for i, section in enumerate(sections):
        section['end_q'] = sections[i+1]['start_q'] if i+1<len(sections) else str(offset)
    return rows, grace, sections, warnings


def summary(rows):
    """Marker shares use written segments; attacks have a distinct denominator."""
    counts, conditional, joints = Counter(), {}, Counter()
    pitches = [r['midi'] for r in rows if r['midi'] is not None]
    low, high = (min(pitches), max(pitches)) if pitches else (None, None)
    for r in rows:
        counts.update(r['effects'])
        for i, left in enumerate(r['effects']):
            for right in r['effects'][i+1:]:joints[left+'+'+right]+=1
    for effect in sorted(counts):
        views = {}
        for label, subset in [('marked', [r for r in rows if effect in r['effects']]),
                              ('unmarked', [r for r in rows if effect not in r['effects']])]:
            durations = Counter(r['duration_q'] for r in subset)
            positions = Counter('bar_start' if F(r['bar_offset_q'])==0 else 'inside_bar' for r in subset)
            registers = Counter('unknown' if r['midi'] is None or high==low else
                                'lower_third' if 3*(r['midi']-low)<high-low else
                                'upper_third' if 3*(r['midi']-low)>2*(high-low) else 'middle_third' for r in subset)
            next_intervals = Counter(str(r.get('next_monophonic_interval', 'unknown')) for r in subset)
            other_markers=Counter(k for r in subset for k in r['effects'] if k!=effect)
            views[label] = dict(note_segments=len(subset), duration_q_histogram=dict(durations),
                                mean_written_duration_q=str(sum((F(r['duration_q']) for r in subset),F(0))/len(subset)) if subset else None,
                                bar_positions=dict(positions), relative_written_register=dict(registers),
                                next_same_voice_monophonic_interval=dict(next_intervals),
                                fret_histogram=dict(Counter(str(r['fret']) for r in subset)),
                                string_index_histogram=dict(Counter(str(r['string']) for r in subset)),
                                other_marker_shares={k:ratio(n,len(subset)) for k,n in other_markers.items()})
        conditional[effect] = views
    values=defaultdict(Counter)
    for r in rows:
        n=r['raw_note'];b=r['raw_beat_effects']
        for field in ('slide','harmonic','harmonicFret','accentuated'):
            if n.get(field) is not None:values[field][json.dumps(n[field],sort_keys=True)]+=1
        velocity=n.get('velocity',b.get('velocity'))
        if velocity is not None:values['explicit_velocity'][str(velocity)]+=1
        bend=n.get('bend')
        if isinstance(bend,dict) and bend.get('points'):
            points=bend['points']
            if all('tone' in p and 'position' in p for p in points):
                peak=max(p['tone'] for p in points)
                values['bend_peak_semitones'][str(F(str(peak))/25)]+=1
                values['bend_initial_semitones'][str(F(str(points[0]['tone']))/25)]+=1
                values['bend_final_semitones'][str(F(str(points[-1]['tone']))/25)]+=1
                first_peak=next(p['position'] for p in points if p['tone']==peak)
                values['bend_first_peak_fraction_of_written_segment'][str(F(str(first_peak))/60)]+=1
    return dict(note_segments=len(rows), attacks=sum(not r['tie_destination'] for r in rows),
                unknown_written_pitch=sum(r['midi'] is None for r in rows),
                marker_shares={k:ratio(v,len(rows)) for k,v in sorted(counts.items())},
                marker_pairs=dict(sorted(joints.items())), marker_value_histograms={k:dict(v) for k,v in values.items()},conditional=conditional)


def hopo(rows, grace):
    """Interpret source hp as an origin marker (upstream GP hammer convention).

    This is a notation-backed transition candidate, not a listening verdict.
    Grace notes, ties with changed pitch and gaps must not create false pairs.
    """
    lanes = defaultdict(list)
    for r in rows:
        if r['string'] is not None:
            lanes[r['voice'], r['string']].append(r)
    out, unresolved = [], []
    grace_times = {(r['voice'],r['string'],r['onset_q']) for r in grace}
    for lane in lanes.values():
        lane.sort(key=lambda r:(F(r['onset_q']),r['occurrence']))
        for i, a in enumerate(lane):
            if 'hp' not in a['effects']:
                continue
            j=i; end=F(a['onset_q'])+F(a['duration_q'])
            while j+1<len(lane) and lane[j+1]['tie_destination'] and F(lane[j+1]['onset_q'])==end and lane[j+1]['midi']==a['midi'] and lane[j+1]['fret']==a['fret']:
                j+=1;end+=F(lane[j]['duration_q'])
            b=lane[j+1] if j+1<len(lane) else None
            reason = 'no_next_same_string_note' if b is None else (
                'gap_or_overlap' if F(b['onset_q'])!=end else
                'unresolved_tie' if b['tie_destination'] else
                'unknown_pitch' if a['midi'] is None or b['midi'] is None else
                'same_fret' if a['fret']==b['fret'] else
                'grace_at_transition' if (b['voice'],b['string'],b['onset_q']) in grace_times else None)
            if reason:
                unresolved.append(dict(origin=a['occurrence'],reason=reason));continue
            out.append(dict(origin=a['occurrence'],destination=b['occurrence'],
                            direction='hammer_on' if b['fret']>a['fret'] else 'pull_off',
                            context='from_open' if a['fret']==0 else 'to_open' if b['fret']==0 else 'fretted',
                            fret_distance=abs(b['fret']-a['fret']),bar=a['bar'],section_start=a['section_start'],
                            crossed_section=a['section_start']!=b['section_start'],interpretation='source-hp-origin contiguous-transition candidate'))
    return out, unresolved


def track_analysis(part):
    rows, grace, sections, warnings = occurrences(part)
    temporal_valid = not warnings
    lanes = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if temporal_valid and not r['tie_destination']:
            lanes[r['voice']][F(r['onset_q'])].append(r)
    for lane in lanes.values():
        starts = sorted(lane)
        for q, nq in zip(starts, starts[1:]):
            a, b = lane[q], lane[nq]
            if len(a)==len(b)==1 and a[0]['midi'] is not None and b[0]['midi'] is not None and a[0]['section_start']==b[0]['section_start']:
                a[0]['next_monophonic_interval']=b[0]['midi']-a[0]['midi']
                a[0]['next_attack_gap_q']=str(nq-q)
    guitar = isinstance(part.get('instrumentId'),int) and 24<=part['instrumentId']<=39
    groups, attacks = [], defaultdict(list)
    if guitar and temporal_valid:
        for r in rows:
            if not r['tie_destination']:
                attacks[F(r['onset_q'])].append(r)
        for q, active in sorted(attacks.items()):
            labels=classify_group(active)
            if labels:
                groups.append(dict(onset_q=str(q),members=[r['occurrence'] for r in active],labels=labels,
                                   pitch_effects_unresolved=any(r['pitch_effects'] for r in active)))
    pairs, unresolved = hopo(rows, grace) if guitar and temporal_valid else ([],[])
    # Pedal detector operates on attacks across voices within a track.
    pedals = detect_bursts(rows) if guitar and temporal_valid else []
    by_section = []
    for s in sections:
        subset=[r for r in rows if r['section_start']==s['id']]
        end=F(s['end_q']);start=F(s['start_q'])
        data=summary(subset)
        data['technique_section_quartiles']={k:dict(Counter(min(3,int(4*(F(r['onset_q'])-start)/(end-start))) for r in subset if k in r['effects'])) for k in data['marker_shares']} if end>start else {}
        by_section.append(dict(**s,summary=data))
    examples=defaultdict(list)
    for r in rows:
        for k in r['effects']:
            if len(examples[k])<4:examples[k].append(r['occurrence'])
    # Preserve near-misses as explicit counterexamples, not merely positive snippets.
    near=[]
    for q, active in sorted(attacks.items()):
        if len(active)==2 and len({r['string'] for r in active})==2 and all(r['midi'] is not None for r in active):
            distance=abs(active[0]['midi']-active[1]['midi'])
            if distance==2 and len(near)<4:near.append(dict(members=[r['occurrence'] for r in active],written_semitones=distance,reason='whole_step_not_close_texture'))
    return dict(part_id=part.get('partId'),name=part.get('name'),guitar_or_bass=guitar,
                temporal_relationships_eligible=temporal_valid,
                summary=summary(rows),sections=by_section,rows=rows,grace_rows=grace,timing_warnings=warnings,
                coattack_groups=groups,hopo_transition_candidates=pairs,unresolved_hp=unresolved,
                pedal_candidates=pedals,examples=dict(examples),counterexamples=near)


def analyze(root, progress=False):
    songs=[];families=defaultdict(list);contents=defaultdict(list)
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or not (folder/'metadata.json').exists():continue
        meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8-sig'))
        if progress:print(f"Analyzing entry {len(songs)+1}: {meta['songId']}",flush=True)
        parts=[json.loads(p.read_text(encoding='utf-8-sig')) for p in sorted(folder.glob('track-*.json'))]
        # Exact representation duplicate only; no fuzzy musical-equivalence claim.
        content=digest([{k:p[k] for k in ('measures','tuning','capo','instrumentId','automations','sounds','trackAutomations') if k in p} for p in parts])
        key=family(meta);sid=meta['songId'];families[key].append(sid);contents[content].append(sid)
        tracks=[track_analysis(p) for p in parts]
        rows=[r for t in tracks if t['guitar_or_bass'] for r in t['rows']]
        songs.append(dict(song_id=sid,revision_id=meta['revisionId'],artist=meta.get('artist'),title=meta.get('title'),
                          ai_generated=meta.get('aiGenerated'),is_junk=meta.get('isJunk'),
                          candidate_work_family=key,provisional_partition='held_out' if int(digest(key)[:8],16)%5==0 else 'development',
                          notation_hash=content,tracks=tracks,summary=summary(rows)))
    # Keep both known exact duplicates and candidate title families in one split.
    parent={s['song_id']:s['song_id'] for s in songs}
    def find(sid):
        while parent[sid]!=sid:
            parent[sid]=parent[parent[sid]];sid=parent[sid]
        return sid
    for members in list(families.values())+list(contents.values()):
        for sid in members[1:]:parent[find(sid)]=find(members[0])
    components=defaultdict(list)
    for s in songs:components[find(s['song_id'])].append(s['song_id'])
    for s in songs:
        component=sorted(components[find(s['song_id'])])
        s['provisional_partition']='held_out' if int(digest(component)[:8],16)%5==0 else 'development'
    cohort_rows=defaultdict(list);artist_rows=defaultdict(list)
    for s in songs:
        rows=[r for t in s['tracks'] if t['guitar_or_bass'] for r in t['rows']]
        cohort_rows['all_entries'].extend(rows)
        if s['ai_generated'] is False and s['is_junk'] is False:cohort_rows['neither_ai_nor_junk_flagged'].extend(rows)
        if s['ai_generated'] is True:cohort_rows['ai_flagged'].extend(rows)
        if s['is_junk'] is True:cohort_rows['junk_flagged'].extend(rows)
        artist_rows[s['artist']].extend(rows)
    return dict(schema='songsterr-relational-observations-v1',songs=songs,
                candidate_family_groups=[v for v in families.values() if len(v)>1],
                exact_notation_duplicate_groups=[v for v in contents.values() if len(v)>1],
                cohorts={k:summary(v) for k,v in cohort_rows.items()},
                artists={k:summary(v) for k,v in artist_rows.items()},
                limitations=['Written score-order occurrences, not expanded repeat playback or recorded performance',
                             'Candidate title families require adjudication; provisional partitions are not validated held-out evaluation',
                             'hp-origin interpretation follows upstream GP convention, not independent technique ground truth',
                             'Coattacks combine voices; sustained sonorities and bend-adjusted sounding intervals are not classified',
                             'Technique percentages use regular written note segments, not distinct sustained gestures',
                             'Tracks with malformed or overflowing written timing retain notation counts but are excluded from temporal relationship candidates',
                             'Marker absence is not observed performance absence; no phrase, intent, chord-function or feel labels'])


def aggregate(report):
    songs=report['songs'];tracks=[t for s in songs for t in s['tracks']];guitars=[t for t in tracks if t['guitar_or_bass']]
    grouped=Counter(label for t in guitars for g in t['coattack_groups'] for label in g['labels'])
    pairs=Counter(p['direction']+'_'+p['context'] for t in guitars for p in t['hopo_transition_candidates'])
    effects=Counter(k for s in songs for k in s['summary']['marker_shares'])
    distributions={}
    for effect in effects:
        rates=[];family_rates=defaultdict(list)
        for s in songs:
            den=s['summary']['note_segments']
            if not den:continue
            rate=s['summary']['marker_shares'].get(effect,{}).get('numerator',0)/den*100
            rates.append(rate);family_rates[s['candidate_work_family']].append(rate)
        distributions[effect]=dict(entries_with_guitar_notes=len(rates),song_mean_percent=sum(rates)/len(rates) if rates else None,
                                  minimum_song_percent=min(rates) if rates else None,maximum_song_percent=max(rates) if rates else None,
                                  candidate_family_balanced_mean_percent=sum(sum(v)/len(v) for v in family_rates.values())/len(family_rates) if family_rates else None)
    return dict(schema=report['schema'],entries=len(songs),tracks=len(tracks),guitar_bass_tracks=len(guitars),
                ai_flagged=sum(s['ai_generated'] is True for s in songs),junk_flagged=sum(s['is_junk'] is True for s in songs),
                candidate_family_group_sizes=[len(g) for g in report['candidate_family_groups']],
                exact_notation_duplicate_group_sizes=[len(g) for g in report['exact_notation_duplicate_groups']],
                timing_warnings=dict(Counter(w['reason'] for t in tracks for w in t['timing_warnings'])),
                temporal_relationship_excluded_tracks=sum(not t['temporal_relationships_eligible'] for t in tracks),
                temporal_relationship_excluded_guitar_tracks=sum(not t['temporal_relationships_eligible'] for t in guitars),
                cohorts=report['cohorts'],entries_with_marker={k:ratio(n,len(songs)) for k,n in effects.items()},coattack_group_labels=dict(grouped),
                across_entry_distributions=distributions,
                hopo_transition_candidates=dict(pairs),unresolved_hp=dict(Counter(w['reason'] for t in guitars for w in t['unresolved_hp'])),
                pedal_candidates=sum(len(t['pedal_candidates']) for t in guitars),
                counterexamples=sum(len(t['counterexamples']) for t in guitars),limitations=report['limitations'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--aggregate',type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:
        p.error('Occurrence evidence must remain in private local-artifacts')
    report=analyze(a.corpus,progress=True)
    with a.out.open('w',encoding='utf-8') as f:json.dump(report,f,separators=(',',':'))
    public=aggregate(report)
    if a.aggregate:a.aggregate.write_text(json.dumps(public,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in public.items() if k not in ('cohorts','limitations')}))
