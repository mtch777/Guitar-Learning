"""Prepare a small source-identification check, never edited/generated music."""
import argparse
from difflib import SequenceMatcher
from fractions import Fraction as F
import hashlib
import html
import json
from pathlib import Path
import shutil


def build(report, corpus, out):
    out.mkdir(exist_ok=False); selected=[]; used=set(); families=[]; jobs=[]
    # Three strict and three more rhythmically variable detections, distinct songs.
    for strict in (True, False):
        for song in report['songs']:
            if song['song_id'] in used or len([s for s in selected if s['strict']==strict])>=3:continue
            family=song['candidate_work_family']
            # Conservative sampling exclusion, not a duplicate-equivalence claim.
            if any(SequenceMatcher(None,family,old).ratio()>.86 for old in families):continue
            folder=corpus/str(song['song_id'])
            meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8-sig'))
            quality=json.loads((folder/'gp7-validation.json').read_text(encoding='utf-8-sig'))
            if meta.get('aiGenerated') is not False or meta.get('isJunk') is not False or not quality.get('roundtripPass'):continue
            found=None
            for ti,track in enumerate(song['tracks']):
                if not track['guitar_or_bass'] or not track['temporal_relationships_eligible']:continue
                by_id={r['occurrence']:r for r in track['rows']}
                for candidate in track['pedal_candidates']:
                    error=F(candidate['relative_period_error'])
                    if (error==0)!=strict:continue
                    target=[by_id[i] for run in candidate['members'] for event in run for i in event]
                    first=min(r['bar'] for r in target);last=max(r['bar'] for r in target)
                    if last-first>3:continue
                    # Avoid source repeats in this short review window: renderer must
                    # not silently substitute a different occurrence of the passage.
                    start=max(1,first-1);end=min(len(song['shared_layout']),last+1)
                    visits=[v['bar'] for v in song['playback']['order']]
                    if any(visits.count(b)!=1 for b in range(start,end+1)):continue
                    found=(ti,track,candidate,target,start,end);break
                if found:break
            if not found:continue
            ti,track,candidate,target,start,end=found
            ident=f'case-{len(selected)+1:02d}'; gp=out/(ident+'.gp');shutil.copyfile(folder/'score.gp',gp)
            source_hash=hashlib.sha256((folder/'score.gp').read_bytes()).hexdigest()
            if hashlib.sha256(gp.read_bytes()).hexdigest()!=source_hash:raise ValueError('Source copy changed')
            base=F(song['shared_layout'][start-1]['start_q']);limit=F(song['shared_layout'][end-1]['start_q'])+F(song['shared_layout'][end-1]['span_q'])
            notes=[r for r in track['rows'] if F(r['onset_q'])<limit and F(r['onset_q'])+F(r['duration_q'])>base and r['midi'] is not None]
            selected.append(dict(id=ident,title=song['title'],track=track['name'] or f'Track {ti+1}',start_bar=start,end_bar=end,
                                 strict=strict,anchor=candidate['anchor_midi'],target_ids=[r['occurrence'] for r in target],
                                 source_sha256=source_hash,song_id=song['song_id'],revision_id=song['revision_id'],
                                 base_q=str(base),end_q=str(limit),notes=notes,candidate=candidate))
            for mode in ('context','focused'):
                jobs.append(dict(case_id=ident,method='unchanged_source',mode=mode,file=str(gp.resolve()),track=ti,start_bar=start,end_bar=end,
                                 target_bar=min(r['bar'] for r in target),target_offset_q=min(target,key=lambda r:F(r['onset_q']))['bar_offset_q'],out=str((out/(ident+'.'+mode+'.wav')).resolve())))
            used.add(song['song_id'])
            families.append(family)
    if len(selected)!=6:raise ValueError(f'Expected 6 source cases, found {len(selected)}')
    (out/'cases.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
    (out/'render-jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    cards=[]
    for case in selected:
        notes=case['notes'];low=min(r['midi'] for r in notes);high=max(r['midi'] for r in notes);base=F(case['base_q']);span=F(case['end_q'])-base
        rects=[];targets=set(case['target_ids'])
        for n in notes:
            x=max(F(0),F(n['onset_q'])-base)/span*960
            end=min(F(case['end_q']),F(n['onset_q'])+F(n['duration_q']))
            width=(end-max(base,F(n['onset_q'])))/span*960
            anchor=n['occurrence'] in targets and n['midi']==case['anchor']
            color='#f6c85f' if anchor else '#69a7c7'
            rects.append(f'<rect x="{float(x):.2f}" y="{(high-n["midi"])*7+5}" width="{max(1,float(width)):.2f}" height="6" fill="{color}"/>')
        ident=case['id'];title=html.escape(case['title']);track=html.escape(case['track'])
        cards.append(f'''<article data-id="{ident}"><h2>{ident}: {title}</h2><p>{track} · source bars {case['start_bar']}–{case['end_bar']}</p>
<p><b>Unchanged source music.</b> Gold marks the note the script identified as a repeating anchor; blue shows the surrounding notes on this track.</p>
<svg role="img" aria-label="Source track notes with proposed anchor highlighted" viewBox="0 0 960 {(high-low+1)*7+10}">{''.join(rects)}</svg>
<p>Full arrangement</p><audio controls preload="metadata" src="{ident}.context.wav"></audio>
<p>Same passage, selected track</p><audio controls preload="metadata" src="{ident}.focused.wav"></audio>
<p><b>Does the gold note act as a repeating anchor while the other notes provide contrast?</b></p>
<select aria-label="Anchor judgment"><option value="">Not reviewed</option><option>Yes</option><option>No</option><option>Unclear</option></select>
<p>Optional: where does that description stop fitting?</p><textarea aria-label="Optional musical explanation"></textarea>
<p><a href="{ident}.gp">Open the unchanged source GP</a></p></article>''')
    fingerprint=hashlib.sha256(json.dumps([(c['source_sha256'],c['target_ids']) for c in selected]).encode()).hexdigest()[:16]
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Source pattern identification</title>
<style>body{background:#101820;color:#edf2f5;font:17px system-ui;max-width:1000px;margin:auto;padding:24px}article{border:1px solid #456;padding:22px;margin:24px 0;border-radius:12px}p{line-height:1.5}svg{width:100%;background:#182630;max-height:260px}audio{width:100%}select,textarea,button{font:inherit;padding:10px}textarea{width:95%;min-height:60px}a{color:#86d5ff}</style>
<h1>Did we identify a repeating anchor?</h1><p>This checks analysis of six actual source passages. Nothing was composed, edited or varied. It does not ask which version sounds better.</p>
<p>The previews use a synthetic soundfont. Judge the repeating-note pattern, not guitar tone or articulation. “Unclear” is useful. Responses stay on this computer until you export them.</p>
<button id="export">Export feedback</button>'''+''.join(cards)+'''<script>
const key='pedal-identification-FINGERPRINT';let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch{}
const cards=[...document.querySelectorAll('article')];for(const c of cards){const s=c.querySelector('select'),t=c.querySelector('textarea');s.value=saved[c.dataset.id]?.answer||'';t.value=saved[c.dataset.id]?.notes||'';for(const el of [s,t])el.addEventListener('change',()=>{saved[c.dataset.id]={answer:s.value,notes:t.value};localStorage.setItem(key,JSON.stringify(saved))})}
document.querySelector('#export').onclick=()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify({study:key,judgments:saved},null,2)],{type:'application/json'}));a.href=url;a.download='source-pattern-feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
for(const audio of document.querySelectorAll('audio'))audio.onplay=()=>{for(const other of document.querySelectorAll('audio'))if(other!==audio)other.pause()};
</script></html>'''
    (out/'index.html').write_text(page.replace('FINGERPRINT',fingerprint),encoding='utf-8')
    return dict(cases=len(selected),source_copies_byte_identical=True,source_song_ids=[c['song_id'] for c in selected],fingerprint=fingerprint)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);p.add_argument('corpus',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Source review must stay private')
    print(json.dumps(build(json.loads(a.report.read_text(encoding='utf-8')),a.corpus,a.out)))
