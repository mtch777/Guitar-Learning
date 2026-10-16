"""Preserve generated controls and aggregate evidence; never package sources/weights."""
import argparse,hashlib,json,statistics,zipfile
from pathlib import Path
from engine_controls import vary
from gp_author import write_gp
from batch_validation import constraints
from benchmarks.freeze_evidence import sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--aggregate',type=Path,required=True);a=p.parse_args();root=a.workspace
    report=json.loads((root/'validation-report-v2.json').read_text());pool=json.loads((root/'neural-pool.json').read_text())['pool']
    base=json.loads(next((root/'compositions').glob('*.expected.json')).read_text());folder=root/'control-examples';folder.mkdir(exist_ok=False)
    controls=[]
    for dimension in ('harmony','melody','rhythm'):
        for target in (0,25,50,75,100):
            score,evidence=vary(base,{dimension:target},pool,17);assert not constraints(score)['violations']
            path=folder/(dimension+'-'+str(target)+'.gp');write_gp(score,path,title=path.stem)
            path.with_suffix('.expected.json').write_text(json.dumps(score));controls.append(dict(file=path.name,**evidence))
    (folder/'measurements.json').write_text(json.dumps(controls,indent=2))
    dimension_means={}
    for d in ('harmony','melody','rhythm'):
        dimension_means[d]={str(t):statistics.mean(r['actual'][d] for r in report['controls'] if r['dimension']==d and r['target']==t and 'infeasible' not in r) for t in (0,25,50,75,100)}
    from scipy.stats import spearmanr
    correlations=[]
    for piece in range(20):
        for seed in (17,29,41,53,67):
            for d in dimension_means:
                rows=[r for r in report['controls'] if r['piece']==piece and r['seed']==seed and r['dimension']==d]
                correlations.append(float(spearmanr([r['target'] for r in rows],[r['actual'][d] for r in rows]).statistic))
    frozen=json.loads((root/'frozen-evidence.json').read_text())['files'];repo=Path(__file__).resolve().parents[1]
    changed=[name for name,entry in frozen.items() if not (repo/name).is_file() or sha(repo/name)!=entry['sha256']]
    if changed:raise AssertionError('Frozen inputs changed; inspect private manifest')
    structure=json.loads((root/'structure-v3/report.json').read_text());engine=json.loads((root/'engine-report.json').read_text())
    aggregate=dict(format='composition-autonomous-results-v1',frozen_files_verified=len(frozen),
        corpus=json.loads((root/'corpus/summary.json').read_text()),representation=json.loads((root/'representation-audit.json').read_text()),
        structure=structure,roles=engine['role_cross_song'],batch=report['summary'],
        controls=dict(means=dimension_means,min_spearman=min(correlations),sweeps=len(correlations),
            exact_zero_violations=sum(any(v!=0 for d,v in r['actual'].items() if r['requested'].get(d,0)==0) for r in report['controls'] if 'actual' in r),
            unsupported=['independent structure','independent role reassignment'],perceptual_calibration=False),
        exact_relative_match_totals={str(n):sum(o['exact_relative_matches'][str(n)] for o in report['outputs']) for n in (8,16,32)},
        quality_verdict=None,human_review='pending',commercial_rights='not established; research outputs private',
        generated_gp_sha256={p.name:sha(p) for p in sorted((root/'compositions').glob('*.gp'))})
    a.aggregate.write_text(json.dumps(aggregate,indent=2),encoding='utf-8')
    archive=root/'Composition_Lab_Generated_Review.zip'
    if archive.exists():raise FileExistsError('Preserve existing package')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for folder_name in ('compositions','control-examples'):
            for path in sorted((root/folder_name).glob('*.gp')):z.write(path,folder_name+'/'+path.name)
        z.write(root/'consolidated-review-v2.json','consolidated-review-v2.json')
        z.write(a.aggregate,'aggregate-results.json')
        z.writestr('README.txt','Private noncommercial research outputs. 100 generated 64-bar GP scores and 15 control examples.\nLoad consolidated-review-v2.json in composition-ablation-review.html?study=final (file picker or paste JSON).\nPreview is a simple synthesizer; GP files allow instrument playback. No musical quality/originality certification.\nFailed boundary/form targets and incomplete structure/role controls are recorded in aggregate-results.json.\nThe 22-case review includes two shorter historical generated references; comparisons are exploratory.\nNo commercial source scores, private annotations, training corpus, checkpoints or secrets are included.\n')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None and len(z.namelist())==118
    print(json.dumps(dict(frozen_unchanged=len(frozen),archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),controls=aggregate['controls'])))


if __name__=='__main__':main()
