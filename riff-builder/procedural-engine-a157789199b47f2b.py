"""Standalone deterministic whole-riff runtime; no filesystem or private inputs.

Public entrypoint: generate({artists, mode, seed}, pack). First refusals and
bounded search are explicit. Musical listening acceptance remains separate.
"""
from collections import Counter, defaultdict, deque
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
import random
import sys

TUNING=[64,59,55,50,45,40,35,28]
MODES={'Aeolian':[0,2,3,5,7,8,10],'Dorian':[0,2,3,5,7,9,10],
       'Ionian':[0,2,4,5,7,9,11],'Mixolydian':[0,2,4,5,7,9,10],
       'Lydian':[0,2,4,6,7,9,11],'Phrygian':[0,1,3,5,7,8,10]}
ARTISTS=['Invent Animate','Currents','ERRA']

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def stable_seed(value):return int(digest(value)[:16],16)

def instance_template(context, instance, relation=None):
    full=context['template'];indices=instance['event_indices'];lookup={ei:i for i,ei in enumerate(indices)}
    # Copy only the selected event/link slice. The previous whole-score copy
    # was immediately discarded for every candidate family's local template.
    local=deepcopy({k:v for k,v in full.items() if k not in ('events','links')})
    local['duration_q']=instance['length_q'];local['events']=[deepcopy(full['events'][ei]) for ei in indices]
    for e in local['events']:e['onset_q']=str(F(e['onset_q'])-F(instance['offset_q']))
    local['links']=[{**deepcopy(l),'origin':[lookup[l['origin'][0]],l['origin'][1]],
        'destination':[lookup[l['destination'][0]],l['destination'][1]]} for l in full['links']
        if l['origin'][0] in lookup and l['destination'][0] in lookup]
    if relation:
        for slot in relation['slot_map']:
            ei,ni=slot['slot'];local['events'][ei]['members'][ni]['role']=slot['instance_role']
    return local

def local_template(context,instance,relation=None):
    local=instance_template(context,instance,relation)
    released={tuple(r['event_slot']) for r in context['released_upper_opens']}
    for li,ei in enumerate(instance['event_indices']):
        for ni,m in enumerate(local['events'][li]['members']):
            m['optional_open']= (ei,ni) in released
    return local

def role_assignments(context,instances,locals,domain,mode,condition,seed,limit=32,fixed_roles=None,forced_domains=None,assignment_filter=None):
    members=defaultdict(list)
    for li,local in enumerate(locals):
        for ei,e in enumerate(local['events']):
            for ni,n in enumerate(e['members']):members[n['role']].append((n,(forced_domains or {}).get((ei,ni),domain) if li==0 else domain))
    roles=sorted(members);choices={};fixed={}
    for role,notes in members.items():
        role_values=None
        for n,n_domain in notes:
            contacts=n_domain['ordinary'] | n_domain['tapped'] if n['marks'].get('tapping') else n_domain['ordinary']
            values={TUNING[s-1]+f for s,f in contacts}
            if n.get('optional_open'):values.update(TUNING)
            if n.get('open_string') is not None:
                values={TUNING[n['open_string']-1]};fixed[role]=next(iter(values))
            bend=n['marks'].get('bend')
            targets=[] if not bend else [F(bend['points'][-1]['semitones']),max(F(p['semitones']) for p in bend['points'])]
            values={p for p in values if (p-4)%12 in MODES[mode] and context['role_register_bounds'][role][0]<=p<=context['role_register_bounds'][role][1]
                and all(t.denominator==1 and (p+int(t)-4)%12 in MODES[mode] for t in targets)}
            role_values=values if role_values is None else role_values&values
        if fixed_roles and role in fixed_roles:role_values &= {fixed_roles[role]}
        for instance,local in zip(instances,locals):
            for li,ei in enumerate(instance['event_indices']):
                for ni,n in enumerate(local['events'][li]['members']):
                    if n['role']==role and (ei,ni) in context.get('_slot_pitch_choices',{}):role_values &= context['_slot_pitch_choices'][ei,ni]
                    if n['role']==role and (ei,ni) in context.get('_fixed_slot_pitches',{}):role_values &= {context['_fixed_slot_pitches'][ei,ni]}
        if fixed_roles:
            role_values={p for p in role_values if all(p>v if role>r else p<v if role<r else p==v for r,v in fixed_roles.items())}
        if not role_values:return []
        choices[role]=sorted(role_values)
    indices={ei for i in instances for ei in i['event_indices']}
    pairs=defaultdict(list)
    if condition=='interval_function':
        for c in context['accent_constraints']:
            if indices.intersection(c['event_indices']):pairs[c['roles'][1]].append((c['roles'][0],c['semitones']))
    link_groups=[]
    for li,local in enumerate(locals):
        groups=[]
        for link in local.get('links',[]):
            keys={tuple(link['origin']),tuple(link['destination'])}
            for group in groups[:]:
                if group.intersection(keys):keys.update(group);groups.remove(group)
            groups.append(keys)
        for keys in groups:
            rows=[]
            for ei,ni in keys:
                n=local['events'][ei]['members'][ni]
                nd=(forced_domains or {}).get((ei,ni),domain) if li==0 else domain
                rows.append((n,nd))
            link_groups.append(rows)
    # Repeated HP/slide cells often repeat the same role/string constraint.
    # Build their pitch-to-string bitmasks once, preserving the exact predicate.
    string_groups=[];seen_groups=set()
    for group in link_groups:
        masks={}
        for n,nd in group:
            role=n['role'];contacts=nd['ordinary']|nd['tapped'] if n['marks'].get('tapping') else nd['ordinary']
            by_pitch={}
            for p in choices[role]:
                possible={s for s,f in contacts if TUNING[s-1]+f==p}
                if n.get('optional_open'):possible.update(s for s,t in enumerate(TUNING,1) if t==p)
                if n.get('open_string') is not None:possible={n['open_string']} if TUNING[n['open_string']-1]==p else set()
                by_pitch[p]=sum(1<<(s-1) for s in possible)
            if role in masks:by_pitch={p:bits&masks[role][p] for p,bits in by_pitch.items()}
            masks[role]=by_pitch
        signature=tuple((r,tuple(sorted(v.items()))) for r,v in sorted(masks.items()))
        if signature not in seen_groups:seen_groups.add(signature);string_groups.append(masks)
    def linked_choices_possible(chosen):
        for group in string_groups:
            strings=255
            for role,by_pitch in group.items():
                if role not in chosen:continue
                strings &= by_pitch[chosen[role]]
                if not strings:return False
        return True
    rng=random.Random(seed);out=[];chosen={};visits=0
    def walk(index):
        nonlocal visits
        visits+=1
        if visits>10000 or len(out)>=limit:return
        if index==len(roles):
            # Unused ordinal roles do not constrain this timed family.
            assignment=[0]*context['template']['role_count']
            for r,p in chosen.items():assignment[r]=p
            out.append(assignment);return
        role=roles[index];options=[p for p in choices[role] if not index or p>chosen[roles[index-1]]]
        if role in pairs:
            options=[p for p in options if all(p==chosen[earlier]+span for earlier,span in pairs[role])]
        rng.shuffle(options)
        for p in options:
            chosen[role]=p
            if linked_choices_possible(chosen) and (not assignment_filter or assignment_filter(chosen)):walk(index+1)
            if len(out)>=limit:break
        chosen.pop(role,None)
    walk(0)
    return out

def local_phrase_steps(program,instance):
    lookup={ei:li for li,ei in enumerate(instance['event_indices'])}
    return [{**r,'left_slots':[[lookup[ei],ni] for ei,ni in r['left_slots']],
        'right_slots':[[lookup[ei],ni] for ei,ni in r['right_slots']]}
        for r in program.get('seam_constraints',{}).get('within_phrase_movement',[])
        if r['instance_id']==instance['id'] and all(ei in lookup for ei,ni in r['left_slots']+r['right_slots'])]


def phrase_step_violations(program,events):
    if 'within_phrase_movement' not in program.get('seam_constraints',{}):return []
    owners=phrase_motion_owners(program)
    frames=[]
    for ei,event in enumerate(events):
        ss=[(ei,ni) for ni,n in enumerate(event['members']) if n['fret']>0 and not n['marks'].get('tapping')]
        if ss:frames.append((ei,ss))
    failures=[]
    for (ai,aa),(bi,bb) in zip(frames,frames[1:]):
        if owners[ai]!=owners[bi]:continue
        if any(link['kind']=='slide' and tuple(link['origin']) in aa and tuple(link['destination']) in bb for link in program['template'].get('links',[])):continue
        left=[events[ei]['members'][ni]['fret'] for ei,ni in aa];right=[events[ei]['members'][ni]['fret'] for ei,ni in bb]
        needed=max(0,max(right)-6-min(left),max(left)-6-min(right))
        if needed:failures.append({'instance_id':owners[bi],'left_slots':list(map(list,aa)),
            'right_slots':list(map(list,bb)),'necessary_box_shift_frets':needed,'local_continuity_limit':0})
    return failures


def phrase_motion_owners(program):
    instances=program['plan']['instances'];parents={i['id']:i['id'] for i in instances}
    def find(ident):
        while parents[ident]!=ident:ident=parents[ident]
        return ident
    for choice in phrase_motion_attachments(program):
        if choice['context'] is not None:parents[find(choice['child'])]=find(choice['context'])
    return {ei:find(i['id']) for i in instances for ei in i['event_indices']}


def phrase_motion_attachments(program):
    """Choose one execution context per dependent child, never both neighbors."""
    rows=[];instances=program['plan']['instances']
    for index,instance in enumerate(instances):
        if instance.get('role')!='accent' and instance.get('independent_phrase') is not False and instance.get('entry_independent') is not False:continue
        role=instance.get('accent_role')
        direction=1 if role=='header' else -1
        authority='declared_header_context' if role=='header' else 'declared_ending_context' if role in ('ending','fill') else 'generated_context_choice_source_ownership_unresolved'
        other=index+direction
        if not 0<=other<len(instances):
            other=index-direction
            authority='generated_context_choice_source_ownership_unresolved'
        context=instances[other]['id'] if 0<=other<len(instances) else None
        rows.append({'child':instance['id'],'context':context,
            'side':'previous' if other<index else 'next','authority':authority,
            'scope':'Execution continuity only; original phrase boundaries and musical relationship authority remain unchanged.'})
    # A header immediately followed by an ending can point at each other.
    # Such a dependent run is not a new independent body. Resolve one actual
    # neighboring body as an explicit generation choice, or retain no choice.
    order={i['id']:n for n,i in enumerate(instances)};parents={i['id']:i['id'] for i in instances}
    def find(ident):
        while parents[ident]!=ident:ident=parents[ident]
        return ident
    for row in rows:
        if row['context'] is not None:parents[find(row['child'])]=find(row['context'])
    groups=defaultdict(set)
    for ident in parents:groups[find(ident)].add(ident)
    bodies={i['id'] for i in instances if i.get('role')!='accent' and i.get('independent_phrase') is not False and i.get('entry_independent') is not False}
    for group in groups.values():
        if group & bodies:continue
        candidates=sorted(bodies,key=lambda ident:(min(abs(order[ident]-order[x]) for x in group),order[ident]))
        target=candidates[0] if candidates else None
        for row in rows:
            if row['child'] not in group:continue
            row['context']=target;row['side']=None if target is None else 'previous' if order[target]<order[row['child']] else 'next'
            row['authority']='generated_context_choice_orphan_dependent_run' if target is not None else 'unresolved_dependent_run_has_no_body'
    return rows


