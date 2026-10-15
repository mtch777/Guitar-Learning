"""Exploratory generator/refiner/selector chain, with explicit authored schedule."""
import argparse
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks.learned_organization import load_model,tensor,generate,sample_encoder,unique,digest,private_output
from learned_phrase_adapter import examples,decode,make_score
from exact_score import extract_score
from gp_author import write_gp
from generation_validation import copying_ngrams


def selector_model(folder):
    import torch
    from transformers import BertConfig,BertForSequenceClassification
    model=BertForSequenceClassification(BertConfig.from_json_file(folder/'config.json'))
    model.load_state_dict(torch.load(folder/'pytorch_model.bin',map_location='cpu',weights_only=True),strict=True)
    model.eval();return model


def rank(model,context,target,vocab):
    import torch
    tokens=['BOS']+[t for t in context if t not in ('BOS','EOS')]+['SEP']+[t for t in target if t not in ('BOS','EOS')]+['EOS']
    if len(tokens)>512:raise ValueError('Selector pair too long')
    with torch.inference_mode():return float(model(tensor(tokens,vocab)).logits[0,-1].sigmoid())


def mask_motif(tokens,kind):
    mask='COR_PITCH_MASK' if kind=='pitch' else 'COR_DURATION_MASK'
    prefixes=('Pitch_',) if kind=='pitch' else ('Duration_','Position_')
    # The released tokenizer has only COR controls, not literal content-mask
    # symbols. Official token filtering removes masked pitch or onset/duration
    # fields; reproduce that intentionally, not by dropping source tokens.
    return [t for t in tokens if t not in ('BOS','EOS') and not t.startswith(prefixes)],mask


def main():
    import torch
    p=argparse.ArgumentParser();p.add_argument('--models',type=Path,required=True);p.add_argument('--sources',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();private_output(args.out);args.out.mkdir(exist_ok=False,parents=True);torch.set_num_threads(2)
    vocab=json.loads((args.models/'tokenizer.json').read_text())
    generator=load_model(args.models/'phrase_generation');refiner=load_model(args.models/'phrase_refinement');selector=selector_model(args.models/'phrase_selection')
    sources={k:extract_score(args.sources/f) for k,f in [('cloud','Cloud Cascade (Tuned Down).gp'),('sweet',"Sweet Child O' Mine.gp")]}
    report=dict(protocol='LEARNED_ORGANIZATION.md follow-up',checkpoints={k:digest(args.models/k/'pytorch_model.bin') for k in ('phrase_generation','phrase_refinement','phrase_selection')},
                schedule=['generator','generator','pitch-mask-refiner','duration-mask-refiner'],selector_tests={},chains=[])
    for family,source in sources.items():
        ti=0 if family=='cloud' else 3;track=source['tracks'][ti]
        data=unique(examples(source,ti,vocab)[0])[:8];rows=[]
        for i,row in enumerate(data):
            wrong=next((data[(i+j)%len(data)]['target'] for j in range(1,len(data)) if data[(i+j)%len(data)]['target']!=row['target']),None)
            if wrong is not None:rows.append(dict(start_bar=row['start_bar'],real=rank(selector,row['context'],row['target'],vocab),wrong=rank(selector,row['context'],wrong,vocab)))
        report['selector_tests'][family]=dict(rows=rows,correct_rankings=sum(r['real']>r['wrong'] for r in rows),pairs=len(rows))
        print('selector',family,report['selector_tests'][family],flush=True)
        for mode in ('generator-only','refiner-selector'):
            for seed in (17,29):
                prior=data[0]['context'];motif=None;all_notes=[];trace=[]
                for block in range(4):
                    candidates=[]
                    for ci in range(1 if mode=='generator-only' else 3):
                        candidate_seed=seed+block*100+ci
                        try:
                            if mode=='refiner-selector' and block>=2:
                                masked,control=mask_motif(motif,'pitch' if block==2 else 'duration')
                                encoder=['BOS']+[t for t in prior if t not in ('BOS','EOS')]+['SEP','CA_True' if block==3 else 'CA_False',control,'SEP']+masked+['EOS']
                                tokens,unused=sample_encoder(refiner,encoder,vocab,track,candidate_seed)
                            else:tokens,unused=generate(generator,prior,vocab,track,candidate_seed)
                            score=rank(selector,prior,tokens,vocab)
                            candidates.append(dict(tokens=tokens,selector_score=score,seed=candidate_seed))
                        except ValueError as e:trace.append(dict(block=block,candidate=ci,rejected=str(e)))
                    if not candidates:raise ValueError('No valid candidates')
                    chosen=max(candidates,key=lambda c:c['selector_score']) if mode!='generator-only' else candidates[0]
                    tokens=chosen['tokens'];trace.append(dict(block=block,candidates=candidates,selected_seed=chosen['seed']))
                    motif=motif or tokens;prior=[t for t in tokens if t not in ('BOS','EOS')]
                    for n in decode(tokens):all_notes.append(dict(n,bar=n['bar']+block*2))
                score=make_score(all_notes,track);stem=f'{family}-{mode}-{seed}'
                write_gp(score,args.out/(stem+'.gp'),title=stem)
                (args.out/(stem+'.expected.json')).write_text(json.dumps(score),encoding='utf-8')
                report['chains'].append(dict(file=stem+'.gp',trace=trace,sha256=digest(args.out/(stem+'.gp')),
                    copying={k:copying_ngrams(s,score) for k,s in sources.items()}))
                (args.out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                print('chain',stem,'notes',len(all_notes),flush=True)


if __name__=='__main__':main()
