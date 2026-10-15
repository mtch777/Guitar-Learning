"""Frozen checkpoint calibration on author-listed held-out phrase pairs."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks.learned_organization import load_model,tensor,private_output
from benchmarks.learned_phrase_chain import selector_model,rank


def tokenize(notes,meter,vocab):
    # Preserve original int/float string spelling, matching upstream encoding.
    bar=notes[0][0]-1;result=[]
    for n in notes:
        while bar<n[0]:result+=['Bar_None',meter];bar+=1
        result += [f'Position_{n[1]}',f'Pitch_{n[3]}',f'Duration_{n[4]}']
    if any(t not in vocab or vocab[t]>=509 for t in result):raise ValueError('Unrepresentable official token')
    return result


def main():
    import torch
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--models',type=Path,required=True);p.add_argument('--lists',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--start',type=int,default=0);p.add_argument('--limit',type=int,default=20)
    args=p.parse_args();private_output(args.out);args.out.mkdir(exist_ok=False,parents=True);torch.set_num_threads(2)
    vocab=json.loads((args.models/'tokenizer.json').read_text())
    train=json.loads((args.lists/'train_file_list.json').read_text());test=json.loads((args.lists/'test_file_list.json').read_text())
    if set(train)&set(test):raise ValueError('Official train/test filename overlap')
    rows=[];rejected=[]
    with zipfile.ZipFile(args.archive) as z:
        for filename in test[args.start:args.start+args.limit]:
            try:
                raw=json.loads(z.read('data/extracted_phrases/'+filename));meta=raw['metadata'];phrases=raw['phrases']
                c=tokenize(phrases['0'][0],meta['time_signature'],vocab);t=tokenize(phrases['1'][0],meta['time_signature'],vocab)
                if len(c)+len(t)>470:raise ValueError('Pair exceeds fixed token budget')
                rows.append(dict(filename=filename,context=c,target=t,metadata=meta))
            except (ValueError,KeyError) as e:rejected.append(dict(filename=filename,reason=str(e)))
    generator=load_model(args.models/'phrase_generation');selector=selector_model(args.models/'phrase_selection')
    results=[]
    with torch.inference_mode():
        for row in rows:
            other=next((r for r in rows if all(r['metadata'][k]==row['metadata'][k] for k in ('time_signature','key_signature','major_or_minor')) and r['context']!=row['context'] and r['target']!=row['target']),None)
            if other is None:continue
            meta=row['metadata'];suffix=['SEP',meta['major_or_minor'],meta['key_signature'],'CA_False','SEP','EOS']
            nll={}
            for name,c in [('real',row['context']),('mismatched',other['context']),('none',[])]:
                nll[name]=float(generator(input_ids=tensor(['BOS']+c+suffix,vocab),labels=tensor(row['target']+['EOS'],vocab)).loss)
            results.append(dict(filename=row['filename'],target_tokens=len(row['target'])+1,nll=nll,
                selector_real=rank(selector,row['context'],row['target'],vocab),selector_wrong=rank(selector,row['context'],other['target'],vocab)))
    summary=dict(archive_sha256=hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        train_filenames=len(train),test_filenames=len(test),filename_overlap=0,test_list_start=args.start,test_list_limit=args.limit,eligible_selected=len(rows),evaluated=len(results),
        token_weighted_nll={k:sum(r['nll'][k]*r['target_tokens'] for r in results)/sum(r['target_tokens'] for r in results) for k in ('real','mismatched','none')},
        real_beats_mismatched=sum(r['nll']['real']<r['nll']['mismatched'] for r in results),
        selector_correct_rankings=sum(r['selector_real']>r['selector_wrong'] for r in results),
        control_match=['meter','key signature','mode'],
        limitations=['Author-listed filename holdout only; melody-family overlap unknown','No adaptation; metadata provided','Small ordered sample; no perceptual accuracy claim'])
    (args.out/'report.json').write_text(json.dumps(dict(summary=summary,rows=results,rejected=rejected),indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
