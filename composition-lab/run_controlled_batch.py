"""Repeatable private multi-core control sweep; failures never become completions."""
import argparse,json
from pathlib import Path
from compose_controlled import run,CONTROLS,amounts


def batch(baselines,config,out,strengths=(0,50,100)):
    if not isinstance(config,dict):raise ValueError('Configuration object required')
    dimensions=config.get('dimensions',list(CONTROLS))
    if not isinstance(dimensions,(list,tuple)) or not dimensions or not all(isinstance(d,str) for d in dimensions) or len(dimensions)!=len(set(dimensions)):raise ValueError('Unique nonempty control dimensions required')
    amounts({d:0 for d in dimensions})
    if not isinstance(strengths,(list,tuple)) or not strengths:raise ValueError('Nonempty strengths required')
    for strength in strengths:amounts({d:strength for d in dimensions})
    if len(strengths)!=len(set(strengths)):raise ValueError('Unique strengths required')
    if set(config)-{'models','artist','seed','dimensions','form_plans'}:raise ValueError('Unknown batch configuration fields')
    sources=sorted(baselines.glob('*.gp'))
    if not sources:raise ValueError('No generated core inputs')
    plans=config.get('form_plans',{})
    if not isinstance(plans,dict) or set(plans)-{p.name for p in sources} or any(not isinstance(v,(str,Path)) or not str(v) for v in plans.values()):
        raise ValueError('Form plans must map input filenames to explicit local paths')
    out.mkdir(parents=True,exist_ok=False)
    records=[];failures=[];code=None;models={};inputs={}
    for source in sources:
        for strength in strengths:
            target=out/f'{source.stem}-{strength:03d}'
            try:
                result=run(source,config.get('models',{}),{d:strength for d in dimensions},target,
                    config.get('seed',17),config.get('artist'),plans.get(source.name))
                identity=dict(gp=result['source_sha256'],expected=result['source_expected_sha256'],form_plan=result.get('form_plan_sha256'))
                if source.name in inputs and inputs[source.name]!=identity:raise AssertionError('Input changed between batch cases')
                inputs[source.name]=identity
                if code is None:code=result['code_sha256']
                if code!=result['code_sha256']:raise AssertionError('Implementation changed between batch cases')
                for key,value in result['model_sha256'].items():
                    if key in models and models[key]!=value:raise AssertionError('Model changed between batch cases')
                    models[key]=value
                records.append(dict(source=source.name,directory=target.name,strength=strength,
                    sha256=result['output_sha256'],zero_identity=result['all_zero_byte_identity']))
            except Exception as exc:
                # Preserve incomplete folders for diagnosis; do not label them
                # successful or overwrite them on retry. Continue independent cases.
                failures.append(dict(source=source.name,strength=strength,directory=target.name,
                    error_type=type(exc).__name__,reason=str(exc)))
    result=dict(schema='controlled-empirical-batch-v1',dimensions=dimensions,strengths=list(strengths),
        outputs=records,failures=failures,complete=not failures,code_sha256=code,model_sha256=models,input_sha256=inputs,
        musical_acceptance=False,limitations=['Completion means requested exports only; independent native checks still required.',
            'Shared seed, fixed-stage release masks; combined changes are not globally nested or perceptual percentages.'])
    (out/'batch.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baselines','config','out'):p.add_argument(name,type=Path)
    p.add_argument('--strengths',type=int,nargs='+',default=[0,50,100]);a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Fresh private output directory required')
    result=batch(a.baselines,json.loads(a.config.read_text(encoding='utf-8')),a.out,a.strengths)
    print(json.dumps(dict(exports=len(result['outputs']),failures=len(result['failures']),complete=result['complete'])))
    if not result['complete']:raise SystemExit(1)
