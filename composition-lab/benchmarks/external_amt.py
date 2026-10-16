"""Actual official AMT sampler, with/without future lead conditioning.

Raw 10-ms output is retained. Final lead is immutable by explicit composition,
not a claim that unconstrained model sampling reproduces it exactly.
"""
import argparse,json,sys,time
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from learned_phrase_adapter import view


def main():
    p=argparse.ArgumentParser();p.add_argument('--upstream',type=Path,required=True);p.add_argument('--models',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--family',choices=['cloud','sweet'],required=True);p.add_argument('--condition',choices=['future','prefix'],required=True);p.add_argument('--seed',type=int,default=1701)
    p.add_argument('--attempt',type=int,default=1)
    p.add_argument('--roles',choices=['native','masked'],default='native')
    p.add_argument('--api',choices=['future','controls'],default='future')
    p.add_argument('--max-calls',type=int,default=128);p.add_argument('--max-seconds',type=float,default=300)
    a=p.parse_args();sys.path.insert(0,str(a.upstream.resolve()))
    import torch
    from transformers import GPT2LMHeadModel,GPT2Config
    from anticipation import ops
    from anticipation import sample
    from anticipation.convert import events_to_midi
    from anticipation.vocab import NOTE_OFFSET,DUR_OFFSET
    root=a.out.resolve()
    if not root.is_relative_to(Path(__file__).resolve().parents[1]/'local-artifacts'):raise ValueError('Private output required')
    dest=root/(a.family+'-amt-'+a.condition+'-'+str(a.seed)+'-attempt'+str(a.attempt)+('' if a.roles=='native' else '-masked')+('' if a.api=='future' else '-controls'));dest.mkdir(exist_ok=False)
    torch.set_num_threads(2);torch.manual_seed(a.seed)
    model=GPT2LMHeadModel(GPT2Config.from_json_file(a.models/'config.json'))
    state=torch.load(a.models/'pytorch_model.bin',map_location='cpu',weights_only=True)
    conversion='native HuggingFace keys'
    if 'wte.weight' in state:
        # Official Levanter export stores the base model without the HF prefix
        # and represents its tied output embedding as None.
        if state.pop('token_out_embeddings','missing') is not None or not model.config.tie_word_embeddings:raise ValueError('Unexpected output embedding format')
        state={'transformer.'+k:v for k,v in state.items()}
        state['lm_head.weight']=state['transformer.wte.weight']
        conversion='Levanter base keys prefixed; None output embedding tied to exact wte tensor'
    buffers=[k for k in state if k.endswith(('.attn.bias','.attn.masked_bias')) and k not in model.state_dict()]
    for k in buffers:del state[k]
    model.load_state_dict(state,strict=True);model.eval()
    source=json.loads((root.parent/'autonomous-v1'/(a.family+'.canonical.json')).read_text());ti={'cloud':0,'sweet':3}[a.family]
    projection=json.loads((root/'source-projections.json').read_text());start=next(r['start_bar']-1 for r in projection if r['family']==a.family)
    notes,audit=view(source['tracks'][ti],start,8)
    lead=[]
    for n in notes:lead += [round(50*(n['bar']*4+n['position'])),DUR_OFFSET+round(50*n['duration']),NOTE_OFFSET+80*128+n['pitch']]
    prompt=[];origin=F(source['tracks'][ti]['measures'][start]['onset_q'])
    for index,program in [(ti,80),({'cloud':2,'sweet':4}[a.family],25),({'cloud':4,'sweet':7}[a.family],32)]:
        for m in source['tracks'][index]['measures'][start:start+(3 if a.api=='controls' else 2)]:
            for e in m['voices'][0]:
                if e.get('grace_type'):continue
                for n in e['notes']:
                    if n['midi'] is None or (n.get('tie') or {}).get('destination')=='true':continue
                    onset=round(50*(F(e['onset_q'])-origin))
                    if onset>=(500 if a.api=='controls' else 400):continue
                    prompt += [onset,DUR_OFFSET+round(50*F(e['duration_q'])),NOTE_OFFSET+128*program+n['midi']]
    # Include original lead once, and all original first-two-bar support attacks.
    supplied=ops.sort(prompt+[x for triple in zip(lead[::3],lead[1::3],lead[2::3]) if triple[0]>=400 for x in triple]) if a.condition=='future' else ops.sort(prompt)
    original=sample.add_token;calls=0;started=time.monotonic()
    if a.roles=='masked':
        native_instruments=sample.instr_logits
        def instrument_constraint(logits,history):
            logits=native_instruments(logits,history)
            permitted=torch.zeros(129*128,dtype=torch.bool,device=logits.device)
            for program in (25,32):permitted[program*128:(program+1)*128]=True
            logits[NOTE_OFFSET:NOTE_OFFSET+len(permitted)].masked_fill_(~permitted,-float('inf'))
            return logits
        sample.instr_logits=instrument_constraint
    def guarded(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls>a.max_calls or time.monotonic()-started>a.max_seconds:raise RuntimeError('Explicit inference resource limit reached')
        return original(*args,**kwargs)
    sample.add_token=guarded
    try:
        if a.api=='controls':
            # Match the upstream accompaniment example: five-second history,
            # followed by anticipated melody controls.
            from anticipation.tokenize import extract_instruments
            _,controls=extract_instruments(lead,[80])
            raw=sample.generate(model,5,16,inputs=ops.sort(prompt),controls=controls if a.condition=='future' else None,top_p=.95)
        else:raw=sample.generate(model,0,16,inputs=supplied,top_p=.95)
    except Exception as error:
        (dest/'execution.json').write_text(json.dumps(dict(status='failed',condition=a.condition,api=a.api,roles=a.roles,calls=calls,max_calls=a.max_calls,max_seconds=a.max_seconds,elapsed_seconds=time.monotonic()-started,error=str(error)),indent=2));raise
    (dest/'raw-events.json').write_text(json.dumps(raw));events_to_midi(raw).save(dest/'raw.mid')
    # Never score or play a duplicated sampled lead as if it were a fixed control.
    support=[x for triple in zip(raw[::3],raw[1::3],raw[2::3]) if (triple[2]-NOTE_OFFSET)//128!=80 for x in triple]
    combined=ops.sort(support+lead)
    (dest/'arranged-events.json').write_text(json.dumps(combined));events_to_midi(combined).save(dest/'arranged.mid')
    projected=[list(t) for t in zip(combined[::3],combined[1::3],combined[2::3]) if (t[2]-NOTE_OFFSET)//128==80]
    assert projected==[list(t) for t in zip(lead[::3],lead[1::3],lead[2::3])]
    new_support=sum(t>=(500 if a.api=='controls' else 400) for t in support[::3])
    (dest/'execution.json').write_text(json.dumps(dict(status='inference_succeeded',seed=a.seed,condition=a.condition,roles=a.roles,api=a.api,prefix_seconds=5 if a.api=='controls' else 4,seconds=16,calls=calls,lead_events=len(lead)//3,lead_event_identity=True,support_events=len(support)//3,generated_support_after_prefix=new_support,source_projection=audit,checkpoint_conversion=conversion,compatibility_removed_nonlearned_buffers=buffers,elapsed_seconds=time.monotonic()-started,limitations=['10ms model timing','source monophonic attack projection, not full source performance','programs mapped to lead80/guitar25/bass32','fixed lead retained explicitly; sampled extra lead excluded','prefix support is source material, not generated','masked variant adds an explicit guitar/bass output-logit constraint; not an upstream trained role-control claim']),indent=2))
    print((dest/'execution.json').read_text())


if __name__=='__main__':main()
