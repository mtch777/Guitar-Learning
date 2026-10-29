"""Render a private review from already verified worker/native evidence only."""
import argparse,json,hashlib
from pathlib import Path


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def build(qa,native,fresh):
    result=read(qa/'result.json');demo=read(qa/'demonstration.json');audit=read(native/'independent-dynamic-artifacts.json')
    if audit['status']not in ('PASS_NATIVE_GP_AND_AUDIO_DYNAMICS','PASS_GP_BUNDLE_AND_AUDIO_DYNAMICS'):raise ValueError('Verified native result required')
    fr=read(fresh/'result.json')
    if not fr['status'].startswith('PASS_'):raise ValueError('Fresh QA failed; review acceptance blocked, original failure retained')
    plan=read(fresh/'plan.json');capture=Path(next(iter(plan['source_hashes']))).parent;selection=read(capture.parent/'selection.json')
    if selection['status']!='captured'or selection['selected_song_id']!=fr.get('song_id'):raise ValueError('Fresh selection/capture identity differs')
    for p,h in plan['source_hashes'].items():
        if sha(Path(p))!=h:raise ValueError('Fresh capture changed')
    if read(qa/'zero-and-pair/result.json')['modules']!=read(fresh/'zero-and-pair/result.json')['modules']:raise ValueError('Fresh/development inverse differs')
    snapshot=read(native/'dynamic-native-snapshot.json')['cases']['zero'];renders=read(native/'audio-jobs.results.json');render=next(r for r in renders if r['method']=='zero'and r['mode']=='focused')
    if snapshot['midi_tick_shift']!=0:raise ValueError('Review clock requires explicit zero MIDI shift')
    tempos=sorted({(e['data']['tick'],e['data']['beatsPerMinute'])for e in snapshot['events']if e['kind']=='TempoChangeEvent'})
    if not tempos or tempos[0][0]!=0:raise ValueError('Explicit native initial tempo required')
    def seconds(tick):
        total=0.;cursor=0;tempo=tempos[0][1]
        for at,bpm in tempos:
            if at>tick:break
            total+=(at-cursor)/960*60/tempo;cursor=at;tempo=bpm
        return total+(tick-cursor)/960*60/tempo
    start=render['playback_range']['startTick'];end=render['playback_range']['endTick'];offset=seconds(start);affected=set(demo['target']['influence_refs'])
    notes=[dict(ref=c['source_ref'],pitch=c['key'],start=max(0,seconds(c['start'])-offset),end=min(render['seconds'],seconds(c['start']+c['length'])-offset),velocity=c['velocity'],changed=c['source_ref']in affected)
        for c in snapshot['callbacks']if c['track']==demo['clip']['part']and c['start']<end and c['start']+c['length']>start]
    if not notes or not any(n['changed']for n in notes):raise ValueError('No changed audible notes in actual selected playback')
    meta=read(qa/'zero-capture/metadata.json');part=read(qa/f"zero-capture/track-{demo['clip']['part']}.json")
    data=dict(title=meta['title'],artist=meta.get('artist'),part=part.get('name',f"Track {demo['clip']['part']+1}"),clip=demo['clip'],duration=render['seconds'],notes=notes,
        before=demo['target']['marking'],after=demo['chosen']['marking'],influenced=len(affected),played_attacks=sum(n['changed']for n in notes),donors=len(demo['chosen']['donor_refs']),controls=demo['controls'],rates=result['rates'],
        facts=result['facts'],source_notes=result['notes'],native_status=audit['status'],fidelity_scope=audit['fidelity_scope'],standalone_roundtrip_pass=all(r['standalone_roundtrip_pass']for r in audit['artifact_fidelity']),
        fresh=dict(title=fr['title'],status=fr['status'],notes=fr['notes'],facts=fr['facts'],counts=fr['counts'],actual_changed=fr['actual_changed'],seed=str(selection['seed']),sampling=selection['pool_rule']),
        evidence_hashes={str(p.resolve()):sha(p)for p in [qa/'demonstration.json',qa/'result.json',native/'independent-dynamic-artifacts.json',native/'dynamic-native-snapshot.json',fresh/'result.json',capture.parent/'selection.json']})
    if demo['controls']['context_policy']=='source_local_dynamic_transition':
        evidence=demo['decision']['evidence'];context=evidence['context']
        data['dynamic_context']=dict(incoming=context['incoming_marking'],position_q=context['position_q'],meter=context['source_meter'],
            options=[dict(marking=o['marking'],declarations=len(o['donor_refs']))for o in evidence['options']],
            witness_pair=evidence['witness_pair'],scope=context['scope'])
    (native/'preview.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (native/'index.html').write_text((Path(__file__).parent/'dynamic-preview.html').read_text(encoding='utf-8'),encoding='utf-8')
    return dict(status='REVIEW_BUILT_UI_QA_PENDING',path=str((native/'index.html').resolve()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('qa',type=Path);p.add_argument('native',type=Path);p.add_argument('fresh',type=Path);a=p.parse_args();print(json.dumps(build(a.qa,a.native,a.fresh)))
