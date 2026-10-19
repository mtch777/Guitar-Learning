"""Repeatable bounded source-annotation replay vs learned reconstruction.

Plans, source annotations, scores and reports are private local artifacts.
No source labels are passed to the learned method; source answers stay in replay
and evaluator code. This is an experimental probe, not musical acceptance.
"""
import json
import argparse
from pathlib import Path
from xml.etree import ElementTree as ET

from engine_contract import _read, _value, _selected, _scope, sha, audit_existing_edit
from recreation_window import fields, inside, redact, replay, overlay
from technique_edits import transact, enable_property
from technique_analysis import analyze, enabled
from exact_score import extract_score
from bend_analysis import bend_shape
from learned_performance import apply as performance
from sequence_palm_method import apply as sequence


def validate_partition(case,model,shapes=None):
    family=case.get('family')
    if not isinstance(family,str) or not family or 'training_families' not in model:
        raise ValueError('Explicit frozen family assignment and model partition evidence required')
    if case['song_id'] in model['training_songs'] or family in model['training_families']:
        raise ValueError('Source song/family was fitted')
    if case['feature']=='bend' and shapes is not None:
        if case['song_id'] in shapes['training_songs'] or family in shapes['families']:
            raise ValueError('Source song/family supplied training bend shapes')


def run(case, folder, performance_model, shapes_path, sequence_model):
    folder=Path(folder);folder.mkdir(exist_ok=False)
    source=Path(case['source']);feature=case['feature'];window=case['window']
    if sha(source)!=case['source_sha256']:raise ValueError('Source differs from frozen plan')
    mp=Path(sequence_model if feature=='palm_mute' else performance_model)
    model=json.loads(mp.read_text(encoding='utf-8'))
    if case['model_sha256']!=sha(mp):raise ValueError('Model differs from frozen plan')
    shapes=json.loads(Path(shapes_path).read_text(encoding='utf-8'))
    validate_partition(case,model,shapes)
    if feature!='palm_mute' and case['shapes_sha256']!=sha(shapes_path):raise ValueError('Shapes differ from frozen plan')
    _,_,_,original=_read(source)
    redact(source,folder/'hidden.gp',feature)
    replay(source,folder/'hidden.gp',folder/'replay.gp',feature)
    domain,names=fields(feature)
    _,_,_,restored=_read(folder/'replay.gp')
    if any(_value(r['note'],domain,names)!=_value(restored[o]['note'],domain,names) for o,r in original.items()):
        raise AssertionError('Source annotation replay differs')

    def propose(input_path,output_path):
        if feature=='palm_mute':return sequence(input_path,output_path,model,'Invent Animate',100,case['seed'],window=window)
        return performance(input_path,output_path,model,shapes,'Invent Animate',{feature:100},case['seed'])
    proposal=propose(folder/'hidden.gp',folder/'proposal.gp')
    audit=overlay(source,folder/'hidden.gp',folder/'proposal.gp',folder/'learned.gp',feature,window,proposal)
    mass=(model['tables']['global']['*'][0] if feature=='palm_mute' else
          next(t for t in model['tables'] if t['artist']=='Invent Animate' and t['context']=='*')['known'][feature])
    support=dict(known=True,eligible_mass_q=mass,denominator_unit='family_weighted_eligible_mass',model_sha256=sha(mp))
    code=Path(__file__).with_name('sequence_palm_method.py' if feature=='palm_mute' else 'learned_performance.py')
    contract=audit_existing_edit(source,folder/'learned.gp',audit,{feature:100},{feature:support},method=code.stem+'.apply/window-overlay',method_source=code)

    # Change every original target marker without altering locked note context.
    _,_,_,hidden=_read(folder/'hidden.gp');permissions={};edits={}
    for row in hidden.values():
        key=('note',row['note']['note_id'],domain);permissions[key]=names
        edits[key]=(['<Vibrato>Slight</Vibrato>'] if domain=='tag' else
                    [enable_property(n) for n in names if n in ('Bended','PalmMuted','HopoOrigin','HopoDestination')])
    transact(folder/'hidden.gp',folder/'perturbed.gp',edits,permissions)
    other=propose(folder/'perturbed.gp',folder/'perturbed-proposal.gp')
    if proposal['decisions']!=other['decisions']:raise AssertionError('Target values influence full-freedom proposals')

    truth=set()
    if feature in ('hammer_on_from_open','pull_off_to_open'):
        analysis=analyze(extract_score(source))
        truth={(p['origin_terminal'],p['destination']) for t in analysis['tracks'] for p in t['explicit_hopo']
               if p['direction']+'_'+p['context']==feature}
    confusion=dict(TP=0,FN=0,FP=0,TN=0);unknown=0;covered=set()
    for d in audit['decisions']:
        scope=_scope(feature,d);covered.update(o for o,_,_ in scope)
        if feature in ('hammer_on_from_open','pull_off_to_open'):y=(d['origin'],d['destination']) in truth
        else:
            labels=[_selected(original[o]['note'],feature,n) for o,domain,n in scope]
            if any(labels) and not all(labels):unknown+=1;continue
            y=all(labels)
        pred=d['proposed_selected'];confusion['TP' if y and pred else 'FN' if y else 'FP' if pred else 'TN']+=1
    for name in ('replay','learned'):
        path=folder/(name+'.gp');_,_,_,rows=_read(path)
        if feature=='bend':
            expected={o:bend_shape(r['note']['note_xml']) for o,r in rows.items() if inside(o,window)}
            path.with_suffix('.window-curves.json').write_text(json.dumps(expected),encoding='utf-8')
        elif feature=='palm_mute':
            expected={o:dict(palmMute=enabled(r['note']['note_xml'],'PalmMuted')) for o,r in rows.items()}
            path.with_suffix('.flags.json').write_text(json.dumps(expected),encoding='utf-8')
        else:path.with_suffix('.techniques.json').write_text(json.dumps(analyze(extract_score(path))),encoding='utf-8')
    result=dict(case=case,contract=contract,confusion=confusion,mixed_source_units=unknown,
                eligible_decisions=len(audit['decisions']),covered_note_occurrences=len(covered),
                ineligible_window_notes=sum(inside(o,window) and o not in covered for o in original),
                replay_target_fields_exact=True,target_perturbation_invariant=True,
                native_validation='pending',musical_acceptance=False)
    (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--performance-model',type=Path,required=True)
    parser.add_argument('--shapes',type=Path,required=True)
    parser.add_argument('--sequence-model',type=Path,required=True)
    args=parser.parse_args()
    cases=json.loads(args.plan.read_text(encoding='utf-8'))['cases']
    if len({c['case_id'] for c in cases})!=len(cases):raise ValueError('Unique case identities required')
    if any(Path(c['case_id']).name!=c['case_id'] or c['case_id'] in ('.','..') for c in cases):
        raise ValueError('Case identity must be a folder name')
    args.output.mkdir(exist_ok=False)
    records=[]
    for case in cases:
        try:
            result=run(case,args.output/case['case_id'],args.performance_model,args.shapes,args.sequence_model)
            records.append(dict(case_id=case['case_id'],eligible=result['eligible_decisions'],
                                confusion=result['confusion'],status='gpif_checked_native_pending'))
        except Exception as error:
            records.append(dict(case_id=case['case_id'],status='blocked',reason=type(error).__name__+': '+str(error)))
        (args.output/'execution.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        print(json.dumps(records[-1]),flush=True)
    if any(r['status']=='blocked' for r in records):raise SystemExit(1)
