"""Run the pinned official orchestration, capturing raw output and call counts.

Upstream code is not vendored. Only model loading is replaced with strict,
weights-only local loading; generation/refinement/selection logic stays upstream.
"""
import argparse,hashlib,json,os,random,runpy,sys,shutil,pickletools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from learned_phrase_adapter import examples,decode,make_score
from gp_author import write_gp


def prepare(root,models):
    import yaml
    from music21 import stream,note
    root.mkdir(parents=True,exist_ok=False);inputs=root/'inputs';inputs.mkdir()
    vocab=json.loads((models/'tokenizer.json').read_text());records=[]
    prior=Path(__file__).resolve().parents[1]/'local-artifacts/autonomous-v1'
    for family,ti in [('cloud',0),('sweet',3)]:
        score=json.loads((prior/(family+'.canonical.json')).read_text())
        rows,rejected=examples(score,ti,vocab)
        harmony,bass={'cloud':(2,4),'sweet':(4,7)}[family]
        def attacks(track,start):
            return sum(n['midi'] is not None and (n.get('tie') or {}).get('destination')!='true' for m in track['measures'][start:start+2] for e in m['voices'][0] if not e.get('grace_type') for n in e['notes'])
        eligible=[r for r in rows if all(attacks(score['tracks'][index],r['start_bar']-1)>=4 for index in (harmony,bass))]
        if not eligible:raise ValueError('No eligible ensemble-context motif')
        row=eligible[0];notes=decode(row['context'])
        melody=stream.Stream()
        for n in notes:melody.insert(n['bar']*4+float(n['position']),note.Note(n['pitch'],quarterLength=float(n['duration'])))
        key=melody.analyze('key');ks='KS_'+key.tonic.name
        if ks not in vocab:ks='KS_'+key.tonic.getEnharmonic().name
        if ks not in vocab:raise ValueError('Unsupported estimated key '+ks)
        raw=[[n['bar'],float(n['position']),0,n['pitch'],float(n['duration']),91] for n in notes]
        data=dict(metadata=dict(tempo={'0':120},key_signature=ks,major_or_minor='MM_'+key.mode,time_signature='TimeSig_4/4'),phrases={'0':[raw,'PP_beginning']})
        (inputs/(family+'.json')).write_text(json.dumps(data))
        records.append(dict(family=family,start_bar=row['start_bar'],projection=row['projection'],quantization=row['quantization'],key_estimate=ks,mode_estimate=key.mode,source_track=ti,selection_rule='first representable motif with >=4 written attacks each in harmony and bass over first two bars'))
    (root/'source-projections.json').write_text(json.dumps(records,indent=2))


def main():
    p=argparse.ArgumentParser();p.add_argument('--upstream',type=Path,required=True);p.add_argument('--models',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--prepare',action='store_true');p.add_argument('--family',choices=['cloud','sweet']);p.add_argument('--selection',choices=['on','off'],default='on');p.add_argument('--seed',type=int,default=1701);p.add_argument('--attempt',type=int,default=1);p.add_argument('--form',choices=['ABA','ABC'],default='ABA')
    a=p.parse_args();upstream=a.upstream.resolve();models=a.models.resolve();root=a.out.resolve()
    if not root.is_relative_to(Path(__file__).resolve().parents[1]/'local-artifacts'):raise ValueError('Private output required')
    if a.prepare:prepare(root,models);return
    import torch,yaml
    from transformers import EncoderDecoderModel,EncoderDecoderConfig,BertForSequenceClassification,BertConfig
    torch.set_num_threads(2);torch.manual_seed(a.seed);random.seed(a.seed)
    def safe_seq(cls,path,*args,**kwargs):
        path=Path(path);model=EncoderDecoderModel(EncoderDecoderConfig.from_json_file(path/'config.json'))
        model.load_state_dict(torch.load(path/'pytorch_model.bin',map_location='cpu',weights_only=True),strict=True);return model
    def safe_selector(cls,path,*args,**kwargs):
        path=Path(path);model=BertForSequenceClassification(BertConfig.from_json_file(path/'config.json'))
        model.load_state_dict(torch.load(path/'pytorch_model.bin',map_location='cpu',weights_only=True),strict=True);return model
    EncoderDecoderModel.from_pretrained=classmethod(safe_seq)
    # Auto class delegates config dispatch to the verified local BERT architecture.
    from transformers import AutoModelForSequenceClassification
    AutoModelForSequenceClassification.from_pretrained=classmethod(safe_selector)
    run=root/(a.family+'-selector-'+a.selection+'-'+str(a.seed)+'-attempt'+str(a.attempt)+('' if a.form=='ABA' else '-'+a.form));run.mkdir(exist_ok=False)
    config=yaml.safe_load((upstream/'configs/configs_os.yaml').read_text())
    config['raw_data'].update(artifact_folder=str(models),json_folder=str(root/'inputs'))
    config['generation'].update(generate_all=False,test_filepath=a.family+'.json',structure=a.form,phrases_per_section=[3,3,3],use_phrase_selection=a.selection=='on',write_midi=True,use_velocity=False,allow_modulation=False,transformations=['permute_melody_rhythm'])
    config['generation']['ratio']=dict(phrase_generation_frequency=1,phrase_refinement_frequency=1,motif_repetition_frequency=50)
    config_path=run/'config.yaml';config_path.write_text(yaml.safe_dump(config));sys.argv=['generate.py','--config',str(config_path)]
    # Upstream imports this relative asset. Reject unexpected pickle globals
    # before exposing the tiny numeric profile to its unmodified loader.
    profile=upstream/'key_profile.pickle'
    allowed={'numpy.core.multiarray _reconstruct','numpy ndarray','numpy dtype'}
    for op,arg,_ in pickletools.genops(profile.read_bytes()):
        if op.name=='STACK_GLOBAL' or (op.name=='GLOBAL' and arg not in allowed):raise ValueError('Unexpected key profile pickle global')
    shutil.copy2(profile,run/profile.name)
    sys.path.insert(0,str(upstream));os.chdir(run)
    module=runpy.run_path(str(upstream/'generate.py'),run_name='official_pipeline_adapter');scope=module['generate'].__globals__;counts={}
    for name in ('generate_phrase','refine_phrase','select_phrase'):
        original=scope[name]
        def wrap(*args,_name=name,_original=original,**kwargs):
            counts[_name]=counts.get(_name,0)+1;return _original(*args,**kwargs)
        scope[name]=wrap
    original_write=scope['encoding_to_midi']
    def capture(encoding,tempo,time_signature,path,*args,**kwargs):
        (run/'raw-notes.json').write_text(json.dumps(dict(notes=encoding,tempo=tempo,time_signature=time_signature)))
        return original_write(encoding,tempo,time_signature,path,*args,**kwargs)
    scope['encoding_to_midi']=capture
    try:
        module['generate'](config['generation'],a.family+'.json',module['phrase_refiner_model'],module['phrase_generation_model'],module['phrase_selection_model'],write_midi=True)
        (run/'execution.json').write_text(json.dumps(dict(status='inference_succeeded',seed=a.seed,calls=counts,form='supplied '+a.form+', three phrases per section',upstream_sha=hashlib.sha256((upstream/'generate.py').read_bytes()).hexdigest()),indent=2))
    except Exception as e:
        (run/'execution.json').write_text(json.dumps(dict(status='failed',calls=counts,error=repr(e)),indent=2));raise


if __name__=='__main__':main()
