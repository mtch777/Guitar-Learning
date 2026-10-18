"""Reproducible private pedal-policy experiment and exhaustive occurrence audit.

Inputs contain source-derived notes and human judgments and must stay private.
This evaluates software constraints and recorded labels, not population accuracy.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from pedal_evidence import analyze_evidence
from pedal_register import analyze_register


def verify(rows, result):
    byid = {n['occurrence']:n for n in rows}
    assert len(byid)==len(rows), 'Duplicate occurrence identity'
    assert set(result['roles']) <= byid.keys(), 'Invented occurrence'
    assert all(not byid[i]['tie_destination'] for i in result['roles']), 'Tie counted as attack'
    call_times={F(byid[i]['onset_q']) for i,role in result['roles'].items() if role=='call'}
    response_times={F(byid[i]['onset_q']) for i,role in result['roles'].items() if role=='response'}
    assert not call_times & response_times, 'Simultaneous source attacks labeled call and response'
    for cycle in result['cycles']:
        calls = [byid[i] for i in cycle['call_members']]
        answers = [byid[i] for i in cycle['response_members']]
        assert all(result['roles'][n['occurrence']]=='call' for n in calls)
        assert all(result['roles'][n['occurrence']]=='response' for n in answers)
        assert calls and answers, 'Empty exchange'
        assert max(F(n['onset_q']) for n in calls) < min(F(n['onset_q']) for n in answers), 'Same-onset answer'
        assert F(cycle['call_start_q']) < F(cycle['response_start_q']) < F(cycle['return_q'])
        call_times = {F(n['onset_q']) for n in calls}
        assert not call_times & {F(n['onset_q']) for n in answers}
    return True


def project_scopes(fixtures, analyses):
    """Do not mistake bounded-label agreement for context-stable acceptance."""
    index={(s['song_id'],s['part_id'],s['section_start']):s for s in analyses}
    records=[]
    for f in fixtures:
        roles={i:role for section in {n['section_start'] for n in f['rows']}
               for i,role in index.get((f['song_id'],f['part_id'],section),{}).get('roles',{}).items()}
        marked=f.get('feedback',{}).get('selected_notes',[])
        missing=[n['occurrence'] for n in marked if roles.get(n['occurrence'])!='call']
        unexpected=[n['occurrence'] for n in f['rows'] if roles.get(n['occurrence'])=='call'] if not f['expected'] else []
        records.append(dict(song=f['song'],track=f['track'],bars=f['bars'],marked_notes=len(marked),
                            missing_marks=missing,call_notes_in_excluded_excerpt=unexpected))
    return records


def evaluate(fixtures, scopes, out):
    algorithm_path=Path(__file__).with_name('pedal_evidence.py')
    algorithm_sha256=hashlib.sha256(algorithm_path.read_bytes()).hexdigest()
    out.mkdir(parents=True, exist_ok=False)
    policies = {
        'timing_only':dict(identity=False,connectivity=False,arpeggio=False,standalone=False,return_identity=False,low_position=False),
        'without_local_identity':dict(identity=False),
        'without_connectivity':dict(connectivity=False),
        'without_arpeggio_exclusion':dict(arpeggio=False),
        'without_standalone_evidence':dict(standalone=False),
        'without_anchor_return':dict(return_identity=False),
        'without_low_position':dict(low_position=False),
        'combined':dict(),
    }
    experiments={}
    for name, policy in policies.items():
        records=[]
        for f in fixtures:
            result=analyze_evidence(f['rows'],**policy);verify(f['rows'],result)
            marked=f.get('feedback',{}).get('selected_notes',[])
            misses=[n['occurrence'] for n in marked if result['roles'].get(n['occurrence'])!='call']
            records.append(dict(song=f['song'],track=f['track'],bars=f['bars'],expected=f['expected'],
                accepted=result['accepted'],matches=f['expected']==result['accepted'],
                marked_notes=len(marked),missed_marks=misses,anchor_pitches=result['anchor_pitches'],
                roles=result['roles'],cycles=result['cycles']))
        experiments[name]=dict(policies=policy,passages=len(records),
            matching_passages=sum(r['matches'] for r in records),
            marked_notes=sum(r['marked_notes'] for r in records),
            missed_marks=sum(len(r['missed_marks']) for r in records),records=records)
    counts=Counter();analyses=[];changes=[]
    for scope in scopes:
        rows=scope['rows'];before=analyze_register(rows);after=analyze_evidence(rows);verify(rows,after)
        key={k:scope[k] for k in ['song_id','part_id','section_start']}
        counts['scopes']+=1;counts['before_accepted']+=before['accepted'];counts['after_accepted']+=after['accepted']
        changed={i:dict(before=before['roles'].get(i,'context'),after=after['roles'].get(i,'context'))
                 for i in set(before['roles'])|set(after['roles'])
                 if before['roles'].get(i)!=after['roles'].get(i)}
        counts['changed_role_occurrences']+=len(changed)
        counts['lost_scopes']+=before['accepted'] and not after['accepted']
        counts['gained_scopes']+=after['accepted'] and not before['accepted']
        if changed:changes.append(dict(key,before_accepted=before['accepted'],after_accepted=after['accepted'],changes=changed))
        analyses.append(dict(key,**{k:after[k] for k in ['accepted','anchor_pitches','roles','cycles','reason']}))
    projection=project_scopes(fixtures,analyses)
    summary=dict(experiments={name:{k:v for k,v in value.items() if k!='records'} for name,value in experiments.items()},
        corpus=dict(counts),algorithm_sha256=algorithm_sha256,
        scope_validation=dict(marked_notes=sum(r['marked_notes'] for r in projection),
            missing_marks=sum(len(r['missing_marks']) for r in projection),
            excluded_excerpts_with_full_scope_calls=sum(bool(r['call_notes_in_excluded_excerpt']) for r in projection)),
        limitations=['Recorded-label agreement is not independent accuracy.',
                    'Corpus role changes have mathematical audits, not human listening acceptance.',
                    'Median-gap multiplier and recurrence counts are experimental policies, not musical laws.'])
    if hashlib.sha256(algorithm_path.read_bytes()).hexdigest()!=algorithm_sha256:
        raise RuntimeError('Detector changed during evaluation; refuse to seal mixed-version results')
    for name,value in [('summary',summary),('experiments',experiments),('corpus-analysis',analyses),('changes',changes),('scope-projection',projection)]:
        (out/(name+'.json')).write_text(json.dumps(value,separators=(',',':')),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['fixtures','scopes','out']:p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Source-derived output must stay private')
    evaluate(json.loads(a.fixtures.read_text(encoding='utf-8')),json.loads(a.scopes.read_text(encoding='utf-8')),a.out)
