"""Real pretrained/adapted phrase inference, fixed source-disjoint local folds.

Run from repo root with optional ML dependencies installed. All model/source
artifacts are written only to the caller's ignored output directory.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from exact_score import extract_score
from learned_phrase_adapter import examples,encoder_tokens,decode,make_score,rational_token
from generation_validation import copying_ngrams
from gp_author import write_gp


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def private_output(path):
    allowed=Path(__file__).resolve().parents[1]/'local-artifacts'
    if not path.resolve().is_relative_to(allowed):raise ValueError('Private experiment output must stay under ignored local-artifacts')


def unique(items):
    seen=set();result=[]
    for item in items:
        key=json.dumps([item['context'],item['target']])
        if key not in seen:seen.add(key);result.append(item)
    return result


def load_model(folder):
    import torch
    from transformers import EncoderDecoderModel,EncoderDecoderConfig
    model=EncoderDecoderModel(EncoderDecoderConfig.from_json_file(folder/'config.json'))
    state=torch.load(folder/'pytorch_model.bin',map_location='cpu',weights_only=True)
    model.load_state_dict(state,strict=True);model.eval()
    return model


def ids(tokens,vocab):
    if any(t not in vocab or not 0<vocab[t]<510 for t in tokens):raise ValueError('Unknown token')
    return [vocab[t] for t in tokens]


def tensor(tokens,vocab):
    import torch
    return torch.tensor([ids(tokens,vocab)],dtype=torch.long)


def fit(model,data,vocab,permuted):
    import torch
    torch.manual_seed(17);model.train();optimizer=torch.optim.AdamW(model.parameters(),lr=0.00005)
    losses=[]
    for step in range(10):
        index=step%len(data);row=data[index]
        context=data[(index+1)%len(data)]['context'] if permuted else row['context']
        optimizer.zero_grad(set_to_none=True)
        loss=model(input_ids=tensor(encoder_tokens(context),vocab),labels=tensor(row['target'],vocab)).loss
        loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step();losses.append(float(loss.detach()))
    model.eval();return losses


def evaluate(model,data,vocab):
    import torch
    results=[]
    with torch.inference_mode():
        for i,row in enumerate(data):
            values={}
            other=next((data[(i+j)%len(data)]['context'] for j in range(1,len(data)) if data[(i+j)%len(data)]['context']!=row['context']),None)
            families={}
            for name,context in [('real',row['context']),('mismatched',other),('none',[])]:
                if context is None:values[name]=None;continue
                labels=tensor(row['target'],vocab)
                output=model(input_ids=tensor(encoder_tokens(context),vocab),labels=labels)
                values[name]=float(output.loss)
                losses=torch.nn.functional.cross_entropy(output.logits[0],labels[0],reduction='none')
                families[name]={}
                for kind,prefix in [('pitch','Pitch_'),('duration','Duration_'),('position','Position_')]:
                    selected=[float(losses[j]) for j,t in enumerate(row['target']) if t.startswith(prefix)]
                    families[name][kind]=dict(sum=sum(selected),count=len(selected))
            results.append(dict(start_bar=row['start_bar'],target_tokens=len(row['target']),token_family_losses=families,**values))
    summary={}
    for k in ('real','mismatched','none'):
        eligible=[r for r in results if r[k] is not None]
        summary[k]=sum(r[k]*r['target_tokens'] for r in eligible)/sum(r['target_tokens'] for r in eligible) if eligible else None
    family_summary={}
    for context in ('real','mismatched','none'):
        family_summary[context]={}
        for kind in ('pitch','duration','position'):
            entries=[r['token_family_losses'][context][kind] for r in results if context in r['token_family_losses']]
            count=sum(e['count'] for e in entries)
            family_summary[context][kind]=sum(e['sum'] for e in entries)/count if count else None
    return dict(rows=results,token_weighted_nll=summary,token_family_nll=family_summary,
        usable_context_contrasts=sum(r['mismatched'] is not None for r in results),
        real_beats_mismatch=sum(r['mismatched'] is not None and r['real']<r['mismatched'] for r in results),examples=len(results))


class Grammar:
    """Notation-valid sampling only: no melodic/harmonic preference rules."""
    def __init__(self,vocab,low,high):
        self.vocab=vocab;self.reverse={i:t for t,i in vocab.items()};self.low=low;self.high=high
        self.positions={};self.durations={}
        for t,i in vocab.items():
            if t.startswith(('Position_','Duration_')):
                try:q=rational_token(t)
                except ValueError:continue
                if t.startswith('Position_') and 0<=q<4:self.positions[i]=q
                if t.startswith('Duration_') and 0<q<=4:self.durations[i]=q

    def allowed(self,sequence):
        v=self.vocab;tokens=[self.reverse.get(int(i),'PAD') for i in sequence];last=tokens[-1]
        bars=tokens.count('Bar_None')
        if last=='BOS':return [v['Bar_None']]
        if last=='Bar_None':return [v['TimeSig_4/4']]
        if last=='TimeSig_4/4':return list(self.positions)
        if last.startswith('Position_'):return [v[f'Pitch_{p}'] for p in range(self.low,self.high+1)]
        if last.startswith('Pitch_'):
            pos=rational_token(tokens[-2]);return [i for i,q in self.durations.items() if pos+q<=4]
        if last.startswith('Duration_'):
            end=rational_token(tokens[-3])+rational_token(last)
            return [i for i,q in self.positions.items() if q>=end]+[v['Bar_None'] if bars<2 else v['EOS']]
        raise ValueError('Unexpected decoder grammar state')

    def __call__(self,input_ids,scores):
        import torch
        allowed=self.allowed(input_ids[0].tolist());mask=torch.full_like(scores,float('-inf'));mask[:,allowed]=0
        return scores+mask


def sample_encoder(model,encoder,vocab,track,seed):
    import torch
    from transformers import LogitsProcessorList
    torch.manual_seed(seed)
    low=max(0,min(track['tunings'][0]));high=min(127,max(track['tunings'][0])+24)
    with torch.inference_mode():
        result=model.generate(tensor(encoder,vocab),decoder_start_token_id=vocab['BOS'],
            eos_token_id=vocab['EOS'],pad_token_id=0,do_sample=True,temperature=1.0,num_beams=1,
            max_new_tokens=128,logits_processor=LogitsProcessorList([Grammar(vocab,low,high)]))
    reverse={i:t for t,i in vocab.items()};raw=[reverse[i] for i in result[0].tolist()]
    if raw[-1]!='EOS':raise ValueError('Generation truncated before EOS')
    return raw,make_score(decode(raw),track)


def generate(model,context,vocab,track,seed):
    return sample_encoder(model,encoder_tokens(context),vocab,track,seed)


def main():
    import torch
    p=argparse.ArgumentParser();p.add_argument('--models',type=Path,required=True);p.add_argument('--sources',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();private_output(args.out);args.out.mkdir(exist_ok=False,parents=True);torch.set_num_threads(2)
    vocab=json.loads((args.models/'tokenizer.json').read_text());folder=args.models/'phrase_generation'
    sources={name:extract_score(args.sources/file) for name,file in [('cloud','Cloud Cascade (Tuned Down).gp'),('sweet',"Sweet Child O' Mine.gp")]}
    if sources['cloud']['source_sha256']==sources['sweet']['source_sha256']:raise ValueError('Source leakage')
    report=dict(protocol='LEARNED_ORGANIZATION.md',checkpoint_sha256=digest(folder/'pytorch_model.bin'),
        tokenizer_sha256=digest(args.models/'tokenizer.json'),source_hashes={k:v['source_sha256'] for k,v in sources.items()},
        upstream_code_commit='59a2a001884a1f235ef9a0313565487874f6e3b9',parameters=None,folds={},
        limitations=['Pretrained corpus song overlap unknown','Only local adaptation source-disjoint','Projected attacks and fixed windows are not human phrases','No quality claim from NLL or grammar','Source/adapted model weights and generated artifacts remain private'])
    for train_name,test_name in [('cloud','sweet'),('sweet','cloud')]:
        training=[];coverage=[]
        for ti,t in enumerate(sources[train_name]['tracks']):
            if t.get('is_percussion') or 'drum' in t['name'].lower():continue
            e,r=examples(sources[train_name],ti,vocab);training+=e;coverage.append(dict(track=ti,accepted=len(e),rejected=r))
        training=unique(training)[:32]
        test_ti=0 if test_name=='cloud' else 3
        raw_test,rejected=examples(sources[test_name],test_ti,vocab);test=unique(raw_test)[:8]
        if len(training)<2 or len(test)<2:raise ValueError('Insufficient distinct eligible windows')
        fold=dict(train=train_name,test=test_name,training_pairs=len(training),eval_pairs=len(test),coverage=coverage,
                  eval_rejected=rejected,eval_projection=[dict(start_bar=r['start_bar'],projection=r['projection'],quantization=r['quantization']) for r in test],conditions={})
        report['folds'][train_name+'-to-'+test_name]=fold
        for condition in ('pretrained','paired','permuted'):
            model=load_model(folder);report['parameters']=sum(p.numel() for p in model.parameters())
            losses=fit(model,training,vocab,condition=='permuted') if condition!='pretrained' else []
            evidence=dict(training_loss=losses,evaluation=evaluate(model,test,vocab),generated=[])
            if condition!='pretrained':
                weights=args.out/f'{train_name}-{condition}.pt';torch.save(model.state_dict(),weights);evidence['adapted_weights_sha256']=digest(weights)
            for seed in (17,29):
                stem=f'{train_name}-to-{test_name}-{condition}-{seed}'
                try:
                    raw,score=generate(model,test[0]['context'],vocab,sources[test_name]['tracks'][test_ti],seed)
                    write_gp(score,args.out/(stem+'.gp'),title=stem)
                    (args.out/(stem+'.expected.json')).write_text(json.dumps(score),encoding='utf-8')
                    entry=dict(file=stem+'.gp',sha256=digest(args.out/(stem+'.gp')),tokens=raw,
                        copying={k:copying_ngrams(source,score) for k,source in sources.items()})
                    if seed==17:
                        other_context=next((r['context'] for r in test if r['context']!=test[0]['context']),None)
                        entry['distinct_context_available']=other_context is not None
                        if other_context is not None:
                            other,unused=generate(model,other_context,vocab,sources[test_name]['tracks'][test_ti],seed)
                            entry['changed_context_same_seed_changes_output']=raw!=other
                            entry['other_context_tokens']=other
                    evidence['generated'].append(entry)
                except ValueError as e:evidence['generated'].append(dict(file=stem+'.gp',rejected=str(e)))
            fold['conditions'][condition]=evidence
            (args.out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(train_name,test_name,condition,json.dumps(evidence['evaluation']['token_weighted_nll']),flush=True)
            del model
    print('complete',args.out,flush=True)


if __name__=='__main__':main()
