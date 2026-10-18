"""Run private development-only profiles and held-out annotation comparisons."""
import argparse,hashlib,json
from pathlib import Path
from artist_profiles import observations,fit,evaluate,describe,stable_hash


def run(report,pedal_expansion,out,coverage=()):
    out.mkdir(parents=True,exist_ok=False)
    implementation=Path(__file__).with_name('artist_profiles.py')
    code_hash=hashlib.sha256(implementation.read_bytes()).hexdigest()
    runner_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    roles={}
    for t in pedal_expansion['tracks']:
        roles[t['song_id'],t['part_id']]={k:v for p in t['phrases'] for k,v in p['roles'].items()}
    events,excluded=observations(report,roles,pedal_coverage=set(roles)|set(coverage))
    models={};scores={}
    for weighting in ('pooled','song','family'):
        model=fit(events,weighting=weighting);models[weighting]=model;scores[weighting]=evaluate(model,events)
        (out/(weighting+'-model.json')).write_text(json.dumps(model,separators=(',',':')),encoding='utf-8')
    # Prove held-out outcome/context mutations cannot affect fitting. Only the
    # test copy changes; the authoritative source report remains untouched.
    altered=[dict(e,labels=['dead'],context='perturbed-heldout') if e['partition']=='held_out' else e for e in events]
    invariant=fit(altered)==models['family']
    assert invariant,'Held-out data affected fitting'
    summary=dict(schema='artist-profile-evaluation-v1',events=len(events),excluded=excluded,
        training_events=models['family']['training_events'],training_songs=len(models['family']['training_songs']),
        training_families=len(models['family']['training_families']),heldout_fit_invariant=invariant,
        artist_labels=sorted({e['artist'] for e in events}),metrics=scores,
        provenance=dict(observations_sha256=stable_hash(events),pedal_expansion_sha256=pedal_expansion['algorithm_sha256'],
            profile_code_sha256=code_hash,runner_sha256=runner_hash),
        limitations=['Source-notation annotation prediction, not performed technique accuracy or musical quality.',
            'Title families are conservative leakage groups, not verified work identities.',
            'AI/junk-flagged entries remain descriptive only; temporal-ineligible tracks excluded.',
            'GP conversion-fidelity flags require separate transfer/export checks; analysis reads cached raw notation.',
            'Absence of an annotation is not evidence of absent performance.'])
    (out/'observations.json').write_text(json.dumps(events,separators=(',',':')),encoding='utf-8')
    (out/'descriptive.json').write_text(json.dumps(describe(events),separators=(',',':')),encoding='utf-8')
    assert code_hash==hashlib.sha256(implementation.read_bytes()).hexdigest(),'Implementation changed during run; results unsealed'
    assert runner_hash==hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'Runner changed during run; results unsealed'
    (out/'evaluation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('metrics','provenance','limitations')}),flush=True)
    print(json.dumps({k:v['metrics'] for k,v in scores.items()}),flush=True)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('report','pedal_expansion','out'):p.add_argument(n,type=Path)
    p.add_argument('--pedal-coverage',type=Path,help='Existing sealed full-scope analysis; never reruns detection')
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    coverage={(r['song_id'],r['part_id']) for r in json.loads(a.pedal_coverage.read_text(encoding='utf-8'))} if a.pedal_coverage else ()
    run(json.loads(a.report.read_text(encoding='utf-8')),json.loads(a.pedal_expansion.read_text(encoding='utf-8')),a.out,coverage)
