"""Fixed research model replay after experiment-cut canonicalization."""
import argparse,json
from pathlib import Path
from research_observation_cuts import prepare,canonicalize,restore
from diagnose_tonal_subdivision import sha
from ordered_tonal_factor import infer,public_observations


def run(study,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private output required')
    output.mkdir(parents=True);old=json.loads((study/'freeze.json').read_text());manifest_path=Path(next(p for p in old if p.endswith('manifest.json')));manifest=json.loads(manifest_path.read_text())
    selected=min((r for r in manifest['records'] if r['split']=='test'),key=lambda r:r['file'])
    root=Path(__file__).parent
    files=list(study.glob('*.json'))+[Path(p) for p in old]+[root/name for name in ('research_observation_cuts.py','run_research_observation_cuts.py','test_research_observation_cuts.py','diagnose_tonal_subdivision.py')]
    frozen={str(p.resolve()):sha(p) for p in files}
    for p,h in old.items():
        if sha(Path(p))!=h:raise ValueError('Original fixed-study seal differs')
    plan=dict(selected=selected,selection='Lexicographically first frozen test filename before prediction reads',frozen=frozen,transformation='Split only nonempty source-supported PC cells; retain rest cells and all original boundaries',scope='Research observation adapter only; no key accuracy improvement or full-source inverse claim')
    (output/'plan-before-inference.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    piece=json.loads((manifest_path.parent/selected['file']).read_text());rows=public_observations(piece['rows']);source={r['id']:r['active_note_refs'] for r in piece['rows'] if not r['quarantine_reasons']}
    packet,unsplit=prepare(rows,source);canonical=canonicalize(packet)
    if canonical['observations']!=rows or restore(canonical)!=packet:raise ValueError('Exact observation/support/cut roundtrip differs')
    (output/'cut-packet.json').write_text(json.dumps(packet),encoding='utf-8');(output/'canonical.json').write_text(json.dumps(canonical),encoding='utf-8')
    reports={}
    for kind in ('ordered','marginal'):
        model=json.loads((study/(kind+'-research-model.json')).read_text());saved=json.loads((study/(kind+'-test.json')).read_text());expected=next(p['prediction'] for p in saved['predictions'] if p['piece']==piece['piece'])
        baseline=infer(model,rows);adapted=infer(model,canonical['observations'])
        if baseline!=adapted:raise ValueError('Canonicalized fixed inference differs')
        error=max(abs(a-b) for x,y in zip(baseline['rows'],expected['rows']) for a,b in zip(x['posterior'],y['posterior']))
        if error>1e-12:raise ValueError('Saved fixed baseline replay differs')
        reports[kind]=dict(saved_baseline_maximum_error=error,canonicalized_inference_exact=True,posterior_changed_cells=0)
    unchanged=all(sha(Path(p))==h for p,h in frozen.items());report=dict(status='PASS_RESEARCH_CUT_INVARIANCE' if unchanged else 'FAIL_CHANGED',unchanged=unchanged,piece=piece['piece'],source_cells=len(piece['rows']),eligible_original_observations=len(rows),experiment_child_observations=len(packet['children']),rest_or_empty_support_not_split=unsplit,all_original_boundaries_preserved=True,exact_cut_packet_roundtrip=True,exact_source_support_preserved=True,models=reports,limitations=['Artificial cuts only; real source event/tie boundaries retained, not inferred picked attacks','No elapsed-time model or demonstrated key accuracy improvement','No product inference/detector/model parameter changes','Research licensed material remains private; not full-source Tier2 inverse gate'])
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=run(a.study,a.output);print(json.dumps(r));raise SystemExit(0 if r['unchanged'] else 1)
