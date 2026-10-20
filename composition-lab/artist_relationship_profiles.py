"""Development-only relationship profiles over existing, accepted observations.

No detector runs here. Counts describe written notation, not artist intent,
emotional purpose, functional harmony, performed articulation or phrase labels.
Source-located tables/models belong in private local-artifacts.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
from itertools import combinations
import hashlib
import json

from artist_profiles import FEATURES, connected_families, context

RELATION_FEATURES=FEATURES+('ghost','harmonic','staccato','accentuated','whammy_curve',
                          'hammer_on_fretted','pull_off_fretted')


def signature(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def bucket(q):
    return 'short' if F(q)<F(1,2) else 'medium' if F(q)<2 else 'long'


def _identity(value):
    if isinstance(value,bool) or not isinstance(value,(str,int)) or not str(value).strip():
        raise ValueError('Nonempty scalar source identity required')
    return str(value)


def validate_profile_inputs(report,accepted_pedals):
    """Fail closed on ambiguous joins; do not repair or reclassify accepted data.

    Phrase membership may contain untagged context. Roles must be a subset of
    membership, not equal to it; the accepted artifact intentionally has context.
    """
    songs=set();tracks={};raw_identities={};audit=Counter()
    for song in report['songs']:
        sid=_identity(song['song_id'])
        if sid in songs:raise ValueError('Duplicate source song identity')
        songs.add(sid);local=set()
        for track in song['tracks']:
            tid=_identity(track['part_id'])
            if tid in local:raise ValueError('Duplicate source track identity')
            local.add(tid);lookup={}
            for row in [*track['rows'],*track.get('grace_rows',[])]:
                ident=row['occurrence']
                if not isinstance(ident,str) or not ident:raise ValueError('Nonempty occurrence identity required')
                if ident in lookup:raise ValueError('Duplicate source occurrence identity')
                lookup[ident]=row
            tracks[sid,tid]=lookup;audit['source_occurrences']+=len(lookup)
            raw_identities[sid,tid]=(song['song_id'],track['part_id'])
    seen=set()
    for track in accepted_pedals.get('tracks',[]):
        key=(_identity(track['song_id']),_identity(track['part_id']))
        if key in seen:raise ValueError('Duplicate accepted pedal track coverage')
        seen.add(key)
        if key not in tracks:raise ValueError('Accepted pedal track missing from source')
        if (track['song_id'],track['part_id'])!=raw_identities[key]:
            raise ValueError('Accepted/source identity representations do not match')
        lookup=tracks[key];role_uses=set();cycle_uses=set()
        for phrase in track['phrases']:
            if any(k not in phrase for k in ('roles','members','cycles')):raise ValueError('Incomplete accepted phrase membership')
            roles=phrase['roles'];members=phrase['members']
            if len(members)!=len(set(members)):raise ValueError('Duplicate accepted phrase member')
            if not set(roles)<=set(members):raise ValueError('Accepted role outside phrase membership')
            if any(i not in lookup for i in members):raise ValueError('Accepted phrase member missing from source')
            if any(role not in ('call','response') for role in roles.values()):raise ValueError('Unsupported accepted pedal role')
            if role_uses&set(roles):raise ValueError('Accepted role reused across phrases')
            role_uses.update(roles)
            audit['accepted_untagged_context_members']+=len(set(members)-set(roles))
            for cycle in phrase['cycles']:
                required=('call_start_q','response_start_q','return_q','call_members','response_members')
                if any(cycle.get(k) is None for k in required):raise ValueError('Incomplete accepted pedal cycle')
                ids=cycle['call_members']+cycle['response_members']
                if not cycle['call_members'] or not cycle['response_members'] or len(ids)!=len(set(ids)):
                    raise ValueError('Empty or duplicate accepted cycle membership')
                if cycle_uses&set(ids):raise ValueError('Accepted cycle member counted twice')
                cycle_uses.update(ids)
                start,response,ret=(F(cycle[k]) for k in ('call_start_q','response_start_q','return_q'))
                if not start<response<ret:raise ValueError('Invalid accepted call/response order')
                for field,role,lo,hi in [('call_members','call',start,response),('response_members','response',response,ret)]:
                    for ident in cycle[field]:
                        if ident not in lookup or roles.get(ident)!=role:raise ValueError('Accepted cycle/source/role reference mismatch')
                        row=lookup[ident]
                        if row['tie_destination'] or not lo<=F(row['onset_q'])<hi:
                            raise ValueError('Accepted cycle member outside declared attack bounds')
                audit['accepted_cycles']+=1
            audit['accepted_phrases']+=1
    audit.update(source_songs=len(songs),source_tracks=len(tracks),accepted_track_coverage=len(seen))
    return dict(audit)


def validate_programs(report,programs):
    source={(_identity(s['song_id']),_identity(t['part_id'])):(s['song_id'],t['part_id'])
            for s in report['songs'] for t in s['tracks']}
    for key,value in programs.items():
        if not isinstance(key,tuple) or len(key)!=2:raise ValueError('Program key must be a song/track pair')
        canonical=tuple(_identity(x) for x in key)
        if canonical not in source or key!=source[canonical]:raise ValueError('Program/source identity representations do not match')
        if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=127:raise ValueError('Invalid MIDI program')


class Counts:
    def __init__(self, support_sink=None):
        self.support_sink = support_sink
        self.cells=defaultdict(Counter)
        self.sections=defaultdict(set)
        self.examples=defaultdict(list)
        self.song_totals=Counter()
        self.songs={}
        self.namespaces={}

    def add(self,song,kind,condition,outcome,section=None,evidence=None,*,support=None):
        if self.support_sink is not None:
            self.support_sink(dict(song_id=song["song_id"],kind=kind,condition=condition,outcome=outcome,section=section,support=support if support is not None else evidence))
        sid=song['song_id'];namespace=(kind,condition.get('feature',condition.get('mechanism',condition.get('pattern_kind'))))
        condition=json.dumps(condition,sort_keys=True,separators=(',',':'))
        outcome=json.dumps(outcome,sort_keys=True,separators=(',',':'))
        key=(kind,condition,outcome)
        self.cells[key][sid]+=1;self.song_totals[namespace,sid]+=1
        self.namespaces[key]=namespace
        self.songs[sid]=song['family']
        if section is not None:self.sections[key].add((sid,str(section)))
        if evidence is not None and len(self.examples[key])<2:self.examples[key].append(evidence)

    def finish(self):
        families=defaultdict(set)
        for namespace,sid in self.song_totals:families[namespace,self.songs[sid]].add(sid)
        tables=defaultdict(list)
        for key,counts in self.cells.items():
            kind,condition,outcome=key
            namespace=self.namespaces[key]
            weight=sum(n/self.song_totals[namespace,sid]/len(families[namespace,self.songs[sid]]) for sid,n in counts.items())
            tables[kind,condition].append(dict(outcome=json.loads(outcome),count=sum(counts.values()),
                songs=len(counts),families=len({self.songs[s] for s in counts}),
                section_instances=len(self.sections[key]),weight=weight,
                examples=self.examples[key],
                song_counts=[dict(song_id=sid,family=self.songs[sid],count=n) for sid,n in sorted(counts.items(),key=lambda item:str(item[0]))]))
        result=[]
        for (kind,condition),outcomes in sorted(tables.items()):
            total=sum(o['weight'] for o in outcomes)
            song_eligible=Counter()
            for o in outcomes:
                for support in o['song_counts']:song_eligible[support['song_id']]+=support['count']
            for o in outcomes:o['conditional_probability']=o['weight']/total
            result.append(dict(kind=kind,condition=json.loads(condition),
                               eligible_count=sum(o['count'] for o in outcomes),
                               weighted_eligible_mass=total,
                               song_eligible_counts=[dict(song_id=sid,family=self.songs[sid],eligible_count=n) for sid,n in sorted(song_eligible.items(),key=lambda item:str(item[0]))],
                               outcomes=sorted(outcomes,key=lambda o:(-o['count'],str(o['outcome'])))))
        return result


def attack_groups(track,roles):
    pedal_covered=roles is not None;roles=roles or {}
    grouped=defaultdict(list);extras=defaultdict(set)
    for row in track['rows']:
        if not row['tie_destination'] and F(row['duration_q'])>0:grouped[F(row['onset_q'])].append(row)
    for g in track.get('coattack_groups',[]):extras[F(g['onset_q'])].update(g['labels'])
    lookup={r['occurrence']:r for r in track['rows']}
    for pair in track.get('hopo_transition_candidates',[]):
        feature=pair['direction']+'_'+pair['context'];origin=lookup.get(pair['origin'])
        if feature in RELATION_FEATURES and origin:extras[F(origin['onset_q'])].add(feature)
    pitches=[r['midi'] for r in track['rows'] if r['midi'] is not None]
    register=(min(pitches),max(pitches)) if pitches else (None,None)
    result=[]
    for q,rows in sorted(grouped.items()):
        labels=set(extras[q]);effects={e for r in rows for e in r.get('effects',[])}
        for old,new in [('bend','bend'),('slide','slide'),('palmMute','palm_mute'),('tapping','tapping'),('dead','dead')]:
            if old in effects:labels.add(new)
        for marker in ('ghost','harmonic','staccato','accentuated'):
            if marker in effects:labels.add(marker)
        if 'tremoloBar' in effects:labels.add('whammy_curve')
        if any(any(r.get(scope,{}).get(k) for scope in ('raw_note','raw_beat_effects') for k in ('vibrato','wideVibrato','leftHandVibrato')) for r in rows):labels.add('finger_vibrato')
        role_values={roles.get(r['occurrence']) for r in rows}-{None}
        for role in role_values & {'call','response'}:labels.add('pedal_'+role)
        known=set(RELATION_FEATURES)
        if not pedal_covered:known-={'pedal_call','pedal_response'}
        ps=sorted(r['midi'] for r in rows if r['midi'] is not None)
        if len(ps)!=len(rows):known-={'close_interval_texture','power_chord','extended_power_chord','double_stop'}
        sections={r.get('section_start') for r in rows}
        result.append(dict(q=q,rows=rows,labels=labels&known,known=known,
                           pitches=ps,all_pitches_known=len(ps)==len(rows),
                           section=next(iter(sections)) if len(sections)==1 else None,
                           duration=max(F(r['duration_q']) for r in rows),
                           context=context(rows[0],rows,register),
                           role='unknown' if not pedal_covered else 'not_tagged_in_accepted_pedal' if not role_values else '+'.join(sorted(role_values))))
    return result


def _pattern(groups,base,anchor=None,span=None):
    # All written member durations and voice IDs matter, not only the longest
    # note. This is a polyphonic written rhythm signature, not just attack IOIs.
    rhythm=(span,[(str(g['q']-base),sorted((r['voice'],str(F(r['duration_q']))) for r in g['rows'])) for g in groups])
    pitch=None
    if groups and all(g['all_pitches_known'] for g in groups):
        if anchor is None:anchor=min(groups[0]['pitches'])
        pitch=[[p-anchor for p in g['pitches']] for g in groups]
    return signature(rhythm),signature(pitch) if pitch is not None else None


def build_relationship_profile(report,accepted_pedals,artist,programs=None,*,partition='development',support_sink=None):
    """Fit only unflagged development songs; use supplied accepted pedal cycles.

    Existing global temporal eligibility is honored. We do not silently promote
    local recovery into detector/profile eligibility. Programs are optional
    provenance; missing values remain explicitly unknown.
    """
    if partition not in ('development','held_out'):raise ValueError('Unknown profile partition')
    input_audit=validate_profile_inputs(report,accepted_pedals)
    family=connected_families(report['songs']);programs=programs or {}
    validate_programs(report,programs)
    pedal_index={(t['song_id'],t['part_id']):t for t in accepted_pedals.get('tracks',[])}
    counts=Counts(support_sink);coverage=Counter();training=[];scope_counts=defaultdict(Counter)
    for source in report['songs']:
        if source.get('artist')!=artist or source['provisional_partition']!=partition or source.get('ai_generated') is not False or source.get('is_junk') is not False:continue
        song=dict(source,family=family[source['song_id']]);training.append(song['song_id'])
        headers={h['bar']:h for h in song.get('shared_layout',[])}
        tracks=[]
        for track in song['tracks']:
            if not track.get('guitar_or_bass'):continue
            if not track.get('temporal_relationships_eligible'):
                coverage['excluded_temporal_tracks']+=1;continue
            tid=track['part_id'];pedal=pedal_index.get((song['song_id'],tid))
            roles={k:v for phrase in pedal['phrases'] for k,v in phrase['roles'].items()} if pedal else None
            groups=attack_groups(track,roles);lookup={r['occurrence']:r for r in track['rows']}
            coverage['tracks']+=1;coverage['attack_groups']+=len(groups)
            coverage['grace_occurrences_excluded']+=len(track.get('grace_rows',[]))
            coverage['groups_unknown_pitch']+=sum(not g['all_pitches_known'] for g in groups)
            coverage['tracks_with_accepted_pedal_coverage']+=pedal is not None
            tracks.append((track,groups))
            bars=defaultdict(list)
            for g in groups:
                evidence=dict(song_id=song['song_id'],part_id=tid,members=[r['occurrence'] for r in g['rows']])
                sec=(tid,g['section']);harmony=sorted(g['labels']&{'close_interval_texture','power_chord','extended_power_chord','double_stop'})
                for feature in sorted(g['known']):
                    if feature.startswith('pedal_') and pedal is None:continue
                    scope=scope_counts[song['song_id'],tid,g['section'],feature]
                    scope['eligible_attack_groups']+=1;scope['positive_attack_groups']+=feature in g['labels']
                    for axis,value in [('context',g['context']),('written_harmony_labels',dict(known=g['all_pitches_known'],labels=harmony if g['all_pitches_known'] else None)),('accepted_pedal_role',g['role'])]:
                        if axis=='accepted_pedal_role' and pedal is None:continue
                        if axis=='written_harmony_labels' and feature in {'close_interval_texture','power_chord','extended_power_chord','double_stop'}:continue
                        if axis=='accepted_pedal_role' and feature.startswith('pedal_'):continue
                        counts.add(song,'technique_given_'+axis,dict(feature=feature,value=value),feature in g['labels'],sec,evidence)
                bars[g['rows'][0]['bar']].append(g)
            # Next written attack, never called a response without accepted roles.
            for a,b in zip(groups,groups[1:]):
                if a['section'] is None or a['section']!=b['section']:
                    coverage['next_attack_section_boundaries_excluded']+=1;continue
                gap=b['q']-(a['q']+a['duration'])
                condition=dict(previous_techniques=sorted(a['labels']),previous_context=a['context'],previous_known_features=sorted(a['known']))
                outcome=dict(next_techniques=sorted(b['labels']),next_context=b['context'],
                             next_known_features=sorted(b['known']),
                             ioi_q=str(b['q']-a['q']),separation='overlap' if gap<0 else 'contiguous' if gap==0 else 'gap')
                counts.add(song,'next_written_attack',condition,outcome,(tid,a['section']),support=dict(part_id=tid,members=[r['occurrence'] for g in (a,b) for r in g['rows']]))
            _mechanical_relationships(song,track,groups,counts,coverage)
            seen={};seen_members={};previous=None
            for bar,gs in sorted(bars.items()):
                base=min(F(r['onset_q'])-F(r.get('bar_offset_q','0')) for g in gs for r in g['rows'])
                header=headers.get(bar,{})
                span=dict(span_q=header.get('span_q',gs[0]['rows'][0].get('bar_span_q')),
                          signature=header.get('signature'))
                if span['span_q'] is None:coverage['bar_patterns_missing_span']+=1
                rhythm,pitch=_pattern(gs,base,span=span);sec=gs[0]['section']
                for kind,fp in [('rhythm',rhythm),('relative_pitch',pitch)]:
                    if fp is None:coverage['bar_pitch_patterns_unknown']+=1;continue
                    old=seen.get((kind,fp));state='first_observation' if old is None else 'same_section_return' if old==sec else 'other_section_return'
                    counts.add(song,'bar_pattern_return',dict(pattern_kind=kind),state,(tid,sec),support=dict(part_id=tid,members=[r['occurrence'] for g in gs for r in g['rows']]+seen_members.get((kind,fp),[]),bar=bar))
                    seen[kind,fp]=sec;seen_members[kind,fp]=[r['occurrence'] for g in gs for r in g['rows']]
                if previous and previous[0]+1==bar and previous[1]==sec:
                    counts.add(song,'adjacent_bar_variation',dict(previous_group_count=previous[4]),
                               dict(rhythm_same=previous[2]==rhythm,pitch_same=None if pitch is None or previous[3] is None else previous[3]==pitch),
                               (tid,sec),support=dict(part_id=tid,bars=[previous[0],bar]))
                previous=(bar,sec,rhythm,pitch,len(gs))
            if pedal:
                _pedal_cycles(song,track,pedal,lookup,counts,coverage)
        _track_interactions(song,tracks,programs,counts,coverage)
    scope_rows=[];song_counts=defaultdict(Counter)
    for (sid,tid,section,feature),values in sorted(scope_counts.items(),key=lambda item:str(item[0])):
        scope_rows.append(dict(song_id=sid,family=family[sid],part_id=tid,source_section_instance=section,feature=feature,
                               **values,rate=values['positive_attack_groups']/values['eligible_attack_groups'],
                               unit='regular attack groups; positive if any member carries the known annotation'))
        song_counts[sid,feature].update(values)
    song_rows=[dict(song_id=sid,family=family[sid],feature=feature,**values,
                    rate=values['positive_attack_groups']/values['eligible_attack_groups'],
                    unit='eligible regular track attack groups across this song')
               for (sid,feature),values in sorted(song_counts.items(),key=lambda item:str(item[0]))]
    return dict(schema='artist-written-relationships-v1',artist=artist,partition=partition,
                scope='development_fit' if partition=='development' else 'heldout_descriptive_only',
                observed_songs=sorted(training),observed_families=sorted({family[s] for s in training}),
                training_songs=sorted(training) if partition=='development' else [],
                training_families=sorted({family[s] for s in training}) if partition=='development' else [],
                coverage=dict(coverage),input_audit=input_audit,tables=counts.finish(),
                technique_song_summaries=song_rows,technique_local_summaries=scope_rows,
                weighting='Each relation kind and eligible unit domain (feature/mechanism/pattern kind): equal eligible song within connected family, conditional renormalization; raw song/outcome support retained',
                limitations=['Written relationships, not artist intent, acoustic sound, emotional purpose or functional harmony',
                             'Global temporal eligibility retained; no detector or approved pedal changes',
                             'Section instances are source markers, not inferred phrases or verse/chorus functions',
                             'Regular attack patterns exclude grace and tied destinations; not complete sounding textures',
                             'Rhythm fingerprints include all member durations/voice IDs and available bar span/meter; base-pitch contour is a separate fingerprint, not motif identity',
                             'Source marker absence is not absence of performed technique'])


def _mechanical_relationships(song,track,groups,counts,coverage):
    lookup={r['occurrence']:r for r in track['rows']}
    group_by_id={r['occurrence']:g for g in groups for r in g['rows']}
    next_by_id={r['occurrence']:b for a,b in zip(groups,groups[1:])
                if a['section'] is not None and a['section']==b['section'] for r in a['rows']}
    seen_whammy_beats=set()
    def beat_identity(row):
        return (row['bar'],row['voice'],row.get('beat',row['occurrence'].rsplit(':',1)[0]))
    for detail in track.get('technique_values',[]):
        ident=detail['occurrence'];g=group_by_id.get(ident);row=lookup.get(ident)
        if g is None or row is None:continue
        for mechanism in ('bend','whammy'):
            shape=detail.get(mechanism)
            if not shape:continue
            if not shape.get('valid'):
                coverage['invalid_'+mechanism+'_curves']+=1;continue
            if mechanism=='whammy':
                identity=beat_identity(row)
                if identity in seen_whammy_beats:
                    coverage['shared_whammy_note_records_deduplicated']+=1;continue
                seen_whammy_beats.add(identity)
            nxt=next_by_id.get(ident)
            origin_pitch=row['midi']
            if mechanism=='whammy':
                members=[r for r in g['rows'] if beat_identity(r)==beat_identity(row)]
                origin_pitch=min(r['midi'] for r in members) if all(r['midi'] is not None for r in members) else None
            next_interval=(min(nxt['pitches'])-origin_pitch) if nxt and nxt['all_pitches_known'] and origin_pitch is not None else None
            counts.add(song,'mechanical_shape_given_context',dict(mechanism=mechanism,context=g['context'],
                       written_harmony_labels=sorted(g['labels']&{'power_chord','extended_power_chord','close_interval_texture','double_stop'}) if g['all_pitches_known'] else None,
                       accepted_pedal_role=g['role']),
                       dict(peak_semitones=shape.get('peak_semitones'),initial_semitones=shape.get('initial_semitones'),
                            source_unit='beat-scoped whammy' if mechanism=='whammy' else 'note-scoped bend',
                            final_semitones=shape.get('final_semitones'),first_peak_fraction=shape.get('first_peak_fraction'),
                            slopes_semitones_per_quarter=shape.get('slopes_semitones_per_quarter'),
                            point_vibrato_flags=shape.get('point_vibrato_flags'),
                            next_attack_written_minimum_interval=next_interval,
                            next_attack_interval_known=next_interval is not None),
                       (track['part_id'],g['section']),dict(song_id=song['song_id'],part_id=track['part_id'],occurrence=ident))
    for pair in track.get('hopo_transition_candidates',[]):
        g=group_by_id.get(pair['origin']);destination=lookup.get(pair['destination'])
        if g is None or destination is None:continue
        counts.add(song,'hopo_transition_given_context',dict(context=g['context'],accepted_pedal_role=g['role']),
                   dict(direction=pair['direction'],context=pair['context'],fret_distance=pair.get('fret_distance'),
                        origin_duration_q=lookup[pair['origin']]['duration_q'],destination_duration_q=destination['duration_q']),
                   (track['part_id'],g['section']),support=dict(part_id=track['part_id'],members=[pair['origin'],pair['destination']]))


def heldout_support(model,held):
    """Support coverage only; held-out outcomes never change fitted tables."""
    if model.get('scope')!='development_fit' or held.get('scope')!='heldout_descriptive_only' or model['artist']!=held['artist']:
        raise ValueError('Separate same-artist development and held-out profiles required')
    if set(model['training_songs'])&set(held['observed_songs']) or set(model['training_families'])&set(held['observed_families']):
        raise ValueError('Source song/family leakage')
    index={(t['kind'],signature(t['condition'])):{signature(o['outcome']) for o in t['outcomes']} for t in model['tables']}
    support=defaultdict(Counter)
    for t in held['tables']:
        key=(t['kind'],signature(t['condition']));row=support[t['kind']]
        row['heldout_eligible_count']+=t['eligible_count'];row['heldout_conditions']+=1
        if key not in index:
            row['unseen_condition_count']+=t['eligible_count'];continue
        row['supported_conditions']+=1;row['supported_condition_count']+=t['eligible_count']
        for o in t['outcomes']:
            if signature(o['outcome']) in index[key]:row['supported_condition_and_outcome_count']+=o['count']
            else:row['unseen_outcome_given_supported_condition_count']+=o['count']
    fields=('heldout_eligible_count','heldout_conditions','supported_conditions','supported_condition_count',
            'supported_condition_and_outcome_count','unseen_condition_count','unseen_outcome_given_supported_condition_count')
    result={k:{f:v[f] for f in fields} for k,v in support.items()}
    for row in result.values():
        assert row['heldout_eligible_count']==row['unseen_condition_count']+row['supported_condition_count']
        assert row['supported_condition_count']==row['supported_condition_and_outcome_count']+row['unseen_outcome_given_supported_condition_count']
    return dict(by_kind=result,heldout_songs=len(held['observed_songs']),heldout_families=len(held['observed_families']),
                limitation='Exact condition/outcome vocabulary coverage, not prediction accuracy, musical correctness or artist feel')


def _pedal_cycles(song,track,pedal,lookup,counts,coverage):
    tid=track['part_id']
    for pi,phrase in enumerate(pedal['phrases']):
        seen={};seen_members={}
        for cycle in phrase.get('cycles',[]):
            ids=cycle['call_members']+cycle['response_members']
            if any(i not in lookup for i in ids) or set(cycle['call_members'])&set(cycle['response_members']):
                coverage['pedal_cycles_missing_or_overlapping_members']+=1;continue
            call=[lookup[i] for i in cycle['call_members']];answer=[lookup[i] for i in cycle['response_members']]
            if not call or not answer or any(r['tie_destination'] for r in call+answer):
                coverage['pedal_cycles_invalid_attack_members']+=1;continue
            if any(cycle.get(k) is None for k in ('call_start_q','response_start_q','return_q')):
                coverage['pedal_cycles_missing_return_or_bounds']+=1;continue
            start=F(cycle['call_start_q']);response=F(cycle['response_start_q']);ret=F(cycle['return_q'])
            if not start<response<ret:
                coverage['pedal_cycles_invalid_order']+=1;continue
            if any(not start<=F(r['onset_q'])<response for r in call) or any(not response<=F(r['onset_q'])<ret for r in answer):
                coverage['pedal_cycles_outside_declared_bounds']+=1;continue
            def groups_for(rows):
                tmp=defaultdict(list)
                for r in rows:tmp[F(r['onset_q'])].append(r)
                return [dict(q=q,rows=rs,duration=max(F(r['duration_q']) for r in rs),
                             pitches=sorted(r['midi'] for r in rs if r['midi'] is not None),
                             all_pitches_known=all(r['midi'] is not None for r in rs)) for q,rs in sorted(tmp.items())]
            cg,rg=groups_for(call),groups_for(answer)
            known=all(r['midi'] is not None for r in call+answer)
            anchor=min(r['midi'] for r in call) if known else None
            cr,cp=_pattern(cg,start,anchor,span=str(response-start));rr,rp=_pattern(rg,response,anchor,span=str(ret-response))
            condition=dict(call_attack_groups=len(cg),call_span=bucket(response-start),
                           call_techniques=sorted({e for r in call for e in r.get('effects',[])}))
            outcome=dict(response_attack_groups=len(rg),response_span_q=str(ret-response),
                         response_textures=sorted({len(g['rows']) for g in rg}),
                         response_techniques=sorted({e for r in answer for e in r.get('effects',[])}),
                         response_intervals_from_lowest_call=sorted({r['midi']-anchor for r in answer}) if known else None)
            sec=(tid,'accepted_pedal',pi)
            counts.add(song,'accepted_pedal_response',condition,outcome,sec,
                       dict(song_id=song['song_id'],part_id=tid,phrase=pi,call_members=cycle['call_members'],response_members=cycle['response_members']))
            call_fp=(anchor,cr,cp)
            if cp is not None and rp is not None and call_fp in seen:
                old=seen[call_fp]
                counts.add(song,'same_pedal_call_answer_variation',dict(call_groups=len(cg)),
                           dict(response_rhythm_same=rr==old[0],response_pitch_same=rp==old[1]),sec,support=dict(part_id=tid,phrase=pi,members=ids+seen_members.get(call_fp,[])))
            if cp is not None and rp is not None:seen[call_fp]=(rr,rp);seen_members[call_fp]=list(ids)
            coverage['accepted_pedal_cycles']+=1


def _track_interactions(song,tracks,programs,counts,coverage):
    for (ta,a),(tb,b) in combinations(tracks,2):
        left={g['q']:g for g in a};right={g['q']:g for g in b}
        if not left or not right:continue
        condition=dict(programs=[programs.get((song['song_id'],ta['part_id']),'unknown'),
                                 programs.get((song['song_id'],tb['part_id']),'unknown')])
        for q in sorted(left.keys()|right.keys()):
            x,y=left.get(q),right.get(q)
            if x is None or y is None:
                counts.add(song,'track_attack_alignment',condition,'left_only' if x else 'right_only',support=dict(parts=[ta['part_id'],tb['part_id']],onset_q=str(q),members=[r['occurrence'] for g in (x,y) if g for r in g['rows']]));continue
            counts.add(song,'track_attack_alignment',condition,'simultaneous',support=dict(parts=[ta['part_id'],tb['part_id']],members=[r['occurrence'] for g in (x,y) for r in g['rows']]))
            known=x['all_pitches_known'] and y['all_pitches_known']
            outcome=dict(cardinalities=[len(x['rows']),len(y['rows'])],
                         absolute_written_minimum_interval=abs(min(x['pitches'])-min(y['pitches'])) if known else None,
                         left_techniques=sorted(x['labels']),right_techniques=sorted(y['labels']),
                         left_known_features=sorted(x['known']),right_known_features=sorted(y['known']))
            counts.add(song,'simultaneous_track_relationship',condition,outcome,
                       (ta['part_id'],tb['part_id'],x['section'],y['section']),support=dict(parts=[ta['part_id'],tb['part_id']],members=[r['occurrence'] for g in (x,y) for r in g['rows']]))
            coverage['simultaneous_track_pairs']+=1