def realize(local,assignment,domain,seed,fixed=None,slot_domains=None,contact_links=(),contact_owners=None,movement_preferences=(),contact_preferences=(),diagnostics=None,phrase_steps=(),enforce_phrase_continuity=False,phrase_owners=None):
    """Contact DFS with explicit invariant slots; all link/hold checks remain."""
    fixed=fixed or {};nodes={(ei,ni):m for ei,e in enumerate(local['events']) for ni,m in enumerate(e['members'])}
    onsets=[F(event['onset_q']) for event in local['events']]
    written_ends={key:onsets[key[0]]+F(n['hold_q']) for key,n in nodes.items()}
    parent={k:k for k in nodes}
    def find(k):
        while parent[k]!=k:k=parent[k]
        return k
    for link in local['links']:parent[find(tuple(link['destination']))]=find(tuple(link['origin']))
    for a,b in contact_links:parent[find(tuple(b))]=find(tuple(a))
    groups=defaultdict(list)
    for k in nodes:groups[find(k)].append(k)
    choices={}
    for k,m in nodes.items():
        pitch=assignment[m['role']]
        selected_domain=(slot_domains or {}).get(k,domain)
        contacts=selected_domain['ordinary']|selected_domain['tapped'] if m['marks'].get('tapping') else selected_domain['ordinary']
        cs={c for c in contacts if TUNING[c[0]-1]+c[1]==pitch}
        if m.get('optional_open'):cs.update((s,0) for s,p in enumerate(TUNING,1) if p==pitch)
        if m.get('open_string') is not None:cs={(m['open_string'],0)} if TUNING[m['open_string']-1]==pitch else set()
        if k in fixed:cs &= {tuple(fixed[k])}
        if not cs:
            if diagnostics is not None:diagnostics['conflict_slots']=[list(k)]
            return None,'required_contact_unavailable'
        choices[k]=sorted(cs)
    allowed={g:set.intersection(*({s for s,f in choices[k]} for k in keys)) for g,keys in groups.items()}
    impossible=next((g for g,ss in allowed.items() if not ss),None)
    if impossible is not None:
        if diagnostics is not None:diagnostics['conflict_slots']=[list(k) for k in groups[impossible]]
        return None,'linked_group_has_no_common_string'
    rng=random.Random(seed)
    for k in choices:rng.shuffle(choices[k])
    ordered=list(nodes);placed={};group_string={};visits=0;step_conflicts=[]
    steps_at=defaultdict(list)
    for rule in phrase_steps:
        if rule.get('explicit_slide'):continue
        for slot in rule['right_slots']:steps_at[tuple(slot)].append(rule)
    def search(index):
        nonlocal visits
        visits+=1
        if visits>30000:return False
        if index==len(ordered):return True
        key=ordered[index];ei,ni=key;m=nodes[key];g=find(key);at=onsets[ei]
        active=[(k,c) for k,c in placed.items() if written_ends[k]>at]
        previous=[c[1] for k,c in placed.items() if c[1] and not nodes[k]['marks'].get('tapping')
            and (not contact_owners or contact_owners[k]==contact_owners[key])]
        cs=choices[key][:]
        if previous:cs.sort(key=lambda c:abs(c[1]-previous[-1]) if c[1] else 0)
        def travel_cost(contact):
            cost=F(0)
            for rule in movement_preferences:
                right=list(map(tuple,rule['right_slots']));left=list(map(tuple,rule['left_slots']))
                if key not in right or not all(k in placed for k in left):continue
                lf=[placed[k][1] for k in left if placed[k][1]]
                rf=[contact[1] if k==key else placed[k][1] for k in right if k==key or k in placed]
                if lf and rf:
                    change=abs(F(sum(rf),len(rf))-F(sum(lf),len(lf)))
                    cost+=max(F(0),change-F(rule['source_center_shift_frets']))/F(rule.get('travel_time_seconds',rule['attack_gap_q']))
            for rule in contact_preferences:
                left,right=tuple(rule['left_slot']),tuple(rule['right_slot'])
                if key==right and left in placed and assignment[nodes[left]['role']]==assignment[m['role']] and placed[left]!=contact:cost+=1
            return cost
        if movement_preferences or contact_preferences:cs.sort(key=travel_cost)
        for s,f in cs:
            if s not in allowed[g] or (g in group_string and group_string[g]!=s):continue
            if any(c[0]==s for k,c in active):continue
            frets=[c[1] for k,c in active if c[1] and not nodes[k]['marks'].get('tapping')]
            if f and not m['marks'].get('tapping'):frets.append(f)
            if frets and max(frets)-min(frets)>6:continue
            attack_complete=index+1==len(ordered) or ordered[index+1][0]!=ei
            if enforce_phrase_continuity and attack_complete:
                prior=[k for k,c in placed.items() if onsets[k[0]]<at and c[1]>0 and not nodes[k]['marks'].get('tapping')
                    and (phrase_owners is None or phrase_owners[k[0]]==phrase_owners[ei])]
                if prior:
                    latest=max(onsets[k[0]] for k in prior);left_slots=[k for k in prior if onsets[k[0]]==latest]
                    right_slots=[k for k,c in placed.items() if k[0]==ei and c[1]>0 and not nodes[k]['marks'].get('tapping')]
                    if f>0 and not m['marks'].get('tapping'):right_slots.append(key)
                    slide=any(link['kind']=='slide' and tuple(link['origin']) in left_slots and tuple(link['destination']) in right_slots for link in local['links'])
                    left=[placed[k][1] for k in left_slots];right=[placed[k][1] if k!=key else f for k in right_slots]
                    if right and not slide and max(0,max(right)-6-min(left),max(left)-6-min(right)):
                        step_conflicts[:]=left_slots+right_slots;continue
            step_bad=False
            for rule in steps_at.get(key,[]):
                left_slots=list(map(tuple,rule['left_slots']));right_slots=list(map(tuple,rule['right_slots']))
                if not all(k in placed for k in left_slots):continue
                left=[placed[k][1] for k in left_slots if placed[k][1]>0 and not nodes[k]['marks'].get('tapping')]
                right=[f if k==key else placed[k][1] for k in right_slots if k==key or k in placed]
                right=[fret for fret in right if fret>0]
                if not left or not right:continue
                span=rule['box_span_frets'];needed=max(0,max(right)-span-min(left),max(left)-span-min(right))
                if needed>rule['maximum_box_relocation_frets']:
                    step_bad=True;step_conflicts[:]=left_slots+right_slots;break
            if step_bad:continue
            bad=False
            for link in local['links']:
                a,b=tuple(link['origin']),tuple(link['destination'])
                if key==b and a in placed:
                    if placed[a][0]!=s or (f>placed[a][1])-(f<placed[a][1])!=link['direction']:bad=True;break
            if bad:continue
            owned=g not in group_string
            group_string[g]=s;placed[key]=(s,f)
            if search(index+1):return True
            del placed[key]
            if owned:del group_string[g]
        return False
    old_limit=sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(max(old_limit,len(ordered)*2+100))
        solved=search(0)
    finally:sys.setrecursionlimit(old_limit)
    if not solved:
        if step_conflicts and diagnostics is not None:diagnostics['conflict_slots']=[list(k) for k in step_conflicts]
        return None,'bounded_contact_search_or_intra_phrase_conflict' if step_conflicts else 'bounded_contact_search_or_hold_conflict'
    events=[]
    for ei,e in enumerate(local['events']):
        notes=[]
        for ni,m in enumerate(e['members']):
            s,f=placed[ei,ni]
            notes.append({'id':f'e{ei}:n{ni}','pitch':assignment[m['role']],'string_number':s,'fret':f,
                'voice':m['voice'],'duration_q':m['hold_q'],'marks':deepcopy(m['marks']),'structural_role':m['role']})
        events.append({'onset_q':e['onset_q'],'members':notes})
    return {'events':events,'duration_q':local['duration_q'],'search_visits':visits},None

def invariant_contacts(parent_result,local,assignment):
    return {(ei,ni):(a['string_number'],a['fret']) for ei,(e,p) in enumerate(zip(local['events'],parent_result['events']))
        for ni,(m,a) in enumerate(zip(e['members'],p['members'])) if assignment[m['role']]==a['pitch']}

def choose_family(context,instance,mode,condition,seed,available,excluded_assignments=(),choice_offset=0,fixed_roles=None,forced_domains=None,hierarchical=False,assignment_filter=None,domain_cost=None,execution_cost=None,enumeration_cache=None):
    # Parent correspondence may supersede an old same-motif flat edge. An
    # explicit empty operative edge list must keep those pitch owners separate.
    if hierarchical or '_operative_flat_relations' in context:
        dependents={r['to'] for r in context.get('_operative_flat_relations',[]) if r['from']==instance['id']}
        family=[instance]+[i for i in context['plan']['instances'] if i['id'] in dependents]
    else:family=[i for i in context['plan']['instances'] if i['motif_id']==instance['motif_id']]
    locals=[local_template(context,i) for i in family]
    used_roles=sorted({n['role'] for local in locals for e in local['events'] for n in e['members']})
    uses_tapping=any(n['marks'].get('tapping') for local in locals for event in local['events'] for n in event['members'])
    own=local_template(context,instance);failures=Counter()
    candidates=available[:];random.Random(seed).shuffle(candidates)
    # Prefer one real observed context when it can carry the complete family.
    # Constructed windows are explicitly separate candidates, never fake shapes.
    candidates.sort(key=lambda d:d['kind']!='observed_palette_modal_subset')
    if domain_cost:candidates.sort(key=domain_cost)
    if all(n.get('open_string') is not None for l in locals for e in l['events'] for n in e['members']):
        candidates=[{'id':'open-only','kind':'open_string_only','ordinary':set(),'tapped':set(),'palettes':[]}]
    alternatives=[];enumeration_cache={} if enumeration_cache is None else enumeration_cache
    for candidate_index,candidate_domain in enumerate(candidates):
        domain={**candidate_domain,'tapped':candidate_domain['tapped'] if uses_tapping else set()}
        domain['palettes']=[p for p in domain['palettes'] if
            any(tuple(c) in domain['ordinary'] for name in ('ordinary_contacts','extension_contacts') for c in p.get(name,[]))
            or any(tuple(c) in domain['tapped'] for c in p.get('tapped_contacts',[]))]
        if candidate_index not in enumeration_cache:
            enumeration_cache[candidate_index]={'assignments':role_assignments(context,family,locals,domain,mode,condition,seed,fixed_roles=fixed_roles,forced_domains=forced_domains,assignment_filter=assignment_filter),'evaluations':{}}
        candidate=enumeration_cache[candidate_index]
        for assignment_index,assignment in enumerate(candidate['assignments']):
            if assignment_filter and not assignment_filter(assignment):continue
            signature=tuple((role,assignment[role]) for role in used_roles)
            if signature in excluded_assignments:continue
            if assignment_index not in candidate['evaluations']:
                result,reason=realize(own,assignment,domain,seed,slot_domains=forced_domains,phrase_steps=local_phrase_steps(context,instance),enforce_phrase_continuity='within_phrase_movement' in context.get('seam_constraints',{}))
                if result:
                    for local,family_instance in (list(zip(locals[1:],family[1:])) if hierarchical else list(zip(locals,family))):
                        fixed=invariant_contacts(result,local,assignment)
                        variant,reason=realize(local,assignment,domain,seed,fixed,phrase_steps=local_phrase_steps(context,family_instance),enforce_phrase_continuity='within_phrase_movement' in context.get('seam_constraints',{}))
                        if not variant:break
                candidate['evaluations'][assignment_index]=(result,reason,execution_cost(result) if result and not reason and execution_cost else 0)
            result,reason,cost=candidate['evaluations'][assignment_index]
            if reason:failures[reason]+=1;continue
            if result:
                if cost:
                    alternatives.append((cost,assignment,domain,result));continue
                if choice_offset:choice_offset-=1;continue
                return assignment,domain,result,dict(failures)
    if alternatives:
        alternatives.sort(key=lambda row:row[0])
        if choice_offset<len(alternatives):
            cost,assignment,domain,result=alternatives[choice_offset]
            return assignment,domain,result,dict(failures)
    return None,None,None,dict(failures)


