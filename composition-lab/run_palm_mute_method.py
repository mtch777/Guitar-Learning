"""Private palm-mute fit and controlled GP exports on generated inputs."""
import argparse,json,hashlib,shutil
from pathlib import Path
from palm_mute_method import train,observations,apply
from artist_profiles import evaluate
from exact_score import extract_score
from technique_analysis import enabled

def run(report_path,baselines,out,pattern='*-100.gp',artist='Invent Animate'):
    out.mkdir(parents=True,exist_ok=False)
    files=[Path(__file__),Path(__file__).with_name('palm_mute_method.py')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    report=json.loads(report_path.read_text(encoding='utf-8'));model=train(report)
    (out/'model.json').write_text(json.dumps(model),encoding='utf-8');evaluation=evaluate(model,observations(report))
    (out/'evaluation.json').write_text(json.dumps(evaluation,indent=2),encoding='utf-8');records=[]
    for src in sorted(baselines.glob(pattern)):
        for strength in (0,50,100):
            dst=out/f'{src.stem}-palm-{strength:03d}.gp';audit=apply(src,dst,model,artist,strength)
            dst.with_suffix('.control.json').write_text(json.dumps(audit),encoding='utf-8')
            shutil.copyfile(src.with_suffix('.expected.json'),dst.with_suffix('.expected.json'))
            # Palm muting must not reset the approved vibrato preview depth or
            # discard independent expectations for otherwise locked techniques.
            for suffix in ('.playback.json','.curves.json','.techniques.json'):
                if src.with_suffix(suffix).exists():shutil.copyfile(src.with_suffix(suffix),dst.with_suffix(suffix))
            score=extract_score(dst);flags={}
            for ti,t in enumerate(score['tracks']):
                for m in t['measures']:
                    for vi,v in enumerate(m['voices']):
                        for ei,e in enumerate(v):
                            for ni,n in enumerate(e['notes']):flags[f'{ti}:{m["number"]}:{vi}:{ei}:{ni}']=dict(palmMute=enabled(n['note_xml'],'PalmMuted'))
            dst.with_suffix('.flags.json').write_text(json.dumps(flags),encoding='utf-8')
            records.append(dict(file=dst.name,strength=strength,sha256=audit['sha256'],
                zero_identity=audit['byte_identity'],opportunities=len(audit.get('decisions',[])),
                applied_proposals=sum(d['released'] and d['proposed_selected'] for d in audit.get('decisions',[])),
                actual_palm_muted_notes=sum(v['palmMute'] for v in flags.values())))
            print(json.dumps(records[-1]),flush=True)
    if not records:raise ValueError('No matching generated baselines')
    if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:raise AssertionError('Code changed during run')
    (out/'batch.json').write_text(json.dumps(dict(outputs=records,code_sha256=hashes,
        source_group_inventory=model['source_group_inventory'],musical_acceptance=False),indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('report','baselines','out'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    run(a.report,a.baselines,a.out)
