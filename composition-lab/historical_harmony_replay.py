"""Recover a recorded Git generator and reproduce frozen harmony, privately.

No live generator edits or GP export. Exact track equality is not historical
helper authenticity, causal attribution or musical validation.
"""
import argparse,hashlib,inspect,json,subprocess,types
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
from artist_form import arrange
from engine_contract import sha


def recover(expected):
    path='composition-lab/corpus_composer.py'
    refs=subprocess.check_output(['git','log','-100','--format=%H','--',path],text=True).splitlines()
    for ref in refs:
        blob=subprocess.check_output(['git','show',ref+':'+path])
        if hashlib.sha256(blob).hexdigest()==expected:
            module=types.ModuleType('_historical_corpus_composer')
            module.__file__=f'historical@{ref}/{path}'
            exec(compile(blob,module.__file__,'exec'),module.__dict__)
            return module,dict(revision=ref,sha256=expected,path=path)
    raise ValueError('Exact recorded generator blob not found; no current-code substitution')


def accepted_attempt(batch,piece):
    attempts=[r['attempt'] for r in batch['rejected_proposals'] if r['piece']==piece]
    if any(type(a)is not int or a<0 for a in attempts) or sorted(attempts)!=list(range(len(attempts))):
        raise ValueError('Accepted retry is ambiguous')
    return len(attempts)


def observe_positions(module):
    original=module.position_chord;events=[];attempts=[]
    def wrapped(pitches,tuning,**kwargs):
        caller=inspect.currentframe().f_back;v=caller.f_locals
        relevant=caller.f_globals is module.__dict__ and v.get('role')=='harmony'
        row=dict(bar=v['bi']+1,local_q=str(v['cursor']),branch='newly_sampled_harmony',
            target=int(v['target']),shift=v['shift'],pitches=list(pitches)) if relevant else None
        try:result=original(pitches,tuning,**kwargs)
        except ValueError:
            if relevant:attempts.append(dict(row,success=False))
            raise
        if relevant:
            attempts.append(dict(row,success=True));before=int(v['root']);step=int(v['step']);target=int(v['target']);actual=min(pitches)
            if target!=before+step or actual!=target+12*v['shift']:raise AssertionError('Historical transformation differs from assumed contract')
            events.append(dict(bar=v['bi']+1,local_q=str(v['cursor']),previous_root=before,source_step=step,
                target_before_fit=target,octave_shift=v['shift'],actual_root=actual,lowest_open=min(tuning),
                source_song=v['pattern']['song_id'],source_part=v['pattern']['part_id'],source_bar=v['pattern']['bar'],
                voicing_intervals=v['source_event']['intervals']))
        return result
    module.position_chord=wrapped
    return original,events,attempts


def run(plan_path,batch_path,trace_core=None):
    plan_path,batch_path=Path(plan_path),Path(batch_path)
    read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
    plan,batch=read(plan_path),read(batch_path);model_spec=plan['models']['composer']
    if sha(model_spec['path'])!=model_spec['sha256']:raise ValueError('Composer revision mismatch')
    model=read(model_spec['path']);module,provenance=recover(batch['code_sha256']['corpus_composer.py'])
    paths=[plan_path,batch_path,Path(model_spec['path'])]+[Path(c[k]) for c in plan['cores'] for k in ('canonical','source','form_plan')]
    helpers=[Path(__file__).with_name(n) for n in ('controlled_generation.py','generation_freedom.py','artist_form.py')]
    seals={str(p):sha(p) for p in paths+helpers};records=[]
    if trace_core is not None and not 1<=trace_core<=len(plan['cores']):raise ValueError('Trace core outside frozen set')
    for ci,c in enumerate(plan['cores']):
        for k in ('source','canonical','form_plan'):
            if sha(c[k])!=c[k+'_sha256']:raise ValueError('Frozen comparator changed')
        reference=read(c['canonical']);sections=read(c['form_plan']);attempt=accepted_attempt(batch,ci);seed=10000+ci*100+attempt
        original=events=attempts=None
        if trace_core==ci+1:original,events,attempts=observe_positions(module)
        try:core,audit=module.generate(model,len(reference['tracks'][0]['measures']),seed)
        finally:
            if original is not None:module.position_chord=original
        actual=arrange(core,sections)
        if actual['tracks'][0]!=reference['tracks'][0]:raise AssertionError('Historical harmony mismatch; causal attribution forbidden')
        record=dict(core=ci+1,seed=seed,accepted_attempt=attempt,harmony_track_exact=True,
            comparison='Entire canonical harmony track dictionary: all voices/occurrences, pitch/voicing, rational clocks/durations, tuning,string/fret,metadata')
        if events is not None:
            for e in events:
                event=next(x for x in core['tracks'][0]['measures'][e['bar']-1]['voices'][0] if F(x['local_onset_q'])==F(e['local_q']))
                if min(n['midi'] for n in event['notes'])!=e['actual_root']:raise AssertionError('Trace differs from emitted root')
            record.update(root_events=events,fit_attempts=attempts,summary=dict(newly_sampled_attacks=len(events),
                shifts=dict(Counter(e['octave_shift'] for e in events)),source_step_sum=sum(e['source_step'] for e in events),
                octave_refit_increment_sum=sum(12*e['octave_shift'] for e in events),
                targets_below_lowest_open=sum(e['target_before_fit']<e['lowest_open'] for e in events),
                upward_refits_with_target_in_range=sum(e['octave_shift']>0 and e['target_before_fit']>=e['lowest_open'] for e in events)))
        records.append(record)
    if seals!={p:sha(p) for p in seals}:raise AssertionError('Input/dependency changed during replay')
    return dict(schema='historical-harmony-replay-v1',historical_generator=provenance,inputs_sha256=seals,records=records,
        limitations=['Current imported helpers reproduce outputs; original helper authenticity was not sealed.',
            'Local step/refit sums exclude reused motif resets; not a whole-piece drift decomposition.',
            'Observational arithmetic only; no counterfactual causal test, repair, new GP export or listening judgment.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','batch','output'):p.add_argument(name,type=Path)
    p.add_argument('--trace-core',type=int);a=p.parse_args()
    if 'local-artifacts' not in a.output.resolve().parts:p.error('Private output required')
    if a.output.exists():raise FileExistsError('Preserve prior replay')
    result=run(a.plan,a.batch,a.trace_core);a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(exact_harmony_tracks=len(result['records']),historical_revision=result['historical_generator']['revision'],traced_core=a.trace_core)))