def seam_pitch_check(program, events, proposed=None):
    proposed=proposed or {}
    def value(slot):
        key=tuple(slot)
        return proposed[key] if key in proposed else events[key[0]]['members'][key[1]]['pitch'] if events[key[0]] is not None else None
    rules=program.get('seam_constraints',{})
    for rule in rules.get('pitch_equalities',[]):
        values=[value(s) for s in rule['left_slots']+rule['right_slots']]
        known=[p for p in values if p is not None]
        if known and len(set(known))>1:return False
    for rule in rules.get('register_relations',[]):
        lows=[value(s) for s in rule['lower_slots']];highs=[value(s) for s in rule['upper_slots']]
        known_lows=[p for p in lows if p is not None];known_highs=[p for p in highs if p is not None]
        if known_lows and known_highs and min(known_highs)-max(known_lows)<rule['min_semitones']:return False
        if all(p is not None for p in lows+highs):
            if min(highs)-max(lows)<rule['min_semitones']:return False
            if sum(highs)*len(lows)-sum(lows)*len(highs)<rule.get('minimum_center_separation_semitones',0)*len(lows)*len(highs):return False
    return True


def movement_seconds(program,rule):
    free=F(rule.get('free_reposition_gap_q','0'))
    span=free if free>0 else F(rule['attack_gap_q'])
    end=F(program['template']['events'][rule['right_slots'][0][0]]['onset_q']);start=max(F(0),end-span)
    points=program['timing']['tempo_map'];seconds=F(0)
    for i,p in enumerate(points):
        a=max(start,F(p['onset_q']));b=min(end,F(points[i+1]['onset_q']) if i+1<len(points) else end)
        if b>a:seconds+=(b-a)*60/F(p['quarter_bpm'])
    return seconds or span # source timing is required; zero onset has no travel interval


def seam_selection(program,instance,events,slot_domains,parent_membership=None):
    indices=set(instance['event_indices']);fixed={};movements=[];prior=[]
    aliases=program.get('_slot_aliases',{});known_aliases={}
    for (ei,ni),alias in aliases.items():
        if events[ei] is None:continue
        value=events[ei]['members'][ni]['pitch']
        if alias in known_aliases and known_aliases[alias]!=value:return None,None,None
        known_aliases[alias]=value
    for ei in indices:
        for ni,n in enumerate(program['template']['events'][ei]['members']):
            alias=aliases.get((ei,ni))
            if alias in known_aliases:
                value=known_aliases[alias]
                if n['role'] in fixed and fixed[n['role']]!=value:return None,None,None
                fixed[n['role']]=value
    for rule in program.get('seam_constraints',{}).get('pitch_equalities',[]):
        slots=rule['left_slots']+rule['right_slots']
        known=[events[ei]['members'][ni]['pitch'] for ei,ni in slots if events[ei] is not None]
        if not known:continue
        if len(set(known))!=1:return None,None,None
        for ei,ni in slots:
            if ei in indices:
                role=program['template']['events'][ei]['members'][ni]['role']
                if role in fixed and fixed[role]!=known[0]:return None,None,None
                fixed[role]=known[0]
    for rule in program.get('seam_constraints',{}).get('movement_preferences',[]):
        if any(ei in indices for ei,ni in rule['right_slots']) and all(events[ei] is not None for ei,ni in rule['left_slots']):
            frets=[events[ei]['members'][ni]['fret'] for ei,ni in rule['left_slots'] if events[ei]['members'][ni]['fret']]
            if frets:movements.append((rule,F(sum(frets),len(frets))))
    guidance=program.get('_movement_guidance',{}).get(instance['id'],[])
    contact_guidance=program.get('_contact_guidance',{}).get(instance['id'],[])
    for rule in program.get('seam_constraints',{}).get('register_relations',[]):
        slots=rule['lower_slots']+rule['upper_slots']
        if any(ei in indices for ei,ni in slots):prior.extend((ei,ni,events[ei]['members'][ni]['pitch']) for ei,ni in slots if events[ei] is not None)
    own_roles={n['role'] for ei in indices for n in program['template']['events'][ei]['members']}
    selected_groups={(parent_membership or {})[ei] for ei in indices if ei in (parent_membership or {})}
    assigned_indices=indices|{ei for ei,group in (parent_membership or {}).items() if group in selected_groups}
    role_aliases=defaultdict(set)
    for ei in assigned_indices:
        for ni,n in enumerate(program['template']['events'][ei]['members']):role_aliases[n['role']].add(aliases.get((ei,ni),(ei,ni)))
    equality_aliases=[list({aliases.get(tuple(s),tuple(s)) for s in r['left_slots']+r['right_slots']})
        for r in program.get('seam_constraints',{}).get('pitch_equalities',[])]
    register_aliases=[([aliases.get(tuple(s),tuple(s)) for s in r['lower_slots']],
        [aliases.get(tuple(s),tuple(s)) for s in r['upper_slots']],r['min_semitones'],r.get('minimum_center_separation_semitones',0))
        for r in program.get('seam_constraints',{}).get('register_relations',[])]
    base_values=dict(known_aliases)
    for ei,event in enumerate(events):
        if event is not None:
            for ni,n in enumerate(event['members']):base_values.setdefault(aliases.get((ei,ni),(ei,ni)),n['pitch'])
    # Reserve feasible modal space for roles introduced only by a later child.
    # Initial global bounds alone cannot detect two missing roles squeezed
    # between concrete adjacent pitches chosen by an earlier parent instance.
    ordered_chains=[];seen_chains=set();pitch_domains={}
    for slot,values in program.get('_slot_pitch_choices',{}).items():pitch_domains[aliases.get(slot,slot)]=sorted(values)
    scopes=[i['event_indices'] for i in program['plan']['instances']]
    by_ident={i['id']:i for i in program['plan']['instances']}
    for relation in program.get('_operative_flat_relations',[]):scopes.append(by_ident[relation['from']]['event_indices']+by_ident[relation['to']]['event_indices'])
    macro_scopes=defaultdict(list)
    for ei,group in (parent_membership or {}).items():macro_scopes[group].append(ei)
    scopes.extend(macro_scopes.values())
    for scope in scopes:
        roles={n['role']:aliases.get((ei,ni),(ei,ni)) for ei in scope for ni,n in enumerate(program['template']['events'][ei]['members'])}
        chain=tuple(roles[r] for r in sorted(roles))
        if chain not in seen_chains and all(a in pitch_domains for a in chain):seen_chains.add(chain);ordered_chains.append(chain)
    assignment_checks={}
    def assignment_filter(assignment):
        key=('partial',tuple(sorted(assignment.items()))) if isinstance(assignment,dict) else ('complete',tuple(assignment))
        if key not in assignment_checks:assignment_checks[key]=check_assignment(assignment)
        return assignment_checks[key]
    def check_assignment(assignment):
        values=dict(base_values);partial=isinstance(assignment,dict)
        for role,related in role_aliases.items():
            if partial and role not in assignment:continue
            pitch=assignment[role]
            if not partial and not pitch and role not in own_roles:continue
            for alias in related:
                if alias in values and values[alias]!=pitch:return False
                values[alias]=pitch
        for group in equality_aliases:
            known=[values[a] for a in group if a in values]
            if known and min(known)!=max(known):return False
        for lower,upper,separation,center in register_aliases:
            lows=[values[a] for a in lower if a in values];highs=[values[a] for a in upper if a in values]
            if lows and highs and min(highs)-max(lows)<separation:return False
            if len(lows)==len(lower) and len(highs)==len(upper) and sum(highs)*len(lows)-sum(lows)*len(highs)<center*len(lows)*len(highs):return False
        for chain in ordered_chains:
            previous=-1
            for alias in chain:
                if alias in values:
                    pitch=values[alias]
                    if pitch<=previous or pitch not in pitch_domains[alias]:return False
                else:
                    pitch=next((p for p in pitch_domains[alias] if p>previous),None)
                    if pitch is None:return False
                previous=pitch
        return True
    # These source/context quantities are invariant throughout this family's
    # candidate enumeration. Keep exact fractions and the original cost order.
    movement_costs=[(rule,old,F(rule['source_center_shift_frets']),movement_seconds(program,rule)) for rule,old in movements]
    guidance_costs=[(F(g['neighbor_center']),F(g['allowed_center_shift']),F(g['time_seconds'])) for g in guidance]
    def domain_cost(domain):
        frets=[f for s,f in domain['ordinary']]
        if not frets:return (0,domain['kind']!='observed_palette_modal_subset')
        center=F(sum(frets),len(frets));cost=F(0)
        for rule,old,allowed,seconds in movement_costs:
            # Source-relative excess travel per available quarter. A long move
            # seen in the source is allowed; unmotivated extra travel costs more.
            excess=max(F(0),abs(center-old)-allowed)
            cost+=excess/seconds
        for neighbor,allowed,seconds in guidance_costs:
            cost+=max(F(0),abs(center-neighbor)-allowed)/seconds
        for preferred in contact_guidance:
            if tuple(preferred['contact']) not in domain['ordinary']|domain['tapped']:cost+=1
        return (cost,domain['kind']!='observed_palette_modal_subset')
    local_lookup={ei:li for li,ei in enumerate(instance['event_indices'])}
    adjustable={aliases.get((ei,ni),(ei,ni)) for ei in indices for ni,n in enumerate(program['template']['events'][ei]['members'])
        if aliases.get((ei,ni),(ei,ni)) not in known_aliases}
    register_costs=[]
    for rule in program.get('seam_constraints',{}).get('register_relations',[]):
        band=rule.get('preferred_center_separation_band')
        if not band:continue
        low=[aliases.get(tuple(s),tuple(s)) for s in rule['lower_slots']]
        high=[aliases.get(tuple(s),tuple(s)) for s in rule['upper_slots']]
        if any(a in adjustable for a in low+high):register_costs.append((low,high,F(band[0]),F(band[1])))
    def execution_cost(result):
        cost=F(0)
        for preferred in contact_guidance:
            ei,ni=preferred['slot']
            n=result['events'][local_lookup[ei]]['members'][ni]
            if n['pitch']==preferred['pitch'] and [n['string_number'],n['fret']]!=preferred['contact']:cost+=1
        for rule,old,allowed,seconds in movement_costs:
            right=[result['events'][local_lookup[ei]]['members'][ni]['fret'] for ei,ni in rule['right_slots'] if ei in local_lookup]
            if right:
                center=F(sum(right),len(right));cost+=max(F(0),abs(center-old)-allowed)/seconds
        played=[n['fret'] for event in result['events'] for n in event['members'] if n['fret'] and not n['marks'].get('tapping')]
        if played:
            center=F(sum(played),len(played))
            for neighbor,allowed,seconds in guidance_costs:cost+=max(F(0),abs(center-neighbor)-allowed)/seconds
        for rule in program.get('seam_constraints',{}).get('contact_preferences',[]):
            ai,an=rule['left_slot'];bi,bn=rule['right_slot']
            if bi in local_lookup and events[ai] is not None:
                x=events[ai]['members'][an];y=result['events'][local_lookup[bi]]['members'][bn]
                if x['pitch']==y['pitch'] and (x['string_number'],x['fret'])!=(y['string_number'],y['fret']):cost+=1
        values=dict(known_aliases)
        for ei,li in local_lookup.items():
            for ni,n in enumerate(result['events'][li]['members']):values[aliases.get((ei,ni),(ei,ni))]=n['pitch']
        for lower,upper,band_low,band_high in register_costs:
            low=[values.get(a) for a in lower]
            high=[values.get(a) for a in upper]
            if all(p is not None for p in low+high):
                distance=F(sum(high),len(high))-F(sum(low),len(low))
                cost+=max(F(0),band_low-distance,distance-band_high)/12
        return cost
    # Cache only values that can change this family's feasible choices or cost.
    # Unrelated earlier notes do not invalidate an exhausted candidate search.
    assigned_aliases=set().union(*role_aliases.values()) if role_aliases else set()
    dependent_aliases=set(assigned_aliases)
    for group in equality_aliases:
        if assigned_aliases.intersection(group):dependent_aliases.update(group)
    for low,high,_,_ in register_aliases:
        if assigned_aliases.intersection(low+high):dependent_aliases.update(low+high)
    for chain in ordered_chains:
        if assigned_aliases.intersection(chain):dependent_aliases.update(chain)
    contact_context=[]
    for rule in program.get('seam_constraints',{}).get('contact_preferences',[]):
        ai,an=rule['left_slot'];bi,bn=rule['right_slot']
        if bi in indices and events[ai] is not None:
            n=events[ai]['members'][an];contact_context.append((ai,an,n['pitch'],n['string_number'],n['fret']))
    signature=(tuple(sorted(fixed.items())),tuple(sorted(prior)),tuple((r['join_id'],str(c)) for r,c in movements),
        tuple(sorted((a,v) for a,v in known_aliases.items() if a in dependent_aliases)),digest(guidance),
        tuple(contact_context),assignment_filter({}))
    if contact_guidance:signature=signature+(digest(contact_guidance),)
    return fixed,assignment_filter,(domain_cost if movements or guidance or contact_guidance else None,signature,execution_cost if movements or guidance or contact_guidance or program.get('seam_constraints',{}).get('register_relations') else None)


