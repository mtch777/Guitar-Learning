"""Exhaustive private before/after tagged-span comparison on identical sources."""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib,json,shutil
from pathlib import Path
from source_semantics import seconds_between


def union(spans):
    out=[]
    for lo,hi in sorted((F(a),F(b)) for a,b in spans if F(a)<F(b)):
        if out and lo<=out[-1][1]:out[-1]=(out[-1][0],max(hi,out[-1][1]))
        else:out.append((lo,hi))
    return out


def subtract(left,right):
    out=[]
    for lo,hi in union(left):
        cursor=lo
        for a,b in union(right):
            if b<=cursor:continue
            if a>=hi:break
            if cursor<a:out.append((cursor,min(a,hi)))
            cursor=max(cursor,b)
            if cursor>=hi:break
        if cursor<hi:out.append((cursor,hi))
    return out


def after_spans(item,track,stop):
    chains=[]
    for c in item['cycles']:
        if not chains or chains[-1][-1]['return_q']!=c['call_start_q']:chains.append([])
        chains[-1].append(c)
    spans=[]
    sustain={c['origin']:F(c['end_q']) for c in track.get('sustain_relationships',{}).get('chains',[])}
    for i,chain in enumerate(chains):
        lo=F(chain[0]['call_start_q']);limit=F(chains[i+1][0]['call_start_q']) if i+1<len(chains) else stop
        members=[n for n in track['rows'] if n['occurrence'] in item['roles'] and lo<=F(n['onset_q'])<limit]
        if members:spans.append((lo,min(stop,max(sustain.get(n['occurrence'],F(n['onset_q'])+F(n['duration_q'])) for n in members))))
    return union(spans)


