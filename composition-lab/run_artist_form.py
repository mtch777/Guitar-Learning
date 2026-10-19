"""Private author-marker form baseline and new-score recurrence experiments."""
import argparse,json,hashlib
from copy import deepcopy
from pathlib import Path
from artist_form import observations,fit,evaluate,plan,arrange,full_plan,select_length_weight
from artist_profiles import connected_families
from corpus_composer import learn,generate
from gp_author import write_gp

def run(report_path,corpus,composer_path,baselines,out,content=False,full=False,role_model_path=None):
    out.mkdir(parents=True,exist_ok=False)
    files=[Path(__file__),Path(__file__).with_name('artist_form.py'),Path(__file__).with_name('gp_author.py'),Path(__file__).with_name('corpus_composer.py')]
    if content:files.append(Path(__file__).with_name('content_form.py'))
    if role_model_path:
        files.extend(Path(__file__).with_name(n) for n in ('role_pitch_transfer.py','role_pitch_model.py'))
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    report=json.loads(report_path.read_text(encoding='utf-8'));connected_families(report['songs']);composer=json.loads(composer_path.read_text(encoding='utf-8'))
    held=deepcopy(report);held['songs']=[s for s in held['songs'] if s['provisional_partition']=='held_out']
    for song in held['songs']:song['provisional_partition']='development'
    held_composer=learn(held,corpus,composer['artist'])
    selection=dict(parts=dict(harmony={**composer['parts']['harmony'],**held_composer['parts']['harmony']}))
    extractor=observations
    if content:
        from content_form import observations as extractor
    forms,excluded=extractor(report,selection);model=select_length_weight(forms,composer['artist']) if full else fit(forms,composer['artist']);evaluation=evaluate(model,forms)
    if content:
        model['schema']='exact-content-form-v1'
        model['limitations']=['Exact transposition-relative written main-voice timeline periods only; static sections abstain.',
            'Original occurrences, resolved tie lengths, unknown-pitch symbols and zero-time grace identities preserved.',
            'Source author boundaries retained; no inferred thematic/functional intent.',
            'Length-predictor evaluation is not likelihood of the return-aware generation process.']
    for name,value in [('model',model),('evaluation',evaluation)]:
        (out/(name+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
    records=[];rejections=[]
    sources=range(4) if full else sorted(baselines.glob('*.expected.json'))
    role_model=json.loads(role_model_path.read_text(encoding='utf-8')) if role_model_path else None
    for i,src in enumerate(sources):
        if full:
            for retry in range(40):
                sections=full_plan(model,1700+i*100+retry);bars=sum(s['length'] for s in sections)
                if bars>512:rejections.append(dict(piece=i,attempt=retry,reason='explicit512bar resource bound'));continue
                try:
                    core,_=generate(composer,bars,10000+i*100+retry)
                    if role_model:
                        from role_pitch_transfer import apply
                        core,_=apply(core,['harmony','melody','bass'],composer,role_model,100)
                except ValueError as exc:rejections.append(dict(piece=i,attempt=retry,reason=str(exc)));continue
                break
            else:raise ValueError('No valid full form/core within explicit retry budget')
            label=f'full-{i+1:03d}'
        else:
            core=json.loads(src.read_text(encoding='utf-8'));sections=plan(model,len(core['tracks'][0]['measures']),1700+i);label=src.name.removesuffix('.expected.json')
        score=arrange(core,sections)
        dst=out/(label+'-form.gp');write_gp(score,dst,title='Source-content form experiment' if content else 'Author-marker form experiment')
        dst.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8');dst.with_suffix('.plan.json').write_text(json.dumps(sections),encoding='utf-8')
        records.append(dict(file=dst.name,sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),bars=len(score['tracks'][0]['measures']),sections=len(sections),returns=sum(s['return_lag']>0 for s in sections)))
        print(json.dumps(records[-1]),flush=True)
    if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:raise AssertionError('Code changed during experiment')
    (out/'batch.json').write_text(json.dumps(dict(outputs=records,code_sha256=hashes,excluded=excluded,rejected_proposals=rejections,musical_acceptance=False),indent=2),encoding='utf-8')
    print(json.dumps(dict(development_forms=len(model['training_songs']),heldout=evaluation,outputs=len(records),returns=sum(r['returns'] for r in records),excluded=excluded)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('report','corpus','composer','baselines','out'):p.add_argument(name,type=Path)
    p.add_argument('--content',action='store_true');p.add_argument('--full',action='store_true');p.add_argument('--role-model',type=Path);a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    run(a.report,a.corpus,a.composer,a.baselines,a.out,a.content,a.full,a.role_model)