def hierarchy_runtime(plan, relations):
    # Internal vocabulary of a witnessed source unit is intrinsic to that unit.
    # Removing its outgoing return edge must not change the already chosen
    # source idea; only destination/descendant constraints disappear.
    groups=[];exact={}
    for relation in plan.get('hierarchy',{}).get('relations',[]):
        members=set(relation['from_events'])
        for old in groups[:]:
            if old.intersection(members):members.update(old);groups.remove(old)
        groups.append(members)
    for relation in relations:
        members=set(relation['from_events']+relation['to_events'])
        for old in groups[:]:
            if old.intersection(members):members.update(old);groups.remove(old)
        groups.append(members)
        for pair in relation['slot_pairs']:
            if pair['preserve_execution']:exact[tuple(pair['to'])]=tuple(pair['from'])
    membership={ei:gi for gi,g in enumerate(groups) for ei in g}
    return membership,exact


def operative_parent_roles(program,relations):
    changes={}
    for relation in relations:
        for pair in relation['slot_pairs']:
            if 'to_role' not in pair:continue
            slot=tuple(pair['to']);role=pair['to_role']
            if not isinstance(role,int) or not 0<=role<program['template']['role_count']:raise ValueError('Invalid directed parent role')
            if slot in changes and changes[slot]!=role:raise ValueError('Conflicting directed parent roles')
            changes[slot]=role
    if all(program['template']['events'][ei]['members'][ni]['role']==r for (ei,ni),r in changes.items()):return program
    altered={**program,'template':deepcopy(program['template'])}
    for (ei,ni),role in changes.items():altered['template']['events'][ei]['members'][ni]['role']=role
    return altered


def relational_pitch_choices(program,mode,relations,hierarchy):
    """Propagate future role-order space through actual equality relationships.

    This is not global equality by source pitch. Only local motif vocabularies,
    operative returns and admitted seam common tones share a variable.
    """
    nodes={(ei,ni):n for ei,event in enumerate(program['template']['events']) for ni,n in enumerate(event['members'])}
    parent={k:k for k in nodes}
    def find(k):
        while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
        return k
    def union(keys):
        keys=list(keys)
        if keys:
            for k in keys[1:]:parent[find(k)]=find(keys[0])
    instances={i['id']:i for i in program['plan']['instances']};role_groups=[]
    for instance in instances.values():
        roles=defaultdict(list)
        for ei in instance['event_indices']:
            for ni,n in enumerate(program['template']['events'][ei]['members']):roles[n['role']].append((ei,ni))
        role_groups.append(roles)
    for relation in relations:
        roles=defaultdict(list)
        for ident in (relation['from'],relation['to']):
            for ei in instances[ident]['event_indices']:
                for ni,n in enumerate(program['template']['events'][ei]['members']):roles[n['role']].append((ei,ni))
        role_groups.append(roles)
    membership,_=hierarchy_runtime(program['plan'],hierarchy);macro=defaultdict(lambda:defaultdict(list))
    for ei,group in membership.items():
        for ni,n in enumerate(program['template']['events'][ei]['members']):macro[group][n['role']].append((ei,ni))
    role_groups.extend(macro.values())
    for roles in role_groups:
        for keys in roles.values():union(keys)
    for equality in program.get('seam_constraints',{}).get('pitch_equalities',[]):union(map(tuple,equality['left_slots']+equality['right_slots']))
    values={};edges=set()
    released={tuple(r['event_slot']) for r in program.get('released_upper_opens',[])}
    for key,n in nodes.items():
        lo,hi=program['role_register_bounds'][n['role']]
        choices={p for p in range(max(28,lo),min(88,hi)+1) if (p-4)%12 in MODES[mode]}
        if n.get('open_string') is not None:choices &= {TUNING[n['open_string']-1]}
        else:
            occupied={m['open_string'] for ni,m in enumerate(program['template']['events'][key[0]]['members']) if ni!=key[1] and m.get('open_string') is not None}
            minimum=0 if key in released else 1
            choices &= {pitch+fret for s,pitch in enumerate(TUNING,1) if s not in occupied for fret in range(minimum,25)}
        root=find(key);values[root]=choices if root not in values else values[root]&choices
    for roles in role_groups:
        ordered=sorted(roles)
        for a,b in zip(ordered,ordered[1:]):edges.add((find(roles[a][0]),find(roles[b][0]),1))
    for rule in program.get('seam_constraints',{}).get('register_relations',[]):
        for a in rule['lower_slots']:
            for b in rule['upper_slots']:
                span=rule.get('minimum_center_separation_semitones',1) if len(rule['lower_slots'])==len(rule['upper_slots'])==1 else rule['min_semitones']
                edges.add((find(tuple(a)),find(tuple(b)),span))
    changed=True
    while changed:
        changed=False
        for a,b,span in edges:
            if a==b or not values[a] or not values[b]:return {k:set() for k in nodes},{k:find(k) for k in nodes}
            left={p for p in values[a] if p+span<=max(values[b])};right={p for p in values[b] if p>=min(values[a])+span}
            if left!=values[a] or right!=values[b]:values[a]=left;values[b]=right;changed=True
    return {k:values[find(k)] for k in nodes},{k:find(k) for k in nodes}

def shape_usage(domain,mode,result):
    usage=_shape_usage(domain['palettes'],mode,domain['ordinary'],domain['tapped'],result['events'])
    usage.update(domain_id=domain['id'],context_origin=domain['kind'],
        context_chosen_before_realization=True,
        interpretation='An observed modal contact subset' if domain['kind']=='observed_palette_modal_subset' else
        'A new local contact domain assembled from observed contacts; not one source shape' if domain['kind'].startswith('constructed') else 'No fretted shape')
    return usage

def transitions(context,score):
    out=[];instances=context['plan']['instances']
    for a,b in zip(instances,instances[1:]):
        ea=score['events'][a['event_indices'][-1]];eb=score['events'][b['event_indices'][0]]
        left=[(n['string_number'],n['fret']) for n in ea['members'] if n['fret'] and not n['marks'].get('tapping')]
        right=[(n['string_number'],n['fret']) for n in eb['members'] if n['fret'] and not n['marks'].get('tapping')]
        out.append({'from':a['id'],'to':b['id'],'q':b['offset_q'],'previous_final_contacts':left,'next_initial_contacts':right,
            'attack_gap_q':str(F(eb['onset_q'])-F(ea['onset_q'])),
            'hand_mean_fret_change':abs(sum(f for s,f in right)/len(right)-sum(f for s,f in left)/len(left)) if left and right else None,
            'crossing_technique_links':sum(F(context['template']['events'][l['origin'][0]]['onset_q'])<F(b['offset_q'])<=F(context['template']['events'][l['destination'][0]]['onset_q']) for l in context['template']['links']),
            'execution_speed_accepted':False})
    return out


def whole_movement_cost(program,score):
    rows=[];total=F(0)
    for rule in program.get('seam_constraints',{}).get('movement_preferences',[]):
        left=[score['events'][ei]['members'][ni]['fret'] for ei,ni in rule['left_slots'] if score['events'][ei]['members'][ni]['fret']]
        right=[score['events'][ei]['members'][ni]['fret'] for ei,ni in rule['right_slots'] if score['events'][ei]['members'][ni]['fret']]
        if not left or not right:continue # opens do not pin the fretting hand
        span=rule['source_box_span_limit']
        # Compare necessary hand-box relocation, not the distance between two
        # fingers inside a usable local shape. This is a source-relative soft
        # objective, never a universal physical speed or fret-jump prohibition.
        needed=max(0,max(right)-span-min(left),max(left)-span-min(right))
        baseline=rule.get('source_minimum_box_shift_frets')
        if baseline is None:baseline=F(rule['source_center_shift_frets'])
        excess=max(F(0),F(needed)-F(baseline));cost=excess/movement_seconds(program,rule)
        if cost:rows.append({'join_id':rule['join_id'],'from':rule['from'],'to':rule['to'],
            'necessary_box_shift_frets':needed,'source_reference_shift_frets':str(baseline),
            'excess_frets':str(excess),'cost':str(cost)})
        total+=cost
    return total,sorted(rows,key=lambda r:F(r['cost']),reverse=True)


def domains(palettes,mode):
    values=[];seen=set();all_regular=set();all_tapped=set()
    for palette in palettes:
        regular={tuple(c) for name in ('ordinary_contacts','extension_contacts') for c in palette.get(name,[])
            if c[1]>0 and (TUNING[c[0]-1]+c[1]-4)%12 in MODES[mode]}
        tapped={tuple(c) for c in palette.get('tapped_contacts',[])
            if c[1]>0 and (TUNING[c[0]-1]+c[1]-4)%12 in MODES[mode]}
        all_regular.update(regular);all_tapped.update(tapped)
        key=(tuple(sorted(regular)),tuple(sorted(tapped)))
        if key in seen:continue
        seen.add(key)
        values.append({'id':palette['id'],'kind':'observed_palette_modal_subset','ordinary':regular,
            'tapped':tapped,'palettes':[palette]})
    seen=set()
    for low in sorted({f for s,f in all_regular}):
        window=frozenset(c for c in all_regular if low<=c[1]<=low+6)
        if window in seen:continue
        seen.add(window)
        supported=[p for p in palettes if any(tuple(c) in window for name in ('ordinary_contacts','extension_contacts') for c in p.get(name,[]))
            or any(tuple(c) in all_tapped for c in p.get('tapped_contacts',[]))]
        values.append({'id':f'constructed-{mode}-{low}-{digest(sorted(window))[:12]}',
            'kind':'constructed_local_domain_from_observed_contacts','ordinary':set(window),
            'tapped':all_tapped,'palettes':supported,'fret_window':[low,low+6]})
    return values


