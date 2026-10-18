"""Extend a private excerpt without changing its GP or overwriting baseline audio."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import shutil
from source_semantics import seconds_between


def extend(root,report,dialogues,ident,end_bar):
    cases=json.loads((root/'cases.json').read_text(encoding='utf-8'));case=next(c for c in cases if c['id']==ident)
    backup=root/'cases.before-extension.json'
    if not backup.exists():backup.write_bytes((root/'cases.json').read_bytes())
    song=next(s for s in report['songs'] if s['song_id']==case['song_id']);part=int(case['notes'][0]['id'].split(':')[0])
    track=next(t for t in song['tracks'] if t['part_id']==part)
    item=next(x for x in dialogues if x['song_id']==song['song_id'] and x['part_id']==part)
    end_bar=min(end_bar,len(song['shared_layout']));base=F(case['base_q']);end=F(song['shared_layout'][end_bar-1]['start_q'])+F(song['shared_layout'][end_bar-1]['span_q'])
    if seconds_between(base,end,song['timeline'])>35:raise ValueError('Extended excerpt exceeds preview cap')
    if any(sum(v['bar']==b for v in song['playback']['order'])!=1 for b in range(case['start_bar'],end_bar+1)):raise ValueError('Repeated source bars require explicit playback occurrence selection')
    roles={n['occurrence']:e['kind'] for r in item['dialogues'] for e in r['events'] for n in e['notes']}
    notes=[]
    for n in track['rows']:
        q=F(n['onset_q']);stop=q+F(n['duration_q'])
        if n['midi'] is None or not(q<end and stop>base):continue
        role=roles.get(n['occurrence'],'context')
        if role=='unknown':role='context'
        if n['tie_destination'] and n['midi'] in case['anchor']:role='call_sustain'
        notes.append(dict(id=n['occurrence'],pitch=n['midi'],bar=n['bar'],string=n['string'],fret=n['fret'],
                          start=seconds_between(base,max(base,q),song['timeline']),end=seconds_between(base,min(end,stop),song['timeline']),
                          onset_q=n['onset_q'],duration_q=n['duration_q'],role=role))
    points=sorted({base,end}|{F(t['onset_q']) for t in song['timeline']['tempo'] if base<F(t['onset_q'])<end})
    case.update(end_bar=end_bar,end_q=str(end),notes=notes,time_map=[dict(seconds=seconds_between(base,q,song['timeline']),x=float((q-base)/(end-base)*960)) for q in points],
                audio_prefix=ident+'.extended',category='anchor_changes',heading='Same pedal idea, fewer notes in the anchor',
                explanation='The two-note anchor becomes a single low note and the pedal idea continues. The earlier short example stopped at that analysis split.',
                caveat='Extended through the continuing source section. The preview ends at the excerpt boundary, not a verified musical ending.')
    old_job=next(j for j in json.loads((root/'render-jobs.json').read_text()) if j['case_id']==ident)
    jobs=[dict(old_job,mode=mode,end_bar=end_bar,out=str((root/(case['audio_prefix']+'.'+mode+'.wav')).resolve())) for mode in ('context','focused')]
    (root/'extension-jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    (root/'cases.json').write_text(json.dumps(cases,separators=(',',':')),encoding='utf-8')
    for name in ('dialogue-explorer.html','dialogue-explorer.js'):shutil.copyfile(Path(__file__).parents[2]/name,root/('index.html' if name.endswith('.html') else name))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('report',type=Path);p.add_argument('dialogues',type=Path);p.add_argument('--id',required=True);p.add_argument('--end-bar',type=int,required=True);a=p.parse_args()
    if 'local-artifacts' not in a.root.resolve().parts:p.error('Private source excerpts only')
    extend(a.root,json.loads(a.report.read_text()),json.loads(a.dialogues.read_text()),a.id,a.end_bar)