def build(report,old,new,corpus,out):
    out.mkdir(parents=True,exist_ok=False);(out/'cases').mkdir();(out/'scores').mkdir();(out/'audio').mkdir()
    old_index={(x['song_id'],x['part_id']):x['regions'] for x in old}
    new_index={(x['song_id'],x['part_id'],x['section_start']):x for x in new}
    cases=[];jobs={};counts=defaultdict(int)
    for song in report['songs']:
        sid=song['song_id'];copied=False
        for ti,track in enumerate(song['tracks']):
            if (sid,track['part_id']) not in old_index:continue
            old_members_all={i for r in old_index[sid,track['part_id']] for i in r['anchor_occurrences']}
            after_roles_all={i:role for (song_id,part_id,_),record in new_index.items()
                             if song_id==sid and part_id==track['part_id'] for i,role in record['roles'].items()}
            for section in track['sections']:
                key=(sid,track['part_id'],section['id']);item=new_index.get(key)
                regions=[r for r in old_index[sid,track['part_id']] if r['section_start']==section['id']]
                if item is None:
                    if regions:raise ValueError('Tagged scope missing from new analysis')
                    continue  # Empty source sections have no written-note analysis.
                before=union([(r['start_q'],r['end_q']) for r in regions]);after=after_spans(item,track,F(section['end_q']))
                counts['compared_source_scopes']+=1
                if before and not after:counts['whole_scopes_removed']+=1
                if after and not before:counts['whole_scopes_added']+=1
                for direction,a,b in [('lost',before,after),('gained',after,before)]:
                    for lo,hi in subtract(a,b):
                        # Exact rational difference, not a new phrase inference.
                        if subtract([(lo,hi)],a) or not subtract([(lo,hi)],b)==[(lo,hi)]:raise ValueError('Invalid diff')
                        ident=f'{direction}-{len(cases)+1:05d}'
                        layout=song['shared_layout']
                        covered=[i+1 for i,bar in enumerate(layout) if F(bar['start_q'])<hi and F(bar['start_q'])+F(bar['span_q'])>lo]
                        if not covered:raise ValueError('Diff outside score')
                        first=max(1,min(covered)-1);last=min(len(layout),max(covered)+1)
                        windows=[];start=first
                        while start<=last:
                            end=start;base=F(layout[start-1]['start_q'])
                            while end<last:
                                limit=F(layout[end]['start_q'])+F(layout[end]['span_q'])
                                seconds=seconds_between(base,limit,song['timeline'])
                                if end-start>=5 or seconds is None or seconds>24:break
                                end+=1
                            limit=F(layout[end-1]['start_q'])+F(layout[end-1]['span_q'])
                            seconds=seconds_between(base,limit,song['timeline'])
                            wid=f'{ident}-{len(windows)+1:03d}'
                            playable=seconds is not None and 0<seconds<=35 and all(sum(v['bar']==bar for v in song['playback']['order'])==1 for bar in range(start,end+1))
                            notes=[]
                            tie_origins={m:c['origin'] for c in track.get('sustain_relationships',{}).get('chains',[]) for m in c['members'][1:]}
                            for n in track['rows']:
                                q=F(n['onset_q']);stop=q+F(n['duration_q'])
                                if n['midi'] is None or q>=limit or stop<=base:continue
                                origin=tie_origins.get(n['occurrence'],n['occurrence'])
                                notes.append(dict(id=n['occurrence'],pitch=n['midi'],bar=n['bar'],onset_q=str(q),duration_q=n['duration_q'],
                                    before='call' if origin in old_members_all else 'context',after=after_roles_all.get(origin,'context'),
                                    tied=bool(n['tie_destination'])))
                            points=sorted({base,limit}|{F(t['onset_q']) for t in song['timeline']['tempo'] if base<F(t['onset_q'])<limit})
                            window=dict(id=wid,start_bar=start,end_bar=end,base_q=str(base),end_q=str(limit),seconds=seconds,
                                playable=playable,notes=notes,time_map=[dict(q=str(q),seconds=seconds_between(base,q,song['timeline'])) for q in points])
                            windows.append(window)
                            if playable:
                                jobs[wid]=[dict(case_id=wid,mode=mode,method='unchanged_source',file=str((out/'scores'/f'{sid}.gp').resolve()),track=ti,
                                    start_bar=start,end_bar=end,target_bar=start,target_offset_q='0',out=str((out/'audio'/f'{wid}.{mode}.wav').resolve())) for mode in ('context','focused')]
                            start=end+1
                        if not copied:
                            src=corpus/str(sid)/'score.gp';dest=out/'scores'/f'{sid}.gp';shutil.copyfile(src,dest)
                            if hashlib.sha256(src.read_bytes()).digest()!=hashlib.sha256(dest.read_bytes()).digest():raise ValueError('Source GP changed')
                            copied=True
                        quality=json.loads((corpus/str(sid)/'gp7-validation.json').read_text(encoding='utf-8-sig'))
                        entry=dict(id=ident,direction=direction,song=song['title'],track=track['name'].strip() or f'Track {ti+1}',
                            song_id=sid,part_id=track['part_id'],section=section['id'],start_bar=min(covered),end_bar=max(covered),
                            start_q=str(lo),end_q=str(hi),whole_scope_flip=not bool(b),roundtrip_pass=quality.get('roundtripPass'),windows=len(windows))
                        detail=dict(entry,windows=windows,bars=[dict(number=i+1,start_q=layout[i]['start_q'],span_q=layout[i]['span_q']) for i in range(first-1,last)],before_spans=[[str(x),str(y)] for x,y in before],after_spans=[[str(x),str(y)] for x,y in after])
                        (out/'cases'/f'{ident}.json').write_text(json.dumps(detail,separators=(',',':')),encoding='utf-8')
                        cases.append(entry);counts[direction+'_spans']+=1;counts['review_windows']+=len(windows)
    manifest=dict(schema='pedal-tag-diff-v1',counts=dict(counts),cases=cases,
        definition='Exact interval differences within the same song, track and source section. These are tagged spans, not inferred musical phrases.',
        before='Frozen pedal-feedback-v2 corpus-regions.json',after='pedal-register-review-v4 corpus-analysis.json')
    (out/'catalogue.json').write_text(json.dumps(manifest,separators=(',',':')),encoding='utf-8')
    (out/'render-index.json').write_text(json.dumps(jobs,separators=(',',':')),encoding='utf-8')
    for name in ('pedal-diff.html','pedal-diff.js'):shutil.copyfile(Path(__file__).parents[2]/name,out/('index.html' if name.endswith('.html') else name))
    print(json.dumps(counts))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('report','old','new','corpus','out'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private source evidence must stay in local-artifacts')
    build(json.loads(a.report.read_text(encoding='utf-8')),json.loads(a.old.read_text(encoding='utf-8')),json.loads(a.new.read_text(encoding='utf-8')),a.corpus,a.out)
    path=a.out/'catalogue.json';manifest=json.loads(path.read_text(encoding='utf-8'))
    manifest['input_sha256']={name:hashlib.sha256(getattr(a,name).read_bytes()).hexdigest() for name in ('report','old','new')}
    path.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf-8')