def _shape_usage(palettes,mode,ordinary,tapped,events):
    # Index each palette once, retaining palette and role order exactly.
    # Rebuilding every contact set for every highlighted fret was quadratic.
    contact_sources=defaultdict(list)
    for p in palettes:
        roles_by_contact=defaultdict(list)
        for field,role in [('ordinary_contacts','core'),('extension_contacts','extension'),('tapped_contacts','tapped')]:
            for c in {tuple(x) for x in p.get(field,[])}:roles_by_contact[c].append(role)
        for c,roles in roles_by_contact.items():contact_sources[c].append({'palette_id':p['id'],'roles':roles,'artist':p['artist']})
    def describe(c):
        sources=contact_sources[c]
        assert sources,'Eligible shape contact lacks real source provenance'
        return {'string_number':c[0],'fret':c[1],'pitch':TUNING[c[0]-1]+c[1],
            'roles':sorted({r for s in sources for r in s['roles']}),'sources':sources}
    used={};opens=set()
    for e in events:
        for n in e['members']:
            c=(n['string_number'],n['fret'])
            if not c[1]:opens.add(c[0]);continue
            row=used.setdefault(c,{'string_number':c[0],'fret':c[1],'pitch':n['pitch'],'as_fretting':False,'as_tapping':False})
            row['as_tapping' if n['marks'].get('tapping') else 'as_fretting']=True
    fretted=sum(n['as_fretting'] for n in used.values());frets=[c[1] for c in ordinary]
    kind='shape_window' if fretted>=2 else 'single_contact_context' if fretted else 'tapped_context_only' if used else 'open_string_only'
    return {'schema':'riff-shape-use/1','mode':mode,'kind':kind,
        'ordinary_fret_bounds':[min(frets),max(frets)] if frets else None,
        'ordinary_contacts':[describe(c) for c in sorted(ordinary)],'tapped_contacts':[describe(c) for c in sorted(tapped)],
        'used_contacts':[used[c] for c in sorted(used)],'open_strings_played':sorted(opens),
        'reference_shapes':[{'palette_id':p['id'],'artist':p['artist'],'provenance_hashes':p.get('provenance_hashes',[])} for p in palettes]}


def _compose(program,palette_pool,mode,seed,choice_offsets=None,relations=None,available_domains=None,family_cache=None,hierarchy_relations=None,movement_guidance=None,fixed_slot_pitches=None,contact_guidance=None):
    if 'within_phrase_movement' in program.get('seam_constraints',{}) and any(r['context'] is None for r in phrase_motion_attachments(program)):
        return {'status':'no_choice','reason':'dependent_execution_context_has_no_body','program_id':program.get('id')}
    plan=program['plan'];relations=deepcopy(plan['relations'] if relations is None else relations)
    hierarchy=deepcopy(plan.get('hierarchy',{}).get('relations',[]) if hierarchy_relations is None else hierarchy_relations)
    program=operative_parent_roles(program,hierarchy)
    membership,parent_exact=hierarchy_runtime(plan,hierarchy);parent_values=defaultdict(dict)
    # Witnessed parents own alignment. Incidental matching child rhythms cannot
    # impose a conflicting return when those children have different extents.
    macro_instances={i['id'] for i in plan['instances'] if any(ei in membership for ei in i['event_indices'])}
    relations=[r for r in relations if r['to'] not in macro_instances]
    incoming={r['to']:r for r in relations};available=domains(palette_pool,mode) if available_domains is None else available_domains;choice_offsets=choice_offsets or {}
    family_cache={} if family_cache is None else family_cache
    constraint_key=('pitch_choices',digest([relations,hierarchy]))
    if constraint_key not in family_cache:family_cache[constraint_key]=relational_pitch_choices(program,mode,relations,hierarchy)
    choices,aliases=family_cache[constraint_key]
    program={**program,'_slot_pitch_choices':choices,'_slot_aliases':aliases,'_operative_flat_relations':relations,'_movement_guidance':movement_guidance or {},
        '_fixed_slot_pitches':fixed_slot_pitches or {},'_contact_guidance':contact_guidance or {}}
    states={};decisions={};events=[None]*len(program['template']['events']);failures={};slot_domains={};owners={};structural_roles={}
    instances={i['id']:i for i in plan['instances']}
    for instance in plan['instances']:
        ident=instance['id'];relation=incoming.get(ident);local=local_template(program,instance,relation)
        local_seed=stable_seed([seed,mode,ident])
        forced_domains={};fixed_roles={};exact_members={}
        seam_fixed,assignment_filter,seam_context=seam_selection(program,instance,events,slot_domains,membership)
        if seam_fixed is None:return {'status':'no_choice','reason':'incompatible_shared_seam_pitch','failed_instance':ident}
        fixed_roles.update(seam_fixed)
        domain_cost,seam_signature,execution_cost=seam_context
        for group in {membership[ei] for ei in instance['event_indices'] if ei in membership}:
            for role,value in parent_values[group].items():
                if role in fixed_roles and fixed_roles[role]!=value:return {'status':'no_choice','reason':'conflicting_parent_variables','failed_instance':ident}
                fixed_roles[role]=value
        for li,ei in enumerate(instance['event_indices']):
            for ni,n in enumerate(local['events'][li]['members']):
                if ei in membership:
                    value=parent_values[membership[ei]].get(n['role'])
                    if value is not None:
                        if n['role'] in fixed_roles and fixed_roles[n['role']]!=value:return {'status':'no_choice','reason':'conflicting_parent_variables','failed_instance':ident}
                        fixed_roles[n['role']]=value
                origin=parent_exact.get((ei,ni))
                if origin and events[origin[0]] is not None:
                    exact_members[li,ni]=deepcopy(events[origin[0]]['members'][origin[1]])
                    forced_domains[li,ni]=slot_domains[origin]
        is_full_parent_return=len(exact_members)==sum(len(e['members']) for e in local['events'])
        if is_full_parent_return:
            assignment=[0]*program['template']['role_count'];result={'events':deepcopy(local['events'])}
            for li,event in enumerate(result['events']):
                for ni,n in enumerate(event['members']):
                    role=n['role'];inherited=exact_members[li,ni];assignment[role]=inherited['pitch']
                    event['members'][ni]={**inherited,'structural_role':role}
            domain=next(iter(forced_domains.values()));decision_kind='reuse_parent_timed_execution'
        elif relation:
            if relation['from'] not in states:return {'status':'no_choice','reason':'noncausal_return_graph'}
            parent=states[relation['from']];assignment=parent['assignment'];domain=parent['domain']
            fixed=invariant_contacts(parent['result'],local,assignment)
            result,reason=realize(local,assignment,domain,local_seed,fixed,phrase_steps=local_phrase_steps(program,instance),enforce_phrase_continuity='within_phrase_movement' in program.get('seam_constraints',{}))
            if not result:return {'status':'no_choice','reason':reason,'failed_instance':ident,'decisions':decisions}
            decision_kind='reuse_exact_execution' if all(assignment[n['role']]==p['pitch'] for e,pe in zip(local['events'],parent['result']['events']) for n,p in zip(e['members'],pe['members'])) else 'shared_context_preserved_invariant_contacts'
        else:
            cache_key=(ident,choice_offsets.get(ident,0),tuple(sorted(fixed_roles.items())),tuple((k,d['id']) for k,d in sorted(forced_domains.items())),seam_signature)
            if fixed_slot_pitches:cache_key+=(digest([[list(k),v] for k,v in sorted(fixed_slot_pitches.items())]),)
            exhausted_key=('exhausted_family',cache_key[0],*cache_key[2:])
            exhausted=family_cache.get(exhausted_key)
            if cache_key not in family_cache:
                if exhausted is not None and cache_key[1]>=exhausted[0]:family_cache[cache_key]=exhausted[1]
                else:
                    # Asking for another offset changes which already ordered
                    # alternative is selected, not candidate feasibility/cost.
                    # The existing dependency signature excludes only offset.
                    enumeration_key=('family_enumeration',cache_key[0],*cache_key[2:])
                    family_cache[cache_key]=choose_family(program,instance,mode,'interval_function',local_seed,available,choice_offset=choice_offsets.get(ident,0),
                        fixed_roles=fixed_roles,forced_domains=forced_domains,hierarchical=ident in macro_instances,
                        assignment_filter=assignment_filter,domain_cost=domain_cost,execution_cost=execution_cost,
                        enumeration_cache=family_cache.setdefault(enumeration_key,{}))
                    if family_cache[cache_key][2] is None and (exhausted is None or cache_key[1]<exhausted[0]):
                        family_cache[exhausted_key]=(cache_key[1],family_cache[cache_key])
            assignment,domain,result,failed=family_cache[cache_key]
            failures[ident]=failed
            if not result:return {'status':'no_choice','reason':'no_admitted_local_family_context','failed_instance':ident,'failures':failures,'decisions':decisions,
                'independent_failure':not any(event is not None for event in events)}
            decision_kind='choose_context_with_parent_variables' if ident in macro_instances else 'choose_local_context_and_execution'
        states[ident]={'assignment':assignment,'domain':domain,'result':result}
        decisions[ident]={'assignment':assignment,'domain_id':domain['id'],'domain_kind':domain['kind'],
            'from_relation':relation and relation['from'],'local_seed':local_seed,'decision_kind':decision_kind,
            'choice_offset':choice_offsets.get(ident,0),'slot_map':deepcopy(relation['slot_map']) if relation else None}
        for li,(absolute,event) in enumerate(zip(instance['event_indices'],result['events'])):
            e=deepcopy(event);e['onset_q']=str(F(e['onset_q'])+F(instance['offset_q']))
            for ni,n in enumerate(e['members']):
                n['id']=f'e{absolute}:n{ni}';slot_domains[absolute,ni]=forced_domains.get((li,ni),domain);owners[absolute,ni]=ident
                structural_roles[absolute,ni]=n['structural_role']
                if absolute in membership:
                    variables=parent_values[membership[absolute]];role=n['structural_role']
                    if role in variables and variables[role]!=n['pitch']:return {'status':'no_choice','reason':'parent_shared_role_conflict','failed_instance':ident}
                    variables[role]=n['pitch']
            events[absolute]=e
        if fixed_slot_pitches and any(events[ei]['members'][ni]['pitch']!=fixed_slot_pitches[ei,ni] for ei in instance['event_indices'] for ni in range(len(events[ei]['members']))):
            return {'status':'no_choice','reason':'joint_register_resolution_conflict','failed_instance':ident}
        if not seam_pitch_check(program,events):return {'status':'no_choice','reason':'cross_phrase_register_or_common_tone_conflict','failed_instance':ident,'decisions':decisions}
    full=deepcopy(program['template']);pitches=[]
    released={tuple(r['event_slot']) for r in program.get('released_upper_opens',[])}
    for ei,e in enumerate(full['events']):
        for ni,n in enumerate(e['members']):
            n['role']=len(pitches);n['optional_open']=(ei,ni) in released;pitches.append(events[ei]['members'][ni]['pitch'])
    contact_links=[(a,b) for b,a in parent_exact.items()]
    for relation in relations:
        left,right=instances[relation['from']],instances[relation['to']]
        for slot in relation['slot_map']:
            local,ni=slot['slot'];a=(left['event_indices'][local],ni);b=(right['event_indices'][local],ni)
            if events[a[0]]['members'][a[1]]['pitch']==events[b[0]]['members'][b[1]]['pitch']:contact_links.append((a,b))
    joint_diagnostics={}
    joint,reason=realize(full,pitches,{'ordinary':set(),'tapped':set()},seed,
        slot_domains=slot_domains,contact_links=contact_links,contact_owners=owners,
        movement_preferences=[{**r,'travel_time_seconds':str(movement_seconds(program,r))} for r in program.get('seam_constraints',{}).get('movement_preferences',[])],
        contact_preferences=program.get('seam_constraints',{}).get('contact_preferences',[]),diagnostics=joint_diagnostics,
        phrase_steps=program.get('seam_constraints',{}).get('within_phrase_movement',[]),
        enforce_phrase_continuity='within_phrase_movement' in program.get('seam_constraints',{}),phrase_owners=phrase_motion_owners(program))
    if not joint:
        failed_slots=joint_diagnostics.get('conflict_slots',[])
        failed_instances=list(dict.fromkeys(owners[tuple(slot)] for slot in sorted(failed_slots)))
        return {'status':'no_choice','reason':'joint_program:'+reason,'decisions':decisions,'failures':failures,
            'failed_instances':failed_instances,'failed_slots':failed_slots,'failed_instance':failed_instances[-1] if failed_instances else None}
    events=joint['events']
    for ei,e in enumerate(events):
        for ni,n in enumerate(e['members']):n['structural_role']=structural_roles[ei,ni]
    phrases=[]
    for instance in plan['instances']:
        ident=instance['id'];blocks=[];runs=[]
        # An exact parent may span several independently detected child shapes.
        # Reuse its timed context sequence; never union those windows into one
        # fictitious hand shape just because the new child cuts differ.
        for ei in instance['event_indices']:
            selected=[slot_domains[ei,ni] for ni in range(len(events[ei]['members']))]
            unique={d['id']:d for d in selected}
            if len(unique)==1:domain=selected[0]
            else:
                domain={'id':'joint-'+digest(sorted(unique))[:16],'kind':'constructed_simultaneous_context',
                    'ordinary':set().union(*(d['ordinary'] for d in unique.values())),
                    'tapped':set().union(*(d['tapped'] for d in unique.values())),
                    'palettes':list({p['id']:p for d in unique.values() for p in d['palettes']}.values())}
            if runs and runs[-1][0]['id']==domain['id']:runs[-1][1].append(ei)
            else:runs.append((domain,[ei]))
        for ri,(domain,indices) in enumerate(runs):
            a=F(instance['offset_q']) if ri==0 else F(events[indices[0]]['onset_q'])
            b=F(events[runs[ri+1][1][0]]['onset_q']) if ri+1<len(runs) else F(instance['offset_q'])+F(instance['length_q'])
            usage=shape_usage(domain,mode,{'events':[events[i] for i in indices]})
            blocks.append({'offset_q':str(a-F(instance['offset_q'])),'duration_q':str(b-a),'shape_usage':usage,'domain_selection':decisions[ident]['decision_kind']})
        phrases.append({'id':ident,'offset_q':instance['offset_q'],'length_q':instance['length_q'],
            'role':instance['role'],'motif_id':instance['motif_id'],'blocks':blocks})
    tempo_map=deepcopy(program['timing']['tempo_map']);bars=deepcopy(program['timing']['bar_map'])
    score={'schema':'procedural-riff-result/1','status':'generated','events':events,'mode':mode,
        'duration_q':program['duration_q'],'tempo':float(F(tempo_map[0]['quarter_bpm'])),'tempo_map':tempo_map,
        'bar_map':bars,'meter':bars[0]['meter'],'tuning':TUNING,'phrases':phrases,'plan':deepcopy(plan),
        'operative_relations':relations,'operative_parent_relations':hierarchy,'decisions':decisions,'program_id':program['id'],'program_artist':program['artist'],
        'closure_status':deepcopy(program['closure_status']),'capability_flags':deepcopy(program.get('capability_flags',[])),
        'articulation_scope':'Written holds, normalized supported marks and technique links; listening and speed-dependent playability unaccepted.'}
    if 'within_phrase_movement' in program.get('seam_constraints',{}):
        score['execution_context_choices']=phrase_motion_attachments(program)
    score['transitions']=transitions(program,score)
    score['checks']=verify(program,score)
    return score


