"""Discover conditional stepwise approaches in the current composition.

No source files, lower-tier caches, mutation, phrase inference or preferred
musical direction. Maximal runs and refusals stay visible. Original observations
are not updated: these are context queries on the supplied current Tier2.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
from copy import deepcopy

import connected_tier2 as connected
import musical_tier2 as music
import melodic_arrival_relation as arrival
from source_fact_tier1 import project_documents
from source_tie_tier1 import extract_documents
from source_observation_evidence import digest

SCHEMA = 'melodic-approach-discovery/1'
POLICY = dict(
    population='Every numeric source GM24-31 part and every explicit voice',
    grouping='Complete accepted written ties; coattack/dead/unknown/grace/unresolved barriers',
    gaps='Positive rests/gaps break a run: conservative grouping policy, not musical law',
    runs='Maximal same-direction consecutive degrees under all global maxima; turningpoint shared; minimum three attacks; no shortening failed runs',
    interpretation='Whole-song and bounding-bar backing-only maxima of both existing profiles; every spanned-bar AardenEssen maximum; retain all exact maxima',
    evidence='CURRENT_COMPOSITION_CONTEXT_NOT_ORIGINAL_SOURCE_VOTES',
    choice='No aesthetic ranking or inferred preferred direction',
)

def ranking(rows,field):
    ranked=sorted(rows,key=lambda r:(r.get(field)is None,-r[field]if r.get(field)is not None else 0,r['id']))
    available=[r for r in ranked if r.get(field)is not None]
    top=[]if not available else[r for r in available if r[field]==available[0][field]]
    return dict(score_field=field,ranking=ranked,exact_maxima=top,undefined_count=len(ranked)-len(available))

def profile_rows(groups,label):
    evidence=music.tonal_evidence(groups)['scopes'][0]
    return [dict(scope=label,family=family,used_member_refs=evidence['used_member_refs'],excluded_member_refs=evidence['excluded_member_refs'],
                 pitch_class_duration_q=evidence['pitch_class_duration_q'],
                 **ranking([c for c in evidence['candidates']if c['family']==family],'score'))for family,*_ in music.TONAL_PROFILES]

def contexts_from_rankings(rows):
    if any(not r['exact_maxima']for r in rows):raise ValueError('NO_DEFINED_MAXIMUM_IN_REQUIRED_CONTEXT')
    return [dict(id=row['scope']+'/'+c['id'],tonic_pc=c['tonic_pc'],intervals=c['reference_intervals'])for row in rows for c in row['exact_maxima']]

def raw_note(documents,event):
    part=documents[f"track-{event['part_id']}.json"];measure=part['measures'][event['bar']-1]
    voice=measure['voices'][event['voice']];beat=voice['beats'][event['beat']]
    return measure,voice,beat,beat['notes'][event['note']]

def attack_inventory(documents,normalized,core,parts):
    """Group accepted written ties; never infer a line inside a coattack."""
    events={e['id']:e for e in normalized['events']};groups={m['id']:g for g in core['coattacks']for m in g['members']}
    chains=music.written_tie_chains(core);chain_by_ref={r:c for c in chains['chains']for r in c['occurrence_refs']}
    unresolved={r['destination']:r['reason']for r in chains['unresolved']}
    lanes=defaultdict(list);barriers=[];raw_counts=Counter();tied_continuations=0
    for e in normalized['events']:
        if e['part_id']not in parts:continue
        raw_counts[e['part_id']]+=1;chain=chain_by_ref.get(e['id'])
        if chain and chain['origin_ref']!=e['id']:tied_continuations+=1;continue
        refs=chain['occurrence_refs']if chain else[e['id']];members=[events[r]for r in refs]
        reasons=[]
        for member in members:
            ref=member['id'];m,v,b,n=raw_note(documents,member);g=groups[ref]
            if len(g['members'])!=1:reasons.append('COATTACK_NOT_ONE_COMPLETE_LINE')
            if n.get('dead'):reasons.append('DEAD_MEMBER')
            if member['pitch']is None:reasons.append('UNKNOWN_WRITTEN_PITCH')
            elif F(member['pitch']).denominator!=1:reasons.append('NONINTEGER_WRITTEN_PITCH')
            if F(member['duration_q'])<=0 or b.get('graceNote'):reasons.append('GRACE_OR_NONPOSITIVE_DURATION')
            if g['timing_uncertain']:reasons.append('SOURCE_TIMING_UNCERTAIN')
            if m.get('rest')or v.get('rest')or b.get('rest')or n.get('rest'):reasons.append('REST_DECLARATION')
            if ref in unresolved:reasons.append('UNRESOLVED_WRITTEN_TIE:'+unresolved[ref])
            if 'tie'in n and type(n['tie'])is not bool:reasons.append('UNKNOWN_TYPED_TIE_DECLARATION')
        if chain and(chain['kind']!='written_pitched_tie'or chain['origin_has_unresolved_incoming_tie']):reasons.append('UNRESOLVED_OR_NONPITCHED_CHAIN')
        if len({m['pitch']for m in members})!=1:reasons.append('TIE_PITCH_DISAGREEMENT')
        row=dict(attack_ref=e['id'],member_refs=refs,part_id=e['part_id'],voice=e['voice'],pitch=e['pitch'],
                 start_q=e['onset_q'],end_q=str(max(F(m['onset_q'])+F(m['duration_q'])for m in members)),
                 first_bar=min(m['bar']for m in members),last_bar=max(m['bar']for m in members),
                 source_note_flags=[{k:v for k,v in raw_note(documents,m)[3].items()if k not in('string','fret')}for m in members],
                 refusal_reasons=sorted(set(reasons)))
        lanes[e['part_id'],e['voice']].append(row)
    # Other notes/graces within a held span remain barriers, including when the
    # tie's written destinations have been collapsed into their actual root.
    for lane,rows in lanes.items():
        rows.sort(key=lambda r:(F(r['start_q']),r['attack_ref']))
        for i,row in enumerate(rows):
            left,right=F(row['start_q']),F(row['end_q'])
            for other in rows:
                if other is row:continue
                a,b=F(other['start_q']),F(other['end_q'])
                if(a<right and b>left)or(a==b and left<=a<right):
                    row['refusal_reasons']=sorted(set(row['refusal_reasons']+['SAME_VOICE_OVERLAP_OR_POINT']))
            if row['refusal_reasons']:barriers.append(row)
    return dict(lanes=lanes,barriers=barriers,raw_occurrences_by_part=dict(raw_counts),tie_continuations_collapsed=tied_continuations,
                accepted_tie_graph=dict(links=core['written_ties']['links'],unresolved=core['written_ties']['unresolved']))

def maximal_runs(rows,interpretations):
    """Every maximal eligible consecutive-degree segment; turningpoint shared."""
    runs=[];pairs=[];active=[];direction=None
    def flush():
        nonlocal active,direction
        if active:runs.append(dict(attacks=active,direction=direction))
        active=[];direction=None
    for a,b in zip(rows,rows[1:]):
        reasons=[];steps=[]
        if a['refusal_reasons']or b['refusal_reasons']:reasons.append('STRUCTURAL_BARRIER')
        delta=F(b['start_q'])-F(a['end_q'])
        if delta>0:reasons.append('POSITIVE_REST_OR_GAP_POLICY')
        elif delta<0:reasons.append('OVERLAPPING_WRITTEN_SPANS')
        if not interpretations:reasons.append('NO_GLOBAL_INTERPRETATION')
        if not reasons:
            for c in interpretations:
                try:
                    x=music.collection_degree_relation(c['tonic_pc'],c['intervals'],pitch=a['pitch'])['diatonic_coordinate']
                    y=music.collection_degree_relation(c['tonic_pc'],c['intervals'],pitch=b['pitch'])['diatonic_coordinate']
                    steps.append(dict(interpretation=c['id'],step=y-x))
                except ValueError as exc:reasons.append('OUTSIDE_GLOBAL_COLLECTION');steps.append(dict(interpretation=c['id'],refusal=str(exc)))
            values={r['step']for r in steps if 'step'in r}
            if len(values)!=1:reasons.append('GLOBAL_STEP_DISAGREEMENT')
            elif next(iter(values))not in(-1,1):reasons.append('REPEAT_OR_NONCONSECUTIVE_GLOBAL_STEP')
        pairs.append(dict(left=a['attack_ref'],right=b['attack_ref'],gap_q=str(delta),steps=steps,refusal_reasons=sorted(set(reasons))))
        if reasons:flush();continue
        new_direction=steps[0]['step']
        if active and direction==new_direction and active[-1]['attack_ref']==a['attack_ref']:active.append(b)
        else:flush();active=[a,b];direction=new_direction
    flush();return runs,pairs

def evaluate_run(run,part,global_rankings,backing,temporal):
    attacks=run['attacks'];first=min(a['first_bar']for a in attacks);last=max(a['last_bar']for a in attacks)
    local=profile_rows([g for g in backing if first<=g['bar']<=last],f'part{part}:bars{first}-{last}:backing')
    timed=[]
    for r in temporal['measures']:
        if first<=int(r['frame_ref'].split(':')[1])<=last:
            timed.append(dict(scope=f"part{part}:backing:{r['id']}",family='AardenEssen',contributing_frames=r['contributing_frame_refs'],
                              used_member_refs=r['used_member_refs'],excluded_member_refs=r['excluded_member_refs'],**ranking(r['candidates'],'smoothed_score')))
    assert len(timed)==last-first+1
    rankings=global_rankings+local+timed
    row=dict(part_id=part,voice=attacks[0]['voice'],attack_refs=[a['attack_ref']for a in attacks],attacks=attacks,
             bars=[first,last],start_q=attacks[0]['start_q'],end_q=attacks[-1]['end_q'],direction=run['direction'],
             original_pitches=[a['pitch']for a in attacks],maximal_run=True,rankings=rankings,refusal_reasons=[])
    try:
        interpretations=contexts_from_rankings(rankings);row['interpretations']=interpretations
        model=arrival.fit(row['original_pitches'],interpretations)
        assert arrival.realize(model)==row['original_pitches']
        row.update(relation=model,original_reconstruction='PASS',status='ORIGINAL_FIT_FLIP_PENDING')
        try:row.update(proposed_pitches=arrival.realize(model,mode='flip'),status='RELATION_AND_FLIP_ADMITTED')
        except ValueError as exc:row.update(status='FLIP_REFUSED',refusal_reasons=['FLIP_INTERPRETATION_DISAGREEMENT'],error=str(exc))
    except ValueError as exc:row.update(status='ORIGINAL_RELATION_REFUSED',original_reconstruction='NOT_REACHED',refusal_reasons=['LOCAL_OR_TIMED_INTERPRETATION_NOT_SUPPORTED'],error=str(exc))
    return row


def _candidate_identity(row, input_sha256):
    return 'approach:' + digest(dict(input_sha256=input_sha256,
        attack_refs=row['attack_refs'], interpretations=row.get('interpretations', [])))


def discover(t2):
    """Query all eligible written lines; no edits or artistic preference claim."""
    input_sha256 = digest(t2)
    lower = connected.realize(connected.strip_lower(t2))
    docs = project_documents(lower)
    normalized = extract_documents(docs)
    core = music.strip_lower(music.analyze(normalized))
    catalog = [dict(part_id=p['partId'], name=p.get('name'), instrumentId=p.get('instrumentId'))
               for name, p in docs.items() if name.startswith('track-')]
    catalog.sort(key=lambda p: p['part_id'])
    parts = [p['part_id'] for p in catalog
             if type(p['instrumentId']) is int and 24 <= p['instrumentId'] <= 31]
    inventory = attack_inventory(docs, normalized, core, parts)
    runs, pairs, short, global_rankings = [], [], [], []
    for part in parts:
        backing = [g for g in core['coattacks'] if g['part_id'] != part]
        ranks = profile_rows(backing, f'part{part}:whole-song-backing')
        global_rankings.extend(ranks)
        try:
            interpretations = contexts_from_rankings(ranks)
        except ValueError:
            interpretations = []
        temporal = music.temporal_tonal_evidence(backing, core['measure_geometry'])['scopes'][0]
        for (pid, voice), rows in sorted(inventory['lanes'].items()):
            if pid != part:
                continue
            segments, steps = maximal_runs(rows, interpretations)
            pairs.extend(dict(part_id=pid, voice=voice, **row) for row in steps)
            for segment in segments:
                if len(segment['attacks']) < 3:
                    short.append(dict(part_id=pid, voice=voice,
                        attack_refs=[a['attack_ref'] for a in segment['attacks']],
                        reason='MAXIMAL_RUN_LESS_THAN_THREE_ATTACKS'))
                    continue
                row = evaluate_run(segment, part, ranks, backing, temporal)
                row.setdefault('interpretations', [])
                row['input_sha256'] = input_sha256
                row['id'] = _candidate_identity(row, input_sha256)
                runs.append(row)
    runs.sort(key=lambda r: (F(r['start_q']), r['part_id'], r['voice'], r['attack_refs']))
    if len({r['id'] for r in runs}) != len(runs):
        raise ValueError('Duplicate discovered approach identity')
    if digest(t2) != input_sha256:
        raise ValueError('Discovery changed its input')
    return dict(schema=SCHEMA, input_sha256=input_sha256, policy=deepcopy(POLICY),
        evidence_kind=POLICY['evidence'], catalog=catalog, guitar_parts=parts,
        attack_lanes=[dict(part_id=p, voice=v, attacks=rows)
                      for (p,v), rows in sorted(inventory['lanes'].items())],
        barriers=inventory['barriers'], accepted_tie_graph=inventory['accepted_tie_graph'],
        pair_inventory=pairs, short_maximal_runs=short, global_rankings=global_rankings,
        runs=runs, counts=dict(
            guitar_parts=len(parts), guitar_voices=len(inventory['lanes']),
            raw_guitar_occurrences=sum(inventory['raw_occurrences_by_part'].values()),
            attack_groups=sum(map(len, inventory['lanes'].values())),
            tie_continuations_collapsed=inventory['tie_continuations_collapsed'],
            structural_barrier_groups=len(inventory['barriers']),
            structural_refusals=dict(Counter(x for r in inventory['barriers'] for x in r['refusal_reasons'])),
            adjacent_pairs=len(pairs), pair_refusals=dict(Counter(x for r in pairs for x in r['refusal_reasons'])),
            maximal_runs_under_three=len(short), maximal_runs_at_least_three=len(runs),
            run_statuses=dict(Counter(r['status'] for r in runs))),
        ownership_admission='NOT_TESTED', execution_and_playback='NOT_TESTED',
        musical_preference='NOT_ASSERTED')


def backing_context(t2, row):
    """Show current written overlaps and exact vertical intervals, without ranking.

    The candidate must describe this exact current input. Pitch realization is
    checked again with the same approach relation; this does not authorize edits.
    """
    before = digest(t2)
    if row.get('input_sha256') != before or row.get('id') != _candidate_identity(row, before):
        raise ValueError('Stale or unidentified current-context candidate')
    if row.get('status') != 'RELATION_AND_FLIP_ADMITTED':
        raise ValueError('An admitted relation and flip are required')
    if arrival.realize(row['relation']) != row['original_pitches'] or arrival.realize(row['relation'], mode='flip') != row['proposed_pitches']:
        raise ValueError('Candidate pitches disagree with the same relationship')
    if row['relation']['interpretations'] != row['interpretations']:
        raise ValueError('Candidate interpretation evidence differs')
    lower = connected.realize(connected.strip_lower(t2))
    docs = project_documents(lower)
    normalized = extract_documents(docs)
    events = {e['id']: e for e in normalized['events']}
    attacks = row['attacks']
    if (len(attacks) != len(row['original_pitches'])
            or [a['attack_ref'] for a in attacks] != row['attack_refs']):
        raise ValueError('Candidate roots differ from its attack groups')
    core = music.strip_lower(music.analyze(normalized))
    inventory = attack_inventory(docs, normalized, core, [row['part_id']])
    current_attacks = {a['attack_ref']:a for values in inventory['lanes'].values() for a in values}
    if any(a != current_attacks.get(a['attack_ref']) or a['refusal_reasons'] for a in attacks):
        raise ValueError('Candidate attack membership differs from complete current ties')
    for attack, pitch in zip(attacks, row['original_pitches']):
        members = [events[r] for r in attack['member_refs']]
        if (not members or members[0]['id'] != attack['attack_ref']
                or any(e['pitch'] != pitch or e['part_id'] != row['part_id']
                       or e['voice'] != row['voice'] for e in members)
                or members[0]['onset_q'] != attack['start_q']
                or str(max(F(e['onset_q'])+F(e['duration_q']) for e in members)) != attack['end_q']):
            raise ValueError('Candidate attack membership differs from current facts')
    start, end = F(row['start_q']), F(row['end_q'])
    if start != F(attacks[0]['start_q']) or end != F(attacks[-1]['end_q']):
        raise ValueError('Candidate extent differs from its complete attacks')
    others = [e for e in events.values() if e['part_id'] != row['part_id']
              and F(e['duration_q']) > 0 and F(e['onset_q']) < end
              and F(e['onset_q'])+F(e['duration_q']) > start]
    points = [e for e in events.values() if e['part_id'] != row['part_id']
              and F(e['duration_q']) == 0 and start <= F(e['onset_q']) < end]
    boundaries = {start, end}
    for e in others:
        boundaries.update((max(start, F(e['onset_q'])), min(end, F(e['onset_q'])+F(e['duration_q']))))
    for a in attacks:
        boundaries.update((F(a['start_q']), F(a['end_q'])))
    cells = []
    ordered = sorted(boundaries)
    for left, right in zip(ordered, ordered[1:]):
        indices = [i for i,a in enumerate(attacks) if F(a['start_q']) <= left and F(a['end_q']) >= right]
        if len(indices) != 1:
            raise ValueError('Candidate does not completely cover its declared context')
        index = indices[0]
        active = sorted((e for e in others if F(e['onset_q']) < right and F(e['onset_q'])+F(e['duration_q']) > left), key=lambda e:e['id'])
        cells.append(dict(start_q=str(left), end_q=str(right), attack_ref=attacks[index]['attack_ref'],
            original_pitch=row['original_pitches'][index], proposed_pitch=row['proposed_pitches'][index],
            backing_occurrence_refs=[e['id'] for e in active],
            intervals=[dict(occurrence_ref=e['id'], backing_pitch=e['pitch'],
                original=None if e['pitch'] is None else str(F(row['original_pitches'][index])-F(e['pitch'])),
                proposed=None if e['pitch'] is None else str(F(row['proposed_pitches'][index])-F(e['pitch']))) for e in active]))
    if digest(t2) != before:
        raise ValueError('Context query changed its input')
    return dict(input_sha256=before, candidate_id=row['id'], cells=cells,
                point_occurrence_refs=[e['id'] for e in points],
                semantics='Current written overlaps only; no acoustic sustain, preferred harmony or original-source vote claim')
