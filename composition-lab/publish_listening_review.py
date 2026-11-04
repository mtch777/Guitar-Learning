"""Populate the existing listening page from verified audio and measured notes.

No musical analysis, rendering, note generation, browser build, or score edits.
"""
from pathlib import Path
import argparse, copy, hashlib, json, math, os, re, tempfile, wave

LAB=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)
def number(value):return type(value)in(int,float)and math.isfinite(value)
def asset(root,name):
    require(isinstance(name,str)and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.wav',name),'Audio must be a relative WAV filename')
    path=(root/name).resolve();require(path.parent==root.resolve()and path.is_file(),'Missing or escaped audio asset')
    return path

def validate_clock(duration,ledger,bars):
    require(number(duration)and duration>0,'Invalid duration')
    require(isinstance(ledger,list)and all(isinstance(b,dict)and type(b.get('bar'))is int and number(b.get('time'))for b in ledger),'Invalid bar clock')
    require(len({b['bar']for b in ledger})==len(ledger),'Duplicate bar clock')
    require(all(a['bar']<b['bar']and a['time']<b['time']for a,b in zip(ledger,ledger[1:])),'Bar clocks must increase')
    times={b['bar']:b['time']for b in ledger};require(all(b in times for b in range(bars[0],bars[1]+2)),'Every bar boundary including end is required')
    require(abs(times[bars[0]])<=64/44100 and abs(times[bars[1]+1]-duration)<=64/44100,'Bar clocks do not span the audio')
    for b in ledger:
        beats=b.get('beat_times',[])
        require(isinstance(beats,list)and all(number(t)and b['time']<t<times.get(b['bar']+1,float('inf'))for t in beats),'Beat clock outside its bar')
        require(all(a<b for a,b in zip(beats,beats[1:])),'Beat clocks must increase')
    return [(b['bar'],len(b.get('beat_times',[])))for b in ledger]

def validate(data,assets):
    require(data.get('schema')=='listening-review/1','Expected listening-review/1')
    for key in('title','artist','playback_note'):
        require(isinstance(data.get(key),str)and data[key].strip(),f'Missing {key}')
    questions=data.get('questions');require(isinstance(questions,list)and 1<=len(questions)<=3 and all(isinstance(q,str)and q.strip()for q in questions),'Provide 1–3 specific listening questions')
    bars=data.get('bars');require(isinstance(bars,list)and len(bars)==2 and all(type(b)is int for b in bars)and 1<=bars[0]<=bars[1],'Invalid bar range')
    duration=data.get('seconds');ledger=data.get('bar_times');clock_shape=validate_clock(duration,ledger,bars)
    sections=data.get('sections');require(isinstance(sections,list)and sections,'Missing listening sections')
    for s in sections:require(type(s.get('first'))is int and type(s.get('last'))is int and bars[0]<=s['first']<=s['last']<=bars[1]and isinstance(s.get('label'),str),'Invalid listening section')
    require(len({s['first']for s in sections})==len(sections),'Duplicate section start')
    tracks=data.get('tracks',[]);silent=data.get('silent_tracks',[]);ids=[t.get('id')for t in tracks+silent]
    require(all(type(i)is int for i in ids)and len(set(ids))==len(ids)and len(ids)==data.get('all_parts'),'Part inventory mismatch')
    require(all(isinstance(t.get('name'),str)and type(t.get('percussion'))is bool for t in tracks+silent),'Missing part labels/types')
    versions=data.get('versions');require(isinstance(versions,list)and len(versions)>=2,'Need original and at least one changed version')
    names=[v.get('id')for v in versions];require(all(isinstance(n,str)and n!='none'and re.fullmatch('[A-Za-z0-9_-]+',n)for n in names)and len(set(names))==len(names),'Invalid version identities')
    require(data.get('original_version')==names[0]and versions[0].get('compare_to')is None,'First version must be untouched original, with no comparison')
    require(data.get('default_version',names[0])in names,'Unknown default version')
    separate_clocks=any('seconds'in v or 'bar_times'in v for v in versions)
    if separate_clocks:
        require(all('seconds'in v and 'bar_times'in v for v in versions),'Every version needs seconds and bar_times when clocks differ')
        require(versions[0]['seconds']==duration and versions[0]['bar_times']==ledger,'Top-level clock must remain the untouched original clock')
        for v in versions:require(validate_clock(v['seconds'],v['bar_times'],bars)==clock_shape,'Version clocks need corresponding bar and beat boundaries')
    written_coordinates=any('score_start_tick'in n or 'score_end_tick'in n for v in versions for n in v.get('notes',[]))
    require(not separate_clocks or written_coordinates,'Per-version clocks require written score coordinates')
    audio=[];formats=[];observed_parts=set()
    for index,v in enumerate(versions):
        for key in('label','description'):require(isinstance(v.get(key),str)and v[key].strip(),f'Missing version {key}')
        if index:require(v.get('compare_to')in names and v['compare_to']!=v['id'],'Changed version needs an explicit comparison baseline')
        version_duration=v['seconds']if separate_clocks else duration
        source=asset(assets,v.get('audio'));digest=sha(source);require(digest==v.get('audio_sha256'),'Audio hash differs from verified input')
        with wave.open(str(source),'rb')as w:
            require(w.getcomptype()=='NONE','Expected PCM WAV');require(abs(w.getnframes()/w.getframerate()-version_duration)<=1/w.getframerate(),'Audio duration differs from its declared clock')
            formats.append((w.getnchannels(),w.getsampwidth(),w.getframerate())+(()if separate_clocks else(w.getnframes(),)))
        require(isinstance(v.get('notes'),list),'Missing measured notes')
        for n in v['notes']:
            require(n.get('part')in ids and number(n.get('start'))and number(n.get('end'))and 0<=n['start']<n['end']<=version_duration+1/44100,'Note outside declared part/time')
            require(type(n.get('pitch'))is int and 0<=n['pitch']<=127,'Invalid played pitch')
            require(type(n.get('bar'))is int and n['bar']<=bars[1],'Missing source bar')
            require(all(k in n for k in('voice','velocity','fret','string','dead','ghost')),'Incomplete note comparison fields')
            if written_coordinates:
                require(type(n.get('score_start_tick'))is int and type(n.get('score_end_tick'))is int and n['score_start_tick']<n['score_end_tick'],'Complete written score coordinates are required')
                require(isinstance(n.get('comparison_identity'),str)and n['comparison_identity'],'Written score comparison requires stable identities')
            observed_parts.add(n['part'])
        audio.append((v,source,digest))
    if any('comparison_identity'in n for v in versions for n in v['notes']):
        for v in versions:
            identities=[n.get('comparison_identity')for n in v['notes']]
            require(all(isinstance(x,str)and x for x in identities),'Comparison identities must be complete')
            require(len(identities)==len(set(identities)),'Comparison identities must be unique within each version')
    require(len(set(formats))==1,'This review requires matched audio formats; undeclared clock changes cannot rescale audio')
    require(observed_parts=={t['id']for t in tracks},'Playing/silent part inventory differs from notes')
    return audio

def atomic_bytes(path,content):
    if path.exists()and path.read_bytes()==content:return False
    fd,temp=tempfile.mkstemp(prefix='.review-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb')as f:f.write(content)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return True

def publish(manifest,assets,out):
    data=json.loads(manifest.read_bytes());audio=validate(data,assets);current=copy.deepcopy(data)
    # Validate ALL input and destination identities before touching the current page.
    copies=[]
    for v,source,digest in audio:
        name=f'{v["id"]}-{digest[:16]}.wav';target=out/name
        require(not target.exists()or sha(target)==digest,'Existing audio destination differs; refusing overwrite')
        copies.append((source,target));next(x for x in current['versions']if x['id']==v['id'])['audio']=name
    out.mkdir(parents=True,exist_ok=True)
    for source,target in copies:
        if not target.exists():atomic_bytes(target,source.read_bytes())
    refreshed=0
    for source,name in((LAB/'arrangement-review.html','index.html'),(LAB/'arrangement-review.mjs','arrangement-review.mjs'),(LAB/'listening-change-summary.mjs','listening-change-summary.mjs')):
        refreshed+=atomic_bytes(out/name,source.read_bytes())
    atomic_bytes(out/'comparison.json',json.dumps(current,ensure_ascii=False,indent=2,allow_nan=False).encode('utf8'))
    require([v['notes']for v in current['versions']]==[v['notes']for v in data['versions']],'Note payload changed during publication')
    return dict(status='PUBLISHED_EXISTING_REVIEW',versions=len(audio),audio_rendered=0,ui_files_refreshed=refreshed,
        audio_sha256={v['id']:digest for v,source,digest in audio},notes_unchanged=True,page=str(out/'index.html'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('--assets',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(json.dumps(publish(a.manifest,a.assets or a.manifest.parent,a.out),indent=2))