def verify(program,score):
    assert score['status']=='generated'
    if 'within_phrase_movement' in program.get('seam_constraints',{}):
        assert not any(r['context'] is None for r in phrase_motion_attachments(program)),'Unanchored dependent execution context'
    program=operative_parent_roles(program,score.get('operative_parent_relations',[]))
    assert seam_pitch_check(program,score['events']),'Whole-riff register/common-tone constraint failed'
    assert not phrase_step_violations(program,score['events']),'Within-phrase ordinary hand continuity failed'
    occupied={};count=0;bends=0;by_id={i['id']:i for i in program['plan']['instances']}
    for ei,(expected,event) in enumerate(zip(program['template']['events'],score['events'])):
        assert F(expected['onset_q'])==F(event['onset_q'])
        assert len(expected['members'])==len(event['members']);at=F(event['onset_q'])
        occupied={s:v for s,v in occupied.items() if v[0]>at}
        for ni,(n,m) in enumerate(zip(expected['members'],event['members'])):
            assert F(n['hold_q'])==F(m['duration_q']) and n['marks']==m['marks']
            assert m['string_number'] not in occupied
            assert m['pitch']==TUNING[m['string_number']-1]+m['fret']
            assert (m['pitch']-4)%12 in MODES[score['mode']]
            occupied[m['string_number']]=(at+F(m['duration_q']),m['fret'],bool(m['marks'].get('tapping')))
            regular=[f for end,f,tap in occupied.values() if f and not tap]
            assert not regular or max(regular)-min(regular)<=6
            bend=m['marks'].get('bend')
            if bend:
                bends+=1
                for delta in [F(bend['points'][-1]['semitones']),max(F(p['semitones']) for p in bend['points'])]:
                    assert delta.denominator==1 and (m['pitch']+int(delta)-4)%12 in MODES[score['mode']]
            count+=1
    assert len(score['events'])==len(program['template']['events'])
    for link in program['template']['links']:
        a,b=link['origin'],link['destination'];x=score['events'][a[0]]['members'][a[1]];y=score['events'][b[0]]['members'][b[1]]
        assert x['string_number']==y['string_number'] and (y['fret']>x['fret'])-(y['fret']<x['fret'])==link['direction']
    parent_slots=0
    for relation in score.get('operative_parent_relations',[]):
        for pair in relation['slot_pairs']:
            a,b=pair['from'],pair['to'];x=score['events'][a[0]]['members'][a[1]];y=score['events'][b[0]]['members'][b[1]]
            if pair['preserve_pitch']:assert x['pitch']==y['pitch'],'Parent return lost pitch correspondence'
            if pair['preserve_execution']:
                assert (x['string_number'],x['fret'],x['duration_q'],x['marks'])==(y['string_number'],y['fret'],y['duration_q'],y['marks']),'Parent return lost execution correspondence'
            parent_slots+=1
    membership,_=hierarchy_runtime(program['plan'],score.get('operative_parent_relations',[]));vocabularies=defaultdict(dict)
    for ei,group in membership.items():
        for member in score['events'][ei]['members']:
            role=member['structural_role'];values=vocabularies[group]
            assert role not in values or values[role]==member['pitch'],'Parent vocabulary lost shared pitch identity'
            values[role]=member['pitch']
    for values in vocabularies.values():
        assert all(values[a]<values[b] for a,b in zip(sorted(values),sorted(values)[1:])),'Parent vocabulary reversed ordered roles'
    invariant=0;exact=0
    for relation in score['operative_relations']:
        left,right=by_id[relation['from']],by_id[relation['to']]
        if score['decisions'][right['id']]['decision_kind']=='reuse_exact_execution':exact+=1
        for slot in relation['slot_map']:
            local,ni=slot['slot'];x=score['events'][left['event_indices'][local]]['members'][ni];y=score['events'][right['event_indices'][local]]['members'][ni]
            if x['pitch']==y['pitch']:
                assert (x['string_number'],x['fret'],x['duration_q'],x['marks'])==(y['string_number'],y['fret'],y['duration_q'],y['marks']);invariant+=1
    intervals=[]
    for c in program['accent_constraints']:
        for ei in c['event_indices']:
            values=[n['pitch'] for n in score['events'][ei]['members']]
            assert max(values)-min(values)==c['semitones']
            intervals.append({'event':ei,'literal_span_semitones':max(values)-min(values)})
    incoming={r['to']:r for r in score['operative_relations']}
    for instance in program['plan']['instances']:
        notes=[n for ei in instance['event_indices'] for n in score['events'][ei]['members']]
        expected=local_template(program,instance,incoming.get(instance['id']))
        expected_roles=[n['role'] for row in expected['events'] for n in row['members']]
        assert [n['structural_role'] for n in notes]==expected_roles,'Output roles differ from the compiled program/operative relation'
        role_order={r:i for i,r in enumerate(sorted(set(expected_roles)))}
        pitch_order={p:i for i,p in enumerate(sorted({n['pitch'] for n in notes}))}
        assert [role_order[r] for r in expected_roles]==[pitch_order[n['pitch']] for n in notes]
    certificate=program.get('novelty_certificate',{})
    assert certificate.get('version')=='private-order-proof/1' and certificate.get('verified') is True
    closure=program.get('closure_status',{})
    if closure.get('status') in ('LOOP','RELEASE'):
        end=max(F(event['onset_q'])+F(n['duration_q']) for event in score['events'] for n in event['members'])
        assert end<=F(closure.get('stop_at_q',program['duration_q'])),'Written gesture extends beyond declared stop'
        if closure['status']=='RELEASE':assert end==F(closure['release_at_q']),'Ending release was not realized'
        if closure['status']=='LOOP':
            rule=closure['loop_constraint'];first,last=rule['first_events'],rule['last_events']
            assert len(first)==len(last)
            for ai,bi in zip(first,last):
                a,b=score['events'][ai],score['events'][bi]
                assert [(n['pitch'],n['string_number'],n['fret'],n['duration_q'],n['marks']) for n in a['members']]==[(n['pitch'],n['string_number'],n['fret'],n['duration_q'],n['marks']) for n in b['members']],'Closing loop lost its complete returning execution'
            internal=F(score['events'][rule['internal_next_start_event']]['onset_q'])-F(score['events'][rule['internal_previous_end_event']]['onset_q'])
            actual=F(score['duration_q'])-F(score['events'][last[-1]]['onset_q'])+F(score['events'][first[0]]['onset_q'])
            assert actual==internal==F(rule['loop_gap_q']),'Loop join differs from the observed internal join'
    return {'source_rhythm_holds_marks_preserved':True,'notes':count,'bends':bends,'technique_links':len(program['template']['links']),
        'whole_program_occupancy_checked':True,'cross_boundary_constraints_checked':True,
        'invariant_execution_slots':invariant,'exact_execution_returns':exact,'salient_intervals':intervals,
        'parent_correspondence_slots':parent_slots,'parent_vocabulary_and_execution_checked':True,
        'whole_riff_register_and_common_tones_checked':True,'ending_constraint_checked':closure.get('status') in ('LOOP','RELEASE'),
        'new_ordinal_program_preserved':True,'source_noncopy_by_private_order_proof':True,
        'source_pitch_oracle_present':False,'listening_acceptance':False,'execution_speed_accepted':False,
        **({'within_phrase_continuity_checked':True,'source_motion_calibration_step_count':len(program['seam_constraints']['within_phrase_movement'])}
            if 'within_phrase_movement' in program.get('seam_constraints',{}) else {})}


