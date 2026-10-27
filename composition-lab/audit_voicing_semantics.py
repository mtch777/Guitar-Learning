"""Complete fixed-development semantic accounting; no edit proposal policy."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import voicing_semantics as semantics
from voicing_families import realize
import musical_tier2 as music
from context_spacing_study import CASES


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(trial,output,case_names=CASES):
    if output.exists()or'local-artifacts'not in output.resolve().parts:raise ValueError('Fresh private output required')
    root=Path(__file__).parent
    files=list(root.glob('*.py'))+[trial/s/name for s in case_names for name in ('stripped-tier2.json','catalog.json','source-witness-audit.json')]
    hashes={str(p.resolve()):sha(p)for p in files};output.mkdir(parents=True)
    (output/'freeze-before-audit.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    cases=[];illustrations={};signatures={}
    for song in case_names:
        upper=json.loads((trial/song/'stripped-tier2.json').read_text(encoding='utf-8'))
        core=realize(upper['musical_relationships']);counts=Counter();views=[]
        for group in core['coattacks']:
            counts['all_groups']+=1;counts['all_members']+=len(group['members'])
            hypotheses=group['interpretation']['chord_candidates']
            view=semantics.describe(group,hypotheses);semantics.validate_view(group,hypotheses,view)
            views.append(view);counts['hypotheses']+=len(hypotheses)
            counts['groups_without_hypothesis'if not hypotheses else'groups_with_hypothesis']+=1
            counts['incomplete_groups']+=not view['complete']
            for h in view['hypotheses']:
                for member in h['members']:
                    p=music.member_pitch(group,next(m for m in group['members']if m['id']==member['id']))
                    if member['coordinates']is None:
                        if p is not None:raise ValueError('Known pitch lost')
                        continue
                    restored=semantics.pitch_coordinate(root_pc=h['hypothesis']['root_pc'],coordinates=member['coordinates'])['pitch']
                    if restored!=p:raise ValueError('Same-relation coordinate inverse mismatch')
                    counts['conditional_coordinates_exact']+=1
                if view['complete']:
                    result=semantics.check(group,group,hypotheses,hypotheses,['harmonic_hypotheses','observed_formula_support','formula_membership','occurrence_ids','doubling','inversion','bass_pitch','spacing','member_pitch_classes','member_register','pitches'])
                    if result['status']!='PASS_CONDITIONAL_SEMANTIC_LOCKS':raise ValueError(result)
                    counts['identity_lock_checks']+=1
                # No edited source: examples compare actual observations only.
                key=h['hypothesis']['id'];pitch_values=[music.member_pitch(group,m)for m in group['members']]
                witness=dict(song=song,group_ref=group['id'],part_id=group['part_id'],bar=group['bar'],onset_q=group['onset_q'],
                    hypothesis=h['hypothesis'],pitches=pitch_values,doubling=h['realized_semitone_multiplicity'],bass_role=h['bass_semitone_role'])
                previous=signatures.setdefault(key,[])
                def relative(values):return None if not values or any(p is None for p in values)else sorted(F(p)-min(map(F,values))for p in values)
                for old in previous:
                    kind='changed_doubling'if old['doubling']!=witness['doubling']else'changed_inversion'if old['bass_role']!=witness['bass_role']else'different_spacing'if relative(old['pitches'])!=relative(pitch_values)else None
                    if kind and kind not in illustrations:illustrations[kind]=dict(first=old,second=witness,
                        scope='Two observed conditional descriptions, not an edit witness, voice correspondence or adjudicated harmony')
                if len(previous)<20:previous.append(witness)
            if hypotheses:
                stale=deepcopy(view);stale['hypotheses'][0]['bass_formula_slot']='tampered'
                try:semantics.validate_view(group,hypotheses,stale)
                except ValueError:counts['stale_views_rejected']+=1
                else:raise ValueError('Stale view accepted')
        evidence=json.loads((trial/song/'source-witness-audit.json').read_text(encoding='utf-8'))
        catalog=json.loads((trial/song/'catalog.json').read_text(encoding='utf-8'));byid={r['id']:r for r in catalog['units']}
        audible=0;physical=0;total=0
        for row in evidence['rows']:
            original=byid[row['target_ref']]['realization']
            for choice in row['options']:
                total+=1;value=choice['realization']
                a=[F(original['anchor'])+F(x)for x in original['intervals']]
                b=[F(value['anchor'])+F(x)for x in value['intervals']]
                audible+=a!=b
                physical+=a==b and value.get('strings')!=byid[row['target_ref']]['fixed_output_strings']
        (output/(song+'-semantic-views.json')).write_text(json.dumps(views,indent=2),encoding='utf-8')
        cases.append(dict(song=song,counts=dict(counts),admitted_options=total,pitch_changing_options=audible,fingering_only_options=physical))
    if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen implementation/input changed')
    result=dict(status='PASS_CONDITIONAL_SEMANTIC_ACCOUNTING',cases=cases,source_illustrations=illustrations,
        audible_status='NO_PITCH_CHANGING_OPTION_IN_CURRENT_APPROVED_SCOPE'if not any(c['pitch_changing_options']for c in cases)else'REQUIRES_NONZERO_INVERSE_GP_AND_LISTENING',
        gates=dict(qa1='SEE_CAPTURE_MANIFEST: this accounting does not itself establish freshness',qa2='coordinate_equation_exact; existing full inverse regression separate; no new pitch ownership',
                   qa3='conditional semantic lock contracts; not established chord roots, learned preference or musical quality'))
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return {k:v for k,v in result.items()if k!='source_illustrations'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('trial',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--cases',nargs='+',default=list(CASES));args=parser.parse_args()
    print(json.dumps(run(args.trial,args.output,tuple(args.cases))))
