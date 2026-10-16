"""Reproduce the exploratory pipeline into a NEW private workspace.

Does not download weights, accept licenses, overwrite baselines, or invent a
musical verdict. Dependencies and authorized inputs must already be installed.
"""
import argparse,json,subprocess,sys,time
from pathlib import Path
from exact_score import extract_score
from sounding_graph import build_sounding,audit_sounding


def main():
    p=argparse.ArgumentParser()
    for name in ('cloud','sweet','archive','models','alphatab','node','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--count',type=int,default=100);p.add_argument('--pool-count',type=int,default=128)
    a=p.parse_args();repo=Path(__file__).resolve().parents[1];root=a.out.resolve()
    if not root.is_relative_to(repo/'composition-lab/local-artifacts'):p.error('Output must remain under private local-artifacts')
    if not 1<=a.count<=1000:p.error('Count must be 1–1000')
    for name in ('cloud','sweet','archive','alphatab','node'):
        if not getattr(a,name).is_file():p.error('Missing input: '+name)
    if not a.models.is_dir():p.error('Missing local models')
    root.mkdir(parents=True,exist_ok=False)
    journal=[]
    def run(script,*args,node=False):
        command=[str(a.node if node else sys.executable),str(repo/'composition-lab'/script),*map(str,args)]
        entry=dict(command=command,started=time.time());journal.append(entry)
        (root/'commands.json').write_text(json.dumps(journal,indent=2))
        with (root/(str(len(journal))+'.log')).open('w',encoding='utf-8') as stream:
            result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,cwd=repo)
        entry.update(returncode=result.returncode,finished=time.time());(root/'commands.json').write_text(json.dumps(journal,indent=2))
        if result.returncode:raise RuntimeError('Stage failed; preserved log '+str(len(journal))+'.log')
    run('benchmarks/freeze_evidence.py','--out',root/'frozen-evidence.json')
    representation={}
    for family in ('cloud','sweet'):
        score=extract_score(getattr(a,family));graph=build_sounding(score)
        (root/(family+'.canonical.json')).write_text(json.dumps(score))
        (root/(family+'.sounding.json')).write_text(json.dumps(graph))
        representation[family]=audit_sounding(score,graph)
    (root/'representation-audit.json').write_text(json.dumps(representation,indent=2))
    run('research_corpus.py','--archive',a.archive,'--out',root/'corpus','--limit',2000)
    run('structural_learning.py','--corpus',root/'corpus/corpus.json','--out',root/'structure-v2')
    run('build_neural_pool.py','--models',a.models,'--corpus',root/'corpus/corpus.json','--out',root/'neural-pool.json','--count',a.pool_count)
    run('composition_engine.py','--workspace',root,'--count',a.count,'--bars',64)
    run('verify_gp.mjs',a.alphatab,*sorted((root/'compositions').glob('*.gp')),node=True)
    run('batch_validation.py','--workspace',root,'--report-name','validation-report-v2.json')
    # Historical generated references remain at the sibling baseline locations.
    run('build_final_review.py','--workspace',root)
    print('Pipeline artifacts ready; musical acceptance remains unjudged:',root)


if __name__=='__main__':main()