def _generate_program(program,pack,request,budget=48,relations=None,hierarchy_relations=None,fixed_slot_pitches=None):
    palettes=[p for p in pack['palettes'] if p['artist'] in request['artists']]
    relations=program['plan']['relations'] if relations is None else relations
    hierarchy=program['plan'].get('hierarchy',{}).get('relations',[]) if hierarchy_relations is None else hierarchy_relations
    membership,_=hierarchy_runtime(program['plan'],hierarchy)
    macro_instances={i['id'] for i in program['plan']['instances'] if any(ei in membership for ei in i['event_indices'])}
    incoming={r['to'] for r in relations if r['to'] not in macro_instances}
    roots=[i['id'] for i in program['plan']['instances'] if i['id'] not in incoming]
    owners={ei:i['id'] for i in program['plan']['instances'] for ei in i['event_indices']}
    active_aliases={}
    incoming_edges={r['to']:r['from'] for r in relations if r['to'] in incoming}
    def root_owner(ident):
        while ident in incoming_edges:ident=incoming_edges[ident]
        return ident
    def relevant_roots(failed,trace_shared_owners=False):
        if failed is None:return list(range(len(roots)))
        indices={ei for ei,owner in owners.items() if owner==failed};related={root_owner(failed)};relevant_slots=set()
        rules=program.get('seam_constraints',{})
        for rule in rules.get('pitch_equalities',[])+rules.get('register_relations',[])+rules.get('movement_preferences',[])+rules.get('within_phrase_movement',[]):
            slots=rule.get('left_slots',[])+rule.get('right_slots',[])+rule.get('lower_slots',[])+rule.get('upper_slots',[])
            if any(ei in indices for ei,ni in slots):
                related.update(root_owner(owners[ei]) for ei,ni in slots if ei<=max(indices));relevant_slots.update(map(tuple,slots))
        variables={active_aliases.get(slot,slot) for slot in relevant_slots}
        earliest={}
        for slot,variable in sorted(active_aliases.items()):
            if variable in variables and slot[0]<=max(indices):earliest.setdefault(variable,root_owner(owners[slot[0]]))
        if trace_shared_owners:related.update(earliest.values())
        groups={membership[ei] for ei in indices if ei in membership}
        related.update(root_owner(owners[ei]) for ei,g in membership.items() if g in groups and ei<=max(indices))
        return [i for i in range(len(roots)-1,-1,-1) if roots[i] in related]
    queue=deque([tuple(0 for _ in roots)]);seen=set(queue);failures=[]
    available=domains(palettes,request['mode']);family_cache={}
    best=None;best_cost=None;best_offsets=None
    phase='feasibility';movement_start=0;movement_guidance={}
    while queue and (len(failures)<budget if phase=='feasibility' else len(failures)-movement_start<budget):
        vector=queue.popleft();offsets=dict(zip(roots,vector))
        try:score=_compose(program,palettes,request['mode'],request['seed'],offsets,relations,available,family_cache,hierarchy_relations,movement_guidance,fixed_slot_pitches)
        except (AssertionError,KeyError,ValueError) as error:
            score={'status':'no_choice','reason':'constraint_or_schema_error:'+type(error).__name__+':'+str(error)}
        active_aliases=next((v[1] for k,v in family_cache.items() if k[0]=='pitch_choices'),{})
        enter_movement=False
        if score['status']=='generated' and score['checks']['new_ordinal_program_preserved']:
            cost,movements=whole_movement_cost(program,score)
            score['checks']['source_relative_movement_cost']=str(cost)
            score['checks']['remaining_source_relative_movement_excess']=movements
            enter_movement=best is None
            if best is None or cost<best_cost:best=score;best_cost=cost;best_offsets=offsets
            if not cost:
                score['search']={'same_program_same_seed':True,'attempts':len(failures)+1,'retained_refusals':failures,'choice_offsets':offsets,
                    'whole_output_movement_ranked':True}
                return score
            score={**score,'reason':'complete_candidate_with_relative_movement_cost','failed_instance':movements[0]['to'],
                'movement_cost':str(cost),'movement_joins':movements}
        reason=score.get('reason','unchanged_or_uniform_transposition')
        failures.append({'reason':reason,'choice_offsets':offsets,'failed_instance':score.get('failed_instance'),
            'events_sha256':digest(score['events']) if score.get('events') else None,
            **({'failed_slots':score['failed_slots'],'failed_instances':score['failed_instances']} if score.get('failed_slots') else {}),
            **({'movement_cost':score['movement_cost'],'movement_joins':score['movement_joins']} if 'movement_cost' in score else {})})
        if enter_movement:
            phase='movement';movement_start=len(failures);queue.clear()
            rules={r['join_id']:r for r in program.get('seam_constraints',{}).get('movement_preferences',[])}
            earliest={}
            for slot,variable in sorted(active_aliases.items()):earliest.setdefault(variable,root_owner(owners[slot[0]]))
            # A returning high shape may have been chosen many children before
            # its low neighbor. Re-solve the same complete generated idea with
            # coherent octave/register alternatives for its owning variables.
            # These are solver inputs, never patches to emitted notes. Every
            # pitch, domain, hold/link and return constraint is checked again.
            base_pitches={(ei,ni):n['pitch'] for ei,event in enumerate(best['events']) for ni,n in enumerate(event['members'])}
            open_variables={active_aliases.get((ei,ni),(ei,ni)) for ei,event in enumerate(best['events']) for ni,n in enumerate(event['members']) if n['fret']==0}
            register_seen=set();register_trials=[]
            for issue in ([] if fixed_slot_pitches is not None else score['movement_joins']):
                rule=rules[issue['join_id']]
                for side in ('right_slots','left_slots'):
                    decision_owners={root_owner(owners[ei]) for ei,ni in rule[side]}
                    decision_owners.update(earliest.get(active_aliases.get(tuple(s),tuple(s))) for s in rule[side])
                    variables={active_aliases.get((ei,ni),(ei,ni)) for ei,event in enumerate(best['events']) for ni,n in enumerate(event['members'])
                        if root_owner(owners[ei]) in decision_owners and n['fret'] and not n['marks'].get('tapping')}-open_variables
                    if not variables:continue
                    expanding=True
                    while expanding:
                        previous=len(variables)
                        for instance in program['plan']['instances']:
                            local_variables={active_aliases.get((ei,ni),(ei,ni)) for ei in instance['event_indices'] for ni,n in enumerate(best['events'][ei]['members'])
                                if n['fret'] and not n['marks'].get('tapping')}-open_variables
                            if variables.intersection(local_variables):variables.update(local_variables)
                        expanding=len(variables)!=previous
                    for delta in (-12,12,-24,24,-36,36,-48,48):
                        proposal={slot:p+delta if active_aliases.get(slot,slot) in variables else p for slot,p in base_pitches.items()}
                        fingerprint=digest([[list(k),v] for k,v in sorted(proposal.items())])
                        if fingerprint in register_seen:continue
                        register_seen.add(fingerprint)
                        if any(not program['role_register_bounds'][program['template']['events'][ei]['members'][ni]['role']][0]<=p<=program['role_register_bounds'][program['template']['events'][ei]['members'][ni]['role']][1] for (ei,ni),p in proposal.items()):continue
                        if not seam_pitch_check(program,[None]*len(program['template']['events']),proposal):continue
                        try:alternative=_compose(program,palettes,request['mode'],request['seed'],{},relations,available,{},hierarchy_relations,{},proposal)
                        except (AssertionError,ValueError,KeyError) as error:alternative={'status':'no_choice','reason':'register_constraint:'+type(error).__name__+':'+str(error)}
                        trial={'join_id':rule['join_id'],'decision_owners':sorted(decision_owners-{None}),'octaves':delta//12,'status':alternative['status'],
                            'proposal_sha256':fingerprint,'reason':alternative.get('reason')}
                        if alternative['status']=='generated':
                            alt_cost,alt_moves=whole_movement_cost(program,alternative)
                            trial.update(movement_cost=str(alt_cost),events_sha256=digest(alternative['events']))
                            alternative['checks'].update(source_relative_movement_cost=str(alt_cost),remaining_source_relative_movement_excess=alt_moves)
                            if alt_cost<best_cost:best=alternative;best_cost=alt_cost;best_offsets={}
                            if not alt_cost:
                                register_trials.append(trial)
                                alternative['search']={'same_program_same_seed':True,'attempts':len(failures)+len(register_trials),'retained_refusals':failures,
                                    'choice_offsets':{},'whole_output_movement_ranked':True,'joint_register_trials':register_trials,
                                    'register_resolution':'Coherent parent/motif variables re-solved through the full contact/relationship engine.'}
                                return alternative
                        register_trials.append(trial)
            if register_trials:failures.append({'reason':'joint_register_trials_retained','trials':register_trials})
            for issue in score['movement_joins']:
                rule=rules[issue['join_id']]
                for side,other in [('left_slots','right_slots'),('right_slots','left_slots')]:
                    frets=[best['events'][ei]['members'][ni]['fret'] for ei,ni in rule[other] if best['events'][ei]['members'][ni]['fret']]
                    if not frets:continue
                    selected={root_owner(owners[ei]) for ei,ni in rule[side]}
                    selected.update(earliest.get(active_aliases.get(tuple(s),tuple(s))) for s in rule[side])
                    for ident in selected-{None}:
                        movement_guidance.setdefault(ident,[]).append({'join_id':rule['join_id'],'neighbor_center':str(F(sum(frets),len(frets))),
                            'allowed_center_shift':rule['source_center_shift_frets'],'time_seconds':str(movement_seconds(program,rule))})
            restart=tuple(0 for _ in roots);queue.append(restart);seen={restart}
            continue
        failed_root=score.get('failed_instance')
        if reason=='no_admitted_local_family_context' and failed_root in roots and offsets[failed_root]==0 and (score.get('independent_failure') or (failed_root not in macro_instances and not program.get('seam_constraints'))):
            # This search depends only on this root, fixed mode/artist pool and
            # seed. Other root choices cannot create its first candidate.
            return {'schema':'procedural-riff-result/1','status':'no_choice','program_id':program['id'],
                'reason':'independent_family_has_no_candidate_in_fixed_search','retained_refusals':failures}
        implicated=score.get('failed_instances') or [failed_root]
        relevant=sorted({index for ident in implicated for index in relevant_roots(ident,reason=='complete_candidate_with_relative_movement_cost')},reverse=True)
        for index in relevant:
            nxt=list(vector);nxt[index]+=1
            if reason=='complete_candidate_with_relative_movement_cost':
                for later in range(index+1,len(nxt)):nxt[later]=0
            nxt=tuple(nxt)
            if nxt not in seen:
                seen.add(nxt)
                if reason=='complete_candidate_with_relative_movement_cost':queue.appendleft(nxt)
                else:queue.append(nxt)
    if best is not None:
        best['search']={'same_program_same_seed':True,'attempts':len(failures),'retained_refusals':failures,'choice_offsets':best_offsets,
            'whole_output_movement_ranked':True,'status':'best_complete_candidate_in_bounded_search','remaining_movement_excess_not_execution_acceptance':True,
            'feasibility_attempts':movement_start,'movement_attempts':len(failures)-movement_start}
        return best
    return {'schema':'procedural-riff-result/1','status':'no_choice','program_id':program['id'],
        'reason':'bounded_same_program_search_exhausted','retained_refusals':failures}


def contact_continuity_issues(program,score):
    issues=[]
    for rule in program.get('seam_constraints',{}).get('contact_preferences',[]):
        a,b=rule['left_slot'],rule['right_slot']
        x=score['events'][a[0]]['members'][a[1]];y=score['events'][b[0]]['members'][b[1]]
        if x['pitch']==y['pitch'] and (x['string_number'],x['fret'])!=(y['string_number'],y['fret']):
            issues.append({'left_slot':a,'right_slot':b,'pitch':x['pitch'],
                'preferred_contact':[x['string_number'],x['fret']]})
    return issues


def refine_contact_continuity(program,pack,request,score,relations=None,hierarchy_relations=None):
    """One fixed-pitch re-solve of avoidable source-backed contact changes.

    This is a tie-break between feasible placements, not an additional search
    budget or hand-speed rule. Failure retains the complete original result.
    """
    issues=contact_continuity_issues(program,score)
    if not issues:return score
    instances={i['id']:i for i in program['plan']['instances']}
    owners={ei:i['id'] for i in instances.values() for ei in i['event_indices']}
    parents={}
    def find(slot):
        slot=tuple(slot)
        while slot in parents and parents[slot]!=slot:slot=parents[slot]
        return slot
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parents[max(a,b)]=min(a,b)
    for relation in score['operative_parent_relations']:
        for pair in relation['slot_pairs']:
            if pair['preserve_execution']:union(pair['from'],pair['to'])
    for relation in score['operative_relations']:
        left,right=instances[relation['from']],instances[relation['to']]
        for slot in relation['slot_map']:
            if slot['invariant']:
                li,ni=slot['slot'];union([left['event_indices'][li],ni],[right['event_indices'][li],ni])
    guidance=defaultdict(list)
    for issue in issues:
        slot=find(issue['right_slot'])
        value={'slot':list(slot),'pitch':issue['pitch'],'contact':issue['preferred_contact']}
        if value not in guidance[owners[slot[0]]]:guidance[owners[slot[0]]].append(value)
    fixed={(ei,ni):n['pitch'] for ei,e in enumerate(score['events']) for ni,n in enumerate(e['members'])}
    palettes=[p for p in pack['palettes'] if p['artist'] in request['artists']]
    try:
        alternative=_compose(program,palettes,request['mode'],request['seed'],relations=relations,
            hierarchy_relations=hierarchy_relations,fixed_slot_pitches=fixed,contact_guidance=guidance)
    except (AssertionError,KeyError,ValueError) as error:
        alternative={'status':'no_choice','reason':'contact_tiebreak:'+type(error).__name__+':'+str(error)}
    before_cost,_=whole_movement_cost(program,score)
    receipt={'attempts':1,'fixed_all_pitches':True,'before_mismatches':len(issues),'status':alternative['status'],'adopted':False}
    if alternative['status']=='generated':
        after_cost,movements=whole_movement_cost(program,alternative)
        after=len(contact_continuity_issues(program,alternative))
        receipt.update(after_mismatches=after,movement_cost_before=str(before_cost),movement_cost_after=str(after_cost))
        if after<len(issues) and after_cost<=before_cost:
            receipt['adopted']=True
            alternative['checks'].update(source_relative_movement_cost=str(after_cost),remaining_source_relative_movement_excess=movements)
            alternative['search']={**score['search'],'contact_continuity_refinement':receipt}
            return alternative
    else:receipt['reason']=alternative.get('reason')
    score['search']={**score['search'],'contact_continuity_refinement':receipt}
    return score


