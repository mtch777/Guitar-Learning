"""Private source playback review: recorded cases plus every changed source scope.

Reuses the verified full-range piano roll and on-demand unchanged-score renderer.
Nothing source-derived is emitted outside the explicitly private output directory.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pedal_register import analyze_register
from pedal_evidence import analyze_evidence
from source_semantics import seconds_between


def support_regions(analysis, rows, sustain_chains=()):
    """Complete evidence chains including their terminal anchor burst.

    These are operational support bounds, not inferred musical phrases.
    """
    chains=[];byid={n['occurrence']:n for n in rows};groups={}
    for n in rows:
        if not n['tie_destination']:groups.setdefault(F(n['onset_q']),[]).append(n)
    for c in analysis['cycles']:
        if not chains or chains[-1][-1]['return_q']!=c['call_start_q']:chains.append([])
        chains[-1].append(c)
    regions=[]
    for chain in chains:
        if len(chain)<2:raise ValueError('A support region must contain repeated exchanges')
        first=F(chain[0]['call_start_q']);last=F(chain[-1]['return_q']);terminal=[]
        for q,ns in sorted(groups.items()):
            if q<last:continue
            calls=[n for n in ns if analysis['roles'].get(n['occurrence'])=='call']
            if not calls:
                if all(n['midi'] is None and 'dead' in n.get('effects',[]) for n in ns):continue
                break
            terminal.extend(calls)
        if not terminal:raise ValueError('Final return missing from source evidence')
        members=[byid[i] for c in chain for i in c['call_members']+c['response_members']]+terminal
        terminal_ids={n['occurrence'] for n in terminal}
        for sustain in sustain_chains:
            if sustain['origin'] in terminal_ids:
                members.extend(byid[i] for i in sustain['members'][1:] if i in byid)
        regions.append(dict(start_q=str(first),end_q=str(max(F(n['onset_q'])+F(n['duration_q']) for n in members)),
            start_bar=min(n['bar'] for n in members),end_bar=max(n['bar'] for n in members),cycles=chain,
            members={n['occurrence'] for n in members},return_members={n['occurrence'] for n in terminal}))
    return regions


def build(report,fixtures,before,after,corpus,out):
    out.mkdir(parents=True,exist_ok=False)
    for name in ['cases','scores','audio']:(out/name).mkdir()
    songs={s['song_id']:s for s in report['songs']}
    old={(s['song_id'],s['part_id'],s['section_start']):s for s in before}
    new={(s['song_id'],s['part_id'],s['section_start']):s for s in after}
    requests=[]
    for f in fixtures:
        requests.append(dict(f,direction='checked',before=analyze_register(f['rows']),after=analyze_evidence(f['rows']),
            review_message='Recorded feedback case. Analysis uses this exact displayed excerpt; this is not a claim that it is a complete phrase.'))
    for f in fixtures:
        if f['expected']:continue
        song=songs[f['song_id']];track=next(t for t in song['tracks'] if t['part_id']==f['part_id'])
        for section in {n['section_start'] for n in f['rows']}:
            key=(f['song_id'],f['part_id'],section)
            if key not in new:continue
            a=new[key];b=old[key]
            if not any(a['roles'].get(n['occurrence'])=='call' for n in f['rows']):continue
            rows=[n for n in track['rows'] if n['section_start']==section]
            target={n['occurrence'] for n in f['rows'] if a['roles'].get(n['occurrence'])=='call'}
            for region in support_regions(a,track['rows'],track.get('sustain_relationships',{}).get('chains',[])):
                if not target & region['members']:continue
                selected_roles={i:role for i,role in a['roles'].items() if i in region['members']}
                selected_anchors=sorted({n['midi'] for n in track['rows'] if selected_roles.get(n['occurrence'])=='call'})
                requests.append(dict(song_id=key[0],part_id=key[1],song=f['song'],track=f['track'],
                    bars=[region['start_bar'],region['end_bar']],direction='scope',before=b,
                    after=dict(a,cycles=region['cycles'],roles=selected_roles,anchor_pitches=selected_anchors),focus_bar=region['start_bar'],reported_bars=f['bars'],
                    return_members=region['return_members'],
                    review_message=f"The short excerpt at bars {f['bars'][0]}–{f['bars'][1]} does not establish a pedal on its own. This wider view shows the complete supporting pattern: {len(region['cycles'])} exchanges, including the closing return. Check whether these are connected musical exchanges; no new pedal is being claimed inside the short excerpt."))
    for key,a in new.items():
        b=old[key]
        if a['roles']==b['roles']:continue
        song=songs[key[0]];track=next(t for t in song['tracks'] if t['part_id']==key[1])
        rows=[n for n in track['rows'] if n['section_start']==key[2]]
        direction='lost' if b['accepted'] and not a['accepted'] else 'gained' if a['accepted'] and not b['accepted'] else 'changed'
        requests.append(dict(song_id=key[0],part_id=key[1],song=song['title'],track=track['name'].strip() or 'Unnamed track',
            bars=[min(n['bar'] for n in rows),max(n['bar'] for n in rows)],direction=direction,before=b,after=a,
            review_message='Complete source analysis scope. This can contain several musical phrases. Compare the highlighted occurrences; section boundaries are not inferred phrase boundaries.'))
    catalogue=[];jobs={};counts=Counter();copied=set()
    for index,request in enumerate(requests):
        sid=request['song_id'];song=songs[sid];track=next(t for t in song['tracks'] if t['part_id']==request['part_id']);ti=song['tracks'].index(track)
        layout=song['shared_layout'];first,last=request['bars'];ident=f"{request['direction']}-{index+1:05d}"
        if sid not in copied:
            src=corpus/str(sid)/'score.gp';dest=out/'scores'/f'{sid}.gp';shutil.copyfile(src,dest)
            assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dest.read_bytes()).digest()
            copied.add(sid)
        windows=[];start=first
        b,a=request['before'],request['after']
        returns=set().union(*(r['return_members'] for r in support_regions(a,track['rows']) if a['accepted'])) if a['accepted'] else set()
        while start<=last:
            end=start;base=F(layout[start-1]['start_q'])
            while end<last:
                limit=F(layout[end]['start_q'])+F(layout[end]['span_q'])
                seconds=seconds_between(base,limit,song['timeline'])
                if end-start>=5 or seconds is None or seconds>24:break
                end+=1
            limit=F(layout[end-1]['start_q'])+F(layout[end-1]['span_q'])
            seconds=seconds_between(base,limit,song['timeline']);wid=f'{ident}-{len(windows)+1:03d}'
            playable=seconds is not None and 0<seconds<=35 and all(sum(v['bar']==bar for v in song['playback']['order'])==1 for bar in range(start,end+1))
            notes=[]
            ties={m:c['origin'] for c in track.get('sustain_relationships',{}).get('chains',[]) for m in c['members'][1:]}
            for n in track['rows']:
                q=F(n['onset_q']);stop=q+F(n['duration_q'])
                if n['midi'] is None or q>=limit or stop<=base:continue
                origin=ties.get(n['occurrence'],n['occurrence'])
                notes.append(dict(id=n['occurrence'],pitch=n['midi'],bar=n['bar'],onset_q=n['onset_q'],duration_q=n['duration_q'],
                    before=b['roles'].get(origin,'context'),after=a['roles'].get(origin,'context'),
                    after_function='closing return' if origin in returns else a['roles'].get(origin,'context'),tied=bool(n['tie_destination'])))
            points=sorted({base,limit}|{F(t['onset_q']) for t in song['timeline']['tempo'] if base<F(t['onset_q'])<limit})
            windows.append(dict(id=wid,start_bar=start,end_bar=end,base_q=str(base),end_q=str(limit),seconds=seconds,playable=playable,notes=notes,
                time_map=[dict(q=str(q),seconds=seconds_between(base,q,song['timeline'])) for q in points]))
            if playable:
                jobs[wid]=[dict(case_id=wid,mode=mode,method='unchanged_source',file=str((out/'scores'/f'{sid}.gp').resolve()),track=ti,
                    start_bar=start,end_bar=end,target_bar=start,target_offset_q='0',out=str((out/'audio'/f'{wid}.{mode}.wav').resolve())) for mode in ['context','focused']]
            start=end+1
        entry=dict(id=ident,direction=request['direction'],song=request['song'],track=request['track'],song_id=sid,part_id=track['part_id'],
            start_bar=first,end_bar=last,start_q=windows[0]['base_q'],end_q=windows[-1]['end_q'],whole_scope_flip=b['accepted']!=a['accepted'],
            roundtrip_pass=True,review_message=request['review_message'],before_accepted=b['accepted'],after_accepted=a['accepted'])
        entry['initial_window']=next((i for i,w in enumerate(windows) if w['start_bar']<=request.get('focus_bar',first)<=w['end_bar']),0)
        entry['reported_bars']=request.get('reported_bars')
        # Preserve real fidelity status rather than inferring it from serialization.
        quality=json.loads((corpus/str(sid)/'gp7-validation.json').read_text(encoding='utf-8-sig'))
        entry['roundtrip_pass']=quality.get('roundtripPass')
        detail=dict(entry,windows=windows,bars=[dict(number=i+1,start_q=layout[i]['start_q'],span_q=layout[i]['span_q']) for i in range(first-1,last)],
                    before_cycles=b['cycles'],after_cycles=a['cycles'],before_anchor=b['anchor_pitches'],after_anchor=a['anchor_pitches'])
        (out/'cases'/f'{ident}.json').write_text(json.dumps(detail,separators=(',',':')),encoding='utf-8')
        catalogue.append(entry);counts[request['direction']]+=1;counts['windows']+=len(windows)
    manifest=dict(schema='pedal-evidence-review-v1',cases=catalogue,counts=dict(counts),
        dataset_sha256=hashlib.sha256(json.dumps([fixtures,after,hashlib.sha256(Path(__file__).read_bytes()).hexdigest()],separators=(',',':')).encode()).hexdigest(),
        algorithm_sha256=hashlib.sha256((Path(__file__).resolve().parents[2]/'pedal_evidence.py').read_bytes()).hexdigest(),
        summary=f"{counts['checked']} recorded cases · {counts['scope']} full supporting patterns · {counts['lost']} scopes removed · {counts['gained']} added · {counts['changed']} with changed highlights. Source audio is unchanged.",
        definition='Before: frozen register detector. After: experimental local-evidence correction. Recorded excerpts and complete source scopes are separate queues. This is software and source-evidence validation; listening acceptance is pending.')
    (out/'catalogue.json').write_text(json.dumps(manifest,separators=(',',':')),encoding='utf-8')
    (out/'render-index.json').write_text(json.dumps(jobs,separators=(',',':')),encoding='utf-8')
    for name in ['pedal-evidence.html','pedal-evidence.js']:shutil.copyfile(Path(__file__).resolve().parents[2]/name,out/('index.html' if name.endswith('.html') else name))
    print(json.dumps(dict(counts)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['report','fixtures','before','after','corpus','out']:p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    build(*(json.loads(getattr(a,n).read_text(encoding='utf-8')) for n in ['report','fixtures','before','after']),a.corpus,a.out)
