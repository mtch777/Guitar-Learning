"""Shared Drop E realization from structural templates and observed shape palettes.

All rhythm templates enter through ReferenceIndex. This module assigns new pitch
roles and contacts; it never selects an artist weight or calls a fixed recipe.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import json
import random

TUNING = [64, 59, 55, 50, 45, 40, 35, 28]
ARTISTS = ('Invent Animate', 'Currents', 'ERRA')
MODES = {'Aeolian': [0,2,3,5,7,8,10], 'Dorian': [0,2,3,5,7,9,10],
    'Ionian': [0,2,4,5,7,9,11], 'Mixolydian': [0,2,4,5,7,9,10],
    'Lydian': [0,2,4,6,7,9,11], 'Phrygian': [0,1,3,5,7,8,10]}
STYLES = ('arpeggio', 'chordal', 'melodic', 'pedal', 'rhythmic', 'other')
FOCUSES = ('single', 'interval', 'triad', 'chord', 'mixed')


def stable_seed(value):
    return int(hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16], 16)


def focus_profile(events):
    counts = Counter('single' if len(e['members']) == 1 else 'interval' if len(e['members']) == 2 else
        'triad' if len(e['members']) == 3 else 'chord' for e in events)
    n = len(events)
    return next((key for key in FOCUSES[:-1] if counts[key]*2 > n), 'mixed')


def validate_request(request):
    if not isinstance(request, dict): raise ValueError('Request must be an object')
    artists = request.get('artists')
    if not isinstance(artists, list) or not artists or len(set(artists)) != len(artists) or any(a not in ARTISTS for a in artists):
        raise ValueError('Choose one or more supported artists')
    if request.get('mode') not in MODES: raise ValueError('Choose an offered E mode')
    tempo = request.get('tempo')
    if type(tempo) is not int or not 80 <= tempo <= 200: raise ValueError('Tempo must be a whole number from 80 to 200 BPM')
    if type(request.get('seed')) is not int: raise ValueError('Seed must be an integer')
    sections = request.get('sections')
    if not isinstance(sections, list) or not 1 <= len(sections) <= 12: raise ValueError('Choose 1–12 sections')
    out = []
    for section in sections:
        if not isinstance(section, dict) or section.get('style') not in STYLES or section.get('focus') not in FOCUSES:
            raise ValueError('Each section requires an offered style and focus')
        if type(section.get('length_q')) not in (int, str): raise ValueError('Section length must be an exact rational')
        length = F(section['length_q'])
        if length <= 0 or length > 64: raise ValueError('Section length must be positive and at most 64 quarter notes')
        if 'seed' in section and type(section['seed']) is not int: raise ValueError('Section seed must be an integer')
        out.append({**section, 'length_q': str(length)})
    return {**request, 'artists': [a for a in ARTISTS if a in artists], 'sections': out}


def _pitch_assignments(template, contacts, rng, mode, budget=48):
    """Nonuniform order-preserving role assignments; repeated roles stay related."""
    allowed = set(MODES[mode])
    pitches = sorted({TUNING[s-1]+f for s,f in contacts if f > 0 and (TUNING[s-1]+f-4)%12 in allowed})
    role_count = len(template['source_relative_pitches'])
    fixed = {}
    for event in template['events']:
        for member in event['members']:
            if member.get('open_string') is None: continue
            pitch = TUNING[member['open_string']-1]
            if (pitch-4)%12 not in allowed: return [], 'fixed_open_outside_mode'
            if member['role'] in fixed and fixed[member['role']] != pitch: return [], 'contradictory_open_role'
            fixed[member['role']] = pitch
    universe = sorted(set(pitches) | set(fixed.values()))
    if len(universe) < role_count: return [], 'palette_has_too_few_pitch_roles'
    choices, seen = [], set()
    # Preserve role order, not the source interval sizes. Exact source copies and
    # uniform transpositions are rejected later against the relative signature.
    for _ in range(budget):
        picked = tuple(sorted(rng.sample(universe, role_count)))
        if picked in seen or any(picked[k] != p for k,p in fixed.items()): continue
        seen.add(picked); choices.append(picked)
    if fixed:
        # Fixed anchors make blind sampling wasteful. Fill each ordered band.
        anchors = [(-1, -1000), *sorted(fixed.items()), (role_count, 1000)]
        for _ in range(budget):
            picked = [None]*role_count; valid = True
            for role,pitch in fixed.items(): picked[role] = pitch
            for (left,low),(right,high) in zip(anchors,anchors[1:]):
                candidates = [p for p in universe if low < p < high]
                needed = right-left-1
                if len(candidates) < needed: valid = False; break
                for offset,p in enumerate(sorted(rng.sample(candidates,needed)),left+1): picked[offset] = p
            picked = tuple(picked)
            if valid and picked not in seen: choices.append(picked); seen.add(picked)
    rng.shuffle(choices)
    return choices, None if choices else 'no_ordered_assignment_with_fixed_opens'


def _realize_window(template, palettes, mode, rng, ordinary, tapped):
    contacts = sorted(ordinary | tapped)
    assignments, reason = _pitch_assignments(template, contacts, rng, mode)
    if reason: return None, reason
    members = [(ei,ni,m) for ei,e in enumerate(template['events']) for ni,m in enumerate(e['members'])]
    nodes = {(ei,ni): m for ei,ni,m in members}
    parents = {key:key for key in nodes}
    def find(key):
        while parents[key] != key: key=parents[key]
        return key
    for link in template['links']:
        a,b = tuple(link['origin']),tuple(link['destination'])
        parents[find(b)] = find(a)
    groups = defaultdict(list)
    for key in nodes: groups[find(key)].append(key)
    last_reason = 'no_valid_contact_assignment'; best=None; successes=0
    for pitches in assignments:
        relative = [p-pitches[0] for p in pitches]
        changed_roles = {i for i,(a,b) in enumerate(zip(relative,template['source_relative_pitches'])) if a != b}
        changed_attacks = [i for i,e in enumerate(template['events']) if any(m['role'] in changed_roles for m in e['members'])]
        changed_members = sum(m['role'] in changed_roles for _,_,m in members)
        domains = {}
        for key,m in nodes.items():
            pitch = pitches[m['role']]
            domains[key] = ([(m['open_string'],0)] if m.get('open_string') is not None else
                [(s,f) for s,f in contacts if f > 0 and TUNING[s-1]+f == pitch
                    and ((s,f) in ordinary or m['marks'].get('tapping'))])
        group_strings = {}
        valid = True
        for group, keys in groups.items():
            options = set(range(1,9))
            for key in keys: options &= {s for s,f in domains[key]}
            if not options: valid=False; break
            group_strings[group] = sorted(options)
        if not valid: last_reason='linked_group_has_no_common_string'; continue
        # Retry contact choices inside a pitch assignment. Open strings are not
        # counted toward fretting span, but do occupy their actual string.
        for _ in range(6):
            chosen_strings = {g:rng.choice(ss) for g,ss in group_strings.items() if len(groups[g])>1}
            held, events, placements = {}, [], {}
            valid = True; previous_fret = None; motion=0; hand_positions=[]
            for ei,event in enumerate(template['events']):
                onset = F(event['onset_q']); held={s:value for s,value in held.items() if value[0] > onset}
                available = []
                for ni,m in enumerate(event['members']):
                    key=(ei,ni); group=find(key)
                    ds=[(s,f) for s,f in domains[key] if s not in held and (group not in chosen_strings or s==chosen_strings[group])]
                    rng.shuffle(ds)
                    if previous_fret is not None: ds.sort(key=lambda c:abs(c[1]-previous_fret) if c[1] else 0)
                    available.append(ds)
                selected=[]
                def coattack(i, used):
                    if i==len(available): return True
                    for contact in available[i]:
                        if contact[0] in used: continue
                        frets=[value[1] for value in held.values() if value[1] and not value[2]]
                        frets += [f for j,(s,f) in enumerate(selected+[contact]) if f and not event['members'][j]['marks'].get('tapping')]
                        # This is a declared MVP physical bound, not a musical
                        # definition; refusal exposes it to future controls.
                        if frets and max(frets)-min(frets)>6: continue
                        selected.append(contact)
                        if coattack(i+1,used|{contact[0]}): return True
                        selected.pop()
                    return False
                if not coattack(0,set()): valid=False;last_reason='held_string_or_coattack_contact_conflict';break
                out=[]
                for ni,(m,(string,fret)) in enumerate(zip(event['members'],selected)):
                    hold=F(m['hold_q']);held[string]=(onset+hold,fret,bool(m['marks'].get('tapping')));placements[ei,ni]=(string,fret)
                    out.append({'id':f'e{ei}:n{ni}','pitch':pitches[m['role']], 'string_number':string,'fret':fret,
                        'voice':m['voice'],'duration_q':str(hold),'marks':deepcopy(m['marks']),
                        'structural_role':m['role'],'relative_pitch_changed':m['role'] in changed_roles})
                fretted=[f for m,(s,f) in zip(event['members'],selected) if f and not m['marks'].get('tapping')]
                if fretted:
                    position=sum(fretted)/len(fretted)
                    if previous_fret is not None: motion+=abs(position-previous_fret)
                    previous_fret=position;hand_positions.extend(fretted)
                events.append({'onset_q':str(onset),'members':out})
            if not valid: continue
            for link in template['links']:
                a,b=tuple(link['origin']),tuple(link['destination']);x,y=placements[a],placements[b]
                direction=(y[1]>x[1])-(y[1]<x[1])
                if x[0]!=y[0] or direction!=link['direction']:
                    valid=False;last_reason='linked_technique_direction_conflict';break
            if valid:
                result={'events':events,'duration_q':template['duration_q'],
                    'measurement':{'relative_pitch_changed_attacks':len(changed_attacks),
                        'relative_pitch_changed_members':changed_members,
                        'attack_count':len(events),'member_count':len(members),
                        'source_relative_pitch_roles':template['source_relative_pitches'],
                        'generated_relative_pitch_roles':relative,
                        'whole_transposition':not changed_roles,'rhythm_and_member_holds_preserved':True,
                        'linked_techniques_checked':len(template['links']),
                        'fretting_hand_span':max(hand_positions)-min(hand_positions) if hand_positions else 0,
                        'fretting_hand_motion':motion,'physical_scope':'One observed contact window; opens excluded and explicit tapping separate'}}
                quality=(-min(len(changed_attacks),2),motion,result['measurement']['fretting_hand_span'])
                if best is None or quality<best[0]:best=(quality,result)
                successes+=1
                if successes>=8:return best[1],None
    return (best[1],None) if best else (None,last_reason)


def _realize(template,palettes,mode,rng):
    ordinary=set();tapped=set()
    for palette in palettes:
        roles=palette.get('contact_roles')
        if roles is None: ordinary.update(tuple(c) for c in palette['contacts'])
        else:
            ordinary.update(tuple(c) for name in ('core_contacts','extension_contacts') for c in roles.get(name,[]))
            tapped.update(tuple(c) for c in roles.get('tapped_contacts',[]))
    ordinary={c for c in ordinary if c[1]>0};tapped={c for c in tapped if c[1]>0}
    # Never flatten distant shapes into an un-timed bag of contacts. A short
    # unit has one coherent fretting-hand region; explicit tapping is separate.
    starts=sorted({f for s,f in ordinary}) or [0]
    windows=[];seen=set()
    for low in starts:
        window=frozenset(c for c in ordinary if low<=c[1]<=low+6)
        if window not in seen:windows.append(window);seen.add(window)
    windows.sort(key=lambda w:-len(w))
    reason='no_coherent_contact_window';best=None
    for window in windows:
        result,reason=_realize_window(template,palettes,mode,rng,set(window),tapped)
        if result:
            m=result['measurement'];quality=(-min(m['relative_pitch_changed_attacks'],2),m['fretting_hand_motion'],m['fretting_hand_span'])
            if best is None or quality<best[0]:best=(quality,result)
            if quality[0]==-2 and quality[1]==0:break
    return (best[1],None) if best else (None,reason)


def generate(request, pack):
    request=validate_request(request)
    if pack.get('schema')!='riff-pattern-pack/1': raise ValueError('Unsupported pattern pack')
    selected_artists=set(request['artists']); all_events=[]; sections=[]; refusals=[]; offset=F(0)
    for index,section in enumerate(request['sections']):
        seed=section.get('seed',stable_seed([request['seed'],index]));rng=random.Random(seed)
        length=F(section['length_q']);style=section['style'];focus=section['focus'];mode=request['mode']
        template_ids=pack['admissions']['rhythms'].get(style+':'+focus,[])
        palette_ids=pack['admissions']['palettes'].get(style+':'+mode,[])
        templates=[pack['templates'][i] for i in template_ids if F(pack['templates'][i]['duration_q'])<=length and
            any(s['artist'] in selected_artists and style in s['style_ids'] for s in pack['templates'][i]['support'])]
        palettes=[pack['palettes'][i] for i in palette_ids if pack['palettes'][i]['artist'] in selected_artists]
        outcome={'index':index,'seed':seed,'style':style,'focus':focus,'offset_q':str(offset),'length_q':str(length),
            'status':'no_choice','blocks':[],'candidate_counts':{'templates':len(templates),'palettes':len(palettes)},
            'refusals':[],'style_scope':pack['style_scope']}
        if not templates or not palettes:
            outcome['refusals'].append({'reason':'no_admitted_rhythm_templates' if not templates else 'no_mode_compatible_shape_palette'})
            sections.append(outcome);offset+=length;continue
        rng.shuffle(templates);rng.shuffle(palettes)
        durations=sorted({F(t['duration_q']) for t in templates},reverse=True)
        @lru_cache(None)
        def can_fill(remaining):
            if remaining==0:return True
            return any(d<=remaining and can_fill(remaining-d) for d in durations)
        if not can_fill(length):
            outcome['refusals'].append({'reason':'whole_units_cannot_fill_requested_length','unit_durations_q':list(map(str,durations))})
            sections.append(outcome);offset+=length;continue
        cursor=F(0);accepted={};attempted=set();failed_patterns=set();section_events=[]
        def realize_candidate(template):
            ident=template['id']
            if ident in accepted:return accepted[ident]
            if ident in failed_patterns:return None
            trial_palettes=palettes[:24];best=None
            for pi,palette in enumerate(trial_palettes):
                combos=[[palette]]
                if len(trial_palettes)>1:
                    other=trial_palettes[(pi+1)%len(trial_palettes)]
                    frets=[f for p in (palette,other) for s,f in p['contacts'] if f]
                    if frets and max(frets)-min(frets)<=6:combos.append([palette,other])
                for combo in combos:
                    key=(ident,tuple(p['id'] for p in combo))
                    if key in attempted:continue
                    attempted.add(key)
                    realized,reason=_realize(template,combo,mode,random.Random(stable_seed([seed,key])))
                    if realized:
                        found=(deepcopy(realized),[p['id'] for p in combo])
                        if best is None or realized['measurement']['relative_pitch_changed_attacks']>best[0]['measurement']['relative_pitch_changed_attacks']:best=found
                        if realized['measurement']['relative_pitch_changed_attacks']>=2:
                            accepted[ident]=best;return best
                    else:outcome['refusals'].append({'pattern_id':ident,'palette_ids':list(key[1]),'reason':reason})
            if best is not None:accepted[ident]=best;return best
            failed_patterns.add(ident);return None
        failed_states=set();planning_states=0
        def plan(remaining,changed,used):
            nonlocal planning_states
            if remaining==0:return [] if changed>=2 else None
            state=(remaining,min(changed,2))
            if state in failed_states:return None
            planning_states+=1
            options=[t for t in templates if t['id'] not in failed_patterns and F(t['duration_q'])<=remaining and can_fill(remaining-F(t['duration_q']))]
            options.sort(key=lambda t:(t['id'] in used,-F(t['duration_q'])))
            for template in options[:80]:
                choice=realize_candidate(template)
                if choice is None:continue
                realized,palette_used=choice
                tail=plan(remaining-F(template['duration_q']),changed+realized['measurement']['relative_pitch_changed_attacks'],used|{template['id']})
                if tail is not None:return [(template,realized,palette_used,template['id'] in used)]+tail
            failed_states.add(state);return None
        planned=plan(length,0,set())
        outcome['planning']={'visited_states':planning_states,'failed_states':len(failed_states),
            'method':'Backtracking over realizable whole units; novelty checked across the complete section'}
        for template,realized,palette_used,repeated in planned or []:
            block_index=len(outcome['blocks']);prefix=f's{index}:b{block_index}'
            for event in realized['events']:
                copied=deepcopy(event);copied['onset_q']=str(offset+cursor+F(event['onset_q']));copied['section_index']=index
                for m in copied['members']:m['id']=prefix+':'+m['id']
                section_events.append(copied)
            support=[s for s in template['support'] if s['artist'] in selected_artists and style in s['style_ids']]
            outcome['blocks'].append({'pattern_id':template['id'],'offset_q':str(cursor),'duration_q':template['duration_q'],
                'palette_ids':palette_used,'reference_support':support,'repeated_realization':repeated,
                'measurement':realized['measurement'],'source_meter':template.get('source_meter',[]),
                'local_construction':deepcopy(template.get('structural_profile',{})),
                'placement':'whole_unit_no_time_stretch_or_truncation'})
            cursor+=F(realized['duration_q'])
        if cursor==length:
            outcome['status']='generated';outcome['generated_length_q']=str(cursor)
            outcome['actual_focus']=focus_profile(section_events)
            outcome['distinct_pattern_count']=len({b['pattern_id'] for b in outcome['blocks']})
            outcome['repeated_blocks']=sum(b['repeated_realization'] for b in outcome['blocks'])
            outcome['measurement']={'relative_pitch_changed_attacks':sum(b['measurement']['relative_pitch_changed_attacks'] for b in outcome['blocks']),
                'whole_transposition':False,'novelty_scope':'Complete section; unchanged anchor and connective units may be retained'}
            all_events.extend(section_events)
        else:
            outcome['refusals'].append({'reason':'bounded_realization_or_section_novelty_search_exhausted','generated_prefix_q':str(cursor)})
        outcome['refusal_counts']=dict(Counter(r['reason'] for r in outcome['refusals']))
        refusals.extend({'section_index':index,**r} for r in outcome['refusals'])
        sections.append(outcome);offset+=length
    success=all(s['status']=='generated' for s in sections)
    refusals=[{'section_index':s['index'],**r} for s in sections for r in s['refusals']]
    return {'schema':'modular-riff-result/1','status':'generated' if success else 'no_choice',
        'request':deepcopy(request),'tempo':request['tempo'],'tuning':TUNING,'duration_q':str(offset),
        'meter':[4,4],'events':all_events if success else [],'sections':sections,'refusals':refusals,
        'provenance':{'pattern_pack_sha256':pack.get('content_sha256'),'source_library_sha256':pack.get('source_library_sha256'),
            'artist_policy':'strict inclusion filter only','style_scope':pack['style_scope']},
        'limits':['New relative pitch realizations, not a learned artist composer or listening acceptance',
            'Rhythms reused exactly; whole units placed in new 4/4 section frames with source meter retained as evidence',
            'Historical shape focus does not certify a new voicing; actual string occupancy and coattack span checked',
            'Each short unit uses a coherent fretting-hand window of at most six frets; explicit tapping is separate. Human execution remains unverified',
            'Search is bounded; failures do not prove musical impossibility',
            'Repeated realized blocks are reported; no claim of unlimited structural variety']}


def generate_json(request, pack):
    if isinstance(request,str):request=json.loads(request)
    if isinstance(pack,str):pack=json.loads(pack)
    return json.dumps(generate(request,pack),separators=(',',':'))