def released_open_movement(program,score):
    """Soft generated-contact preference where source opens give no hand baseline.

    Ordinary contact footprints, actual elapsed time and written free time are
    retained. Zero preferred relocation is a new placement preference, never a
    claim about source fingering or a prohibition on between-phrase movement.
    """
    released={tuple(r['event_slot']) for r in program.get('released_upper_opens',[])}
    if not released:return F(0),[],{}
    events=score['events'];frames=[];rules={};issues=[];total=F(0)
    for ei,event in enumerate(events):
        slots=[(ei,ni) for ni,n in enumerate(event['members']) if n['fret']>0 and not n['marks'].get('tapping')]
        if slots:frames.append((ei,slots))
    covered=[(set(map(tuple,r['left_slots'])),set(map(tuple,r['right_slots'])))
        for r in program.get('seam_constraints',{}).get('movement_preferences',[])]
    for (ai,left),(bi,right) in zip(frames,frames[1:]):
        if not released.intersection(left+right):continue
        if any(set(left)<=a and set(right)<=b for a,b in covered):continue
        if any(l['kind']=='slide' and tuple(l['origin']) in left and tuple(l['destination']) in right
            for l in program['template'].get('links',[])):continue
        gap=F(events[bi]['onset_q'])-F(events[ai]['onset_q'])
        if gap<=0:continue
        written_end=max(F(event['onset_q'])+F(n['duration_q']) for event in events[:ai+1]
            for n in event['members'] if n['fret']>0 and not n['marks'].get('tapping'))
        ident=f'released-open:{ai}:{bi}'
        rule={'join_id':ident,'left_slots':list(map(list,left)),'right_slots':list(map(list,right)),
            'attack_gap_q':str(gap),'free_reposition_gap_q':str(max(F(0),F(events[bi]['onset_q'])-written_end)),
            'box_span_limit':6,'preferred_box_shift_frets':0,
            'basis':'generated_placement_preference_without_source_fretted_baseline'}
        rules[ident]=rule
        a=[events[ei]['members'][ni]['fret'] for ei,ni in left];b=[events[ei]['members'][ni]['fret'] for ei,ni in right]
        shift=max(0,max(b)-6-min(a),max(a)-6-min(b));cost=F(shift)/movement_seconds(program,rule)
        if cost:issues.append({'join_id':ident,'necessary_box_shift_frets':shift,'cost':str(cost),'basis':rule['basis']})
        total+=cost
    return total,issues,rules


def refine_soft_movement(program,pack,request,score,relations=None,hierarchy_relations=None):
    """One complete fixed-pitch re-solve for an avoidable between-phrase move.

    The allowed reference pool and all hard musical/physical relationships stay
    fixed. A failed alternative retains the valid original; there is no new
    cross-phrase speed cap and no additional candidate-search loop.
    """
    before_cost,issues=whole_movement_cost(program,score)
    before_open_cost,open_issues,open_rules=released_open_movement(program,score)
    if not before_cost and not before_open_cost:return score
    palettes=[p for p in pack['palettes'] if p['artist'] in request['artists']]
    contacts={tuple(c) for p in palettes for field in ('ordinary_contacts','extension_contacts') for c in p.get(field,[])}
    rules={r['join_id']:r for r in program.get('seam_constraints',{}).get('movement_preferences',[])}
    rules.update(open_rules);issues=issues+open_issues
    candidates=[]
    for issue in issues:
        rule=rules[issue['join_id']]
        sides={side:[tuple(slot) for slot in rule[side] if score['events'][slot[0]]['members'][slot[1]]['fret']>0
            and not score['events'][slot[0]]['members'][slot[1]]['marks'].get('tapping')] for side in ('left_slots','right_slots')}
        if not all(sides.values()):continue
        def cost(override=None):
            override=override or {}
            left,right=([override.get(slot,score['events'][slot[0]]['members'][slot[1]]['fret']) for slot in sides[side]] for side in ('left_slots','right_slots'))
            span=rule.get('source_box_span_limit',rule.get('box_span_limit'))
            shift=max(0,max(right)-span-min(left),max(left)-span-min(right))
            baseline=rule.get('preferred_box_shift_frets',rule.get('source_minimum_box_shift_frets'))
            if baseline is None:baseline=F(rule['source_center_shift_frets'])
            return max(F(0),F(shift)-F(baseline))/movement_seconds(program,rule)
        current=cost()
        for side in ('left_slots','right_slots'):
            for slot in sides[side]:
                n=score['events'][slot[0]]['members'][slot[1]]
                for contact in sorted(contacts):
                    if TUNING[contact[0]-1]+contact[1]!=n['pitch'] or contact==(n['string_number'],n['fret']):continue
                    if contact[1]<=0:continue
                    footprint=[m['fret'] for ni,m in enumerate(score['events'][slot[0]]['members']) if ni!=slot[1] and m['fret']>0 and not m['marks'].get('tapping')]+[contact[1]]
                    if max(footprint)-min(footprint)>6:continue
                    after=cost({slot:contact[1]})
                    if after<current:candidates.append((current-after,abs(contact[1]-n['fret']),slot,contact,issue['join_id']))
    if not candidates:return score
    candidates.sort(key=lambda row:(-row[0],row[1],row[2],row[3]))
    improvement,travel,slot,contact,join_id=candidates[0]
    instances={i['id']:i for i in program['plan']['instances']}
    owners={ei:i['id'] for i in instances.values() for ei in i['event_indices']};aliases={}
    def find(s):
        s=tuple(s)
        while s in aliases and aliases[s]!=s:s=aliases[s]
        return s
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:aliases[max(a,b)]=min(a,b)
    for relation in score['operative_parent_relations']:
        for pair in relation['slot_pairs']:
            if pair['preserve_execution']:union(pair['from'],pair['to'])
    for relation in score['operative_relations']:
        left,right=instances[relation['from']],instances[relation['to']]
        for pair in relation['slot_map']:
            if pair['invariant']:
                li,ni=pair['slot'];union([left['event_indices'][li],ni],[right['event_indices'][li],ni])
    root=find(slot);pitch=score['events'][slot[0]]['members'][slot[1]]['pitch']
    guidance={owners[root[0]]:[{'slot':list(root),'pitch':pitch,'contact':list(contact)}]}
    fixed={(ei,ni):n['pitch'] for ei,event in enumerate(score['events']) for ni,n in enumerate(event['members'])}
    receipt={'attempts':1,'admitted_contact_candidates_considered':len(candidates),'join_id':join_id,
        'candidate_slot':list(slot),'owning_slot':list(root),'preferred_contact':list(contact),'fixed_all_pitches':True,
        'before_cost':str(before_cost),'before_released_open_cost':str(before_open_cost),
        'preference_basis':rules[join_id].get('basis','source_relative_movement'),
        'adopted':False,'scope':'Soft ranking only; no cross-phrase jump/speed limit.'}
    try:alternative=_compose(program,palettes,request['mode'],request['seed'],relations=relations,
        hierarchy_relations=hierarchy_relations,fixed_slot_pitches=fixed,contact_guidance=guidance)
    except (AssertionError,ValueError,KeyError) as error:alternative={'status':'no_choice','reason':'soft_motion_refinement:'+type(error).__name__+':'+str(error)}
    receipt.update(status=alternative['status'],reason=alternative.get('reason'))
    if alternative['status']=='generated':
        after_cost,movements=whole_movement_cost(program,alternative)
        after_open_cost,_,_=released_open_movement(program,alternative)
        previous_issues={(tuple(x['left_slot']),tuple(x['right_slot'])) for x in contact_continuity_issues(program,score)}
        following_issues={(tuple(x['left_slot']),tuple(x['right_slot'])) for x in contact_continuity_issues(program,alternative)}
        def music(value):return [(event['onset_q'],[{k:v for k,v in n.items() if k not in ('string_number','fret')} for n in event['members']]) for event in value['events']]
        same_music=music(score)==music(alternative) and all(score.get(k)==alternative.get(k) for k in
            ('plan','operative_relations','operative_parent_relations','duration_q','tempo_map','bar_map'))
        receipt.update(after_cost=str(after_cost),no_contact_continuity_regression=following_issues<=previous_issues,
            after_released_open_cost=str(after_open_cost),same_notes_and_plan=same_music,
            alternative_events_sha256=digest(alternative['events']))
        if after_cost<=before_cost and after_open_cost<=before_open_cost and after_cost+after_open_cost<before_cost+before_open_cost and following_issues<=previous_issues and same_music:
            receipt['adopted']=True
            alternative['checks'].update(source_relative_movement_cost=str(after_cost),remaining_source_relative_movement_excess=movements)
            alternative['search']={**score['search'],'soft_movement_refinement':receipt}
            return alternative
    score['search']={**score['search'],'soft_movement_refinement':receipt}
    return score


def generate_program(program,pack,request,budget=48,relations=None,hierarchy_relations=None):
    score=_generate_program(program,pack,request,budget,relations,hierarchy_relations)
    if score['status']=='generated':
        score=refine_contact_continuity(program,pack,request,score,relations,hierarchy_relations)
        return refine_soft_movement(program,pack,request,score,relations,hierarchy_relations)
    return score


def generate(request,pack):
    if pack.get('schema')!='procedural-riff-pack/1':raise ValueError('Unsupported program pack')
    artists=request.get('artists',[])
    if not artists or any(a not in ARTISTS for a in artists):raise ValueError('Choose one or more supported artists')
    if request.get('mode') not in MODES:raise ValueError('Unsupported mode')
    seed=request.get('seed',0)
    if not isinstance(seed,(int,str)):raise ValueError('Seed must be an integer or string')
    request={'artists':[a for a in ARTISTS if a in artists],'mode':request['mode'],'seed':seed}
    programs=[p for p in pack['programs'] if p['artist'] in request['artists'] and p.get('closure_status',{}).get('authority',{}).get('whole_riff_eligible') is True]
    random.Random(stable_seed([seed,request['mode'],request['artists']])).shuffle(programs)
    refusals=[]
    for program in programs:
        score=generate_program(program,pack,request)
        if score['status']=='generated':
            score.update(request=request,program_selection={'eligible_programs':len(programs),'attempted_programs':len(refusals)+1,
                'retained_refusals':refusals},pack_sha256=pack.get('content_sha256'))
            return score
        refusals.append({'program_id':program['id'],'reason':score['reason'],'attempts':score['retained_refusals']})
    return {'schema':'procedural-riff-result/1','status':'no_choice','request':request,
        'reason':'no_complete_program_in_bounded_search','retained_refusals':refusals,'events':[],'phrases':[]}


def generate_json(request,pack):
    if isinstance(request,str):request=json.loads(request)
    if isinstance(pack,str):pack=json.loads(pack)
    return json.dumps(generate(request,pack),separators=(',',':'))

