"""Private compact player, bound to actual inverse, native and fresh proofs."""
import argparse,json
from pathlib import Path
from write_dynamic_review import read,sha


def build(qa,native,fresh):
    result=read(qa/'result.json');demo=read(qa/'demonstration.json');audit=read(native/'independent-accent-artifacts.json');fr=read(fresh/'result.json')
    if audit['status']not in('PASS_NATIVE_GP_AND_AUDIO_ACCENTS','PASS_GP_BUNDLE_AND_AUDIO_ACCENTS'):raise ValueError('Verified native accent output required')
    if not fr['status'].startswith('PASS_'):raise ValueError('Fresh QA failed; retain failure before review')
    plan=read(fresh/'plan.json');capture=Path(next(iter(plan['source_hashes']))).parent;selection=read(capture.parent/'selection.json')
    if selection['status']!='captured'or selection['selected_song_id']!=fr['song_id']:raise ValueError('Actual fresh selection differs')
    if any(sha(Path(p))!=h for p,h in plan['source_hashes'].items()):raise ValueError('Fresh source changed')
    if result['modules']!=fr['modules']:raise ValueError('Fresh and development relationships differ')
    snapshot=read(native/'accent-native-snapshot.json')['cases']['zero'];render=next(r for r in read(native/'audio-jobs.results.json')if r['method']=='zero'and r['mode']=='focused')
    if snapshot['midi_tick_shift']!=0:raise ValueError('Explicit zero MIDI clock shift required')
    tempos=sorted({(e['data']['tick'],e['data']['beatsPerMinute'])for e in snapshot['events']if e['kind']=='TempoChangeEvent'})
    if not tempos or tempos[0][0]!=0:raise ValueError('Explicit initial tempo required')
    def seconds(tick):
        total=0.;cursor=0;tempo=tempos[0][1]
        for at,bpm in tempos:
            if at>tick:break
            total+=(at-cursor)/960*60/tempo;cursor=at;tempo=bpm
        return total+(tick-cursor)/960*60/tempo
    start=render['playback_range']['startTick'];end=render['playback_range']['endTick'];offset=seconds(start);target=demo['target'];ref=target['occurrence_ref']
    notes=[dict(ref=c['source_ref'],pitch=c['key'],start=max(0,seconds(c['start'])-offset),end=min(render['seconds'],seconds(c['start']+c['length'])-offset),velocity=c['velocity'],changed=c['source_ref']==ref)
        for c in snapshot['callbacks']if c['track']==demo['clip']['part']and c['start']<end and c['start']+c['length']>start]
    if not notes or not any(n['changed']for n in notes):raise ValueError('Selected accent not present in audible clip')
    def label(state):return 'No accent'if state['kind']=='absent'else['Explicit no accent','Accent','Heavy accent'][state['value']]
    meta=read(qa/'zero-capture/metadata.json');part=read(qa/f"zero-capture/track-{demo['clip']['part']}.json")
    data=dict(title=meta['title'],artist=meta.get('artist'),part=part.get('name',f"Track{demo['clip']['part']+1}"),clip=demo['clip'],duration=render['seconds'],notes=notes,
        before=label(target['state']),after=label(demo['chosen']['state']),influenced=1,played_attacks=sum(n['changed']for n in notes),donors=len(demo['chosen']['donor_refs']),controls=demo['controls'],
        rates={k:dict(draws=v['draws'],released=v['released'],changed=v['changed_sound_level'])for k,v in result['rates'].items()},facts=result['facts'],source_notes=result['counts']['note_objects'],
        native_status=audit['status'],fidelity_scope=audit['fidelity_scope'],standalone_roundtrip_pass=all(r['standalone_roundtrip_pass']for r in audit['artifact_fidelity']),
        accent_context=dict(dynamic=target['dynamic_marking'],meter=target['source_meter'],position_q=target['position_q'],duration_q=target['duration_q'],
            options=[dict(marking=label(o['state']),declarations=len(o['donor_refs']))for o in demo['decision']['evidence']['options']],
            donor_locations=[dict(bar=int(r.split(':')[3]),voice=int(r.split(':')[4])+1,beat_index=int(r.split(':')[5])+1)for r in demo['chosen']['donor_refs']]),
        fresh=dict(title=fr['title'],status=fr['status'],notes=fr['counts']['note_objects'],facts=fr['facts'],counts=fr['counts'],actual_changed=fr['status']=='PASS_SYMBOLIC_LOCAL_ACCENTS_CHANGE',seed=str(selection['seed']),sampling=selection['pool_rule']),
        evidence_hashes={str(p.resolve()):sha(p)for p in[qa/'result.json',qa/'demonstration.json',native/'independent-accent-artifacts.json',native/'accent-native-snapshot.json',fresh/'result.json',capture.parent/'selection.json']})
    (native/'preview.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (native/'index.html').write_text((Path(__file__).parent/'dynamic-preview.html').read_text(encoding='utf-8'),encoding='utf-8')
    return dict(status='REVIEW_BUILT_UI_QA_PENDING',path=str((native/'index.html').resolve()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('qa',type=Path);p.add_argument('native',type=Path);p.add_argument('fresh',type=Path);a=p.parse_args();print(json.dumps(build(a.qa,a.native,a.fresh)))
