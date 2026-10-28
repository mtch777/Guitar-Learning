"""Conditional source-pattern alternatives; no preferred harmony or edit admission."""
from collections import Counter,defaultdict
from fractions import Fraction as F
from inner_voicing import component_links,encoded
from voicing_frames import pitches,relationship
from probe_voicing_frames import preflight


def build(c,evidence):
    units={u['id']:u for u in c['units']}
    if len(units)!=len(c['units']):raise ValueError('Duplicate component hypothesis')
    groups=[];totals=Counter();pairs=set();patterns=defaultdict(set)
    for unit in units.values():
        if unit['base_reasons']:continue
        frame=relationship(*unit['family'][1:],roles=unit['roles'])
        bindings=sorted((s,r['degree_token'],r['octave_offset'])for s,r in zip(unit['strings'],frame['components']))
        key=encoded([unit['part_id'],unit['family'][2],bindings])
        patterns[key].add(unit['group_ref'])
    for row in evidence['groups']:
        if not row['hypotheses']:continue
        all_ids=[h['id']for h in row['hypotheses']];eligible=[];refusals=[];layouts={}
        for ident in all_ids:
            target=units.get(ident)
            if target is None or target['reasons']:
                refusals.append(dict(hypothesis_ref=ident,reasons=target['reasons'] if target else ['NO_COMPONENT_UNIT']))
                continue
            if target['member_refs']!=row['member_refs']:raise ValueError('Component changes occurrence order')
            eligible.append(ident)
            for link in component_links(c,target):
                donor=link['donor'];layout=tuple(map(str,pitches(*target['family'][1:],link['roles'])))
                totals['hypothesis_donor_links']+=1;pairs.add((row['group_ref'],donor['group_ref']))
                entry=layouts.setdefault(layout,dict(support={}))
                support=entry['support'].setdefault(ident,dict(roles=link['roles'],donor_hypothesis_refs=[],donor_group_refs=set()))
                if encoded(support['roles'])!=encoded(link['roles']):raise ValueError('Multiple spellings for one component assumption')
                support['donor_hypothesis_refs'].append(donor['id']);support['donor_group_refs'].add(donor['group_ref'])
        rendered=[]
        for layout,entry in sorted(layouts.items()):
            first=next(iter(entry['support']));target=units[first]
            changed=tuple(map(lambda x:str(F(x)),target['pitches']))!=layout
            support=[]
            for ident,s in sorted(entry['support'].items()):
                support.append(dict(target_hypothesis_ref=ident,roles=s['roles'],donor_hypothesis_refs=sorted(s['donor_hypothesis_refs']),donor_group_refs=sorted(s['donor_group_refs'])))
            complete=set(entry['support'])==set(all_ids)
            status=preflight(c,target,entry['support'][first]['roles'])if changed else dict(stage='UNCHANGED')
            rendered.append(dict(pitches=list(layout),changed=changed,support=support,
                support_class='ALL_ENUMERATED_TARGET_ASSUMPTIONS'if complete else'SOME_ENUMERATED_TARGET_ASSUMPTIONS',preflight=status))
            totals['unique_layouts']+=1;totals['changed_layouts']+=int(changed);totals['all_assumption_layouts'if complete else'some_assumption_layouts']+=1
            totals[status['stage']]+=1
        groups.append(dict(group_ref=row['group_ref'],member_refs=row['member_refs'],all_hypothesis_refs=all_ids,eligible_target_hypothesis_refs=eligible,refusals=refusals,layouts=rendered))
    totals.update(dict(exact_fit_groups=len(groups),eligible_target_groups=sum(bool(g['eligible_target_hypothesis_refs'])for g in groups),unique_source_target_pairs=len(pairs),unique_normalized_patterns=len(patterns),patterns_repeated_across_groups=sum(len(v)>1 for v in patterns.values())))
    return dict(schema='conditional-source-pattern-ledger/1',policy_activated=False,
        relation='Existing same-part/root/kind coupled inner-degree substitution; literal outer occurrences locked',
        scope='Source-supported conditional alternatives, before creative admission; all-assumption support is not harmonic truth, preference or playability',
        counts=dict(totals),groups=groups)


def validate(c,evidence,ledger):
    expected=build(c,evidence)
    if encoded(expected)!=encoded(ledger):raise ValueError('Stale, duplicated or incomplete conditional pattern ledger')
    return expected
