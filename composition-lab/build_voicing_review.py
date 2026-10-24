"""Small private listening review populated from verified intervention artifacts."""
import argparse
from html import escape
import json
from pathlib import Path


def build(qa,artifacts):
    report=json.loads((qa/'result.json').read_text());check=json.loads((artifacts/'independent-gp-audio-check.json').read_text())
    if report['status']!='PASS_EXACT_AND_SCOPED_SYMBOLIC_INTERVENTION' or check['status']!='PASS_NATIVE_GP_AND_AUDIO_CHANGE':raise ValueError('Verified source/inverse/GP/audio artifacts required')
    from source_fact_tier1 import extract,project_documents
    from run_reversible_tier_qa import extract_documents
    before=extract_documents(project_documents(extract(qa/'zero-capture')))['events'];after=extract_documents(project_documents(extract(qa/'changed-capture')))['events']
    old={e['id']:e for e in before};new={e['id']:e for e in after};docs=project_documents(extract(qa/'zero-capture'))
    def label(p):
        midi=int(p);return ('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')[midi%12]+'_'+str(midi//12-1)
    rows=[]
    changed_count=0
    for ref in report['decision']['member_refs']:
        e=old[ref];note=docs[f"track-{e['part_id']}.json"]['measures'][e['bar']-1]['voices'][e['voice']]['beats'][e['beat']]['notes'][e['note']]
        next_note=json.loads((qa/'changed-capture'/f"track-{e['part_id']}.json").read_text())['measures'][e['bar']-1]['voices'][e['voice']]['beats'][e['beat']]['notes'][e['note']]
        rows.append('<tr><td>'+str(note['string']+1)+'</td><td>'+label(e['pitch'])+' · fret '+str(note['fret'])+'</td><td>'+label(new[ref]['pitch'])+' · fret '+str(next_note['fret'])+'</td><td>'+('Ghost marking retained' if note.get('ghost') else 'Unchanged markings')+'</td></tr>')
        changed_count+=e['pitch']!=new[ref]['pitch']
    config=dict(duration=check['audio']['focused']['seconds'],cue=check['audio']['focused']['delta_start_seconds'],end=check['audio']['focused']['delta_end_seconds'])
    jobs=json.loads((artifacts/'audio-jobs.results.json').read_text());window=jobs[0]
    donor_refs=report['decision']['chosen']['donor_refs'];donor_bars=sorted({int(r.split(':')[3]) for r in donor_refs})
    pitch_classes='/'.join(label(old[r]['pitch']).split('_')[0] for r in report['decision']['member_refs'])
    count_text=' '.join(f"{s}%: {r['changed']}/{r['draws']} changed." for s,r in report['control_counts'].items())
    fields=dict(TITLE=docs['metadata.json']['title'],START=str(window['start_bar']),END=str(window['end_bar']),BAR=str(report['target_bar']),CUE=f"{config['cue']:.2f}",
        TRACK=docs[f"track-{report['part_id']}.json"]['name'],CHANGECOUNT=str(changed_count),SAMECOUNT=str(len(report['decision']['member_refs'])-changed_count),
        FRETS=' / '.join(map(str,report['decision']['fixed_string_frets'])),SPAN=str(report['decision']['fretted_span']),DONORS=str(len(donor_refs)),DONORBARS=', '.join(map(str,donor_bars)),PCS=pitch_classes,
        FACTS=f"{report['all_source_facts']:,}",COUNTS=count_text)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>One voicing change</title>
<style>body{font:16px/1.5 system-ui;margin:0;background:#101c24;color:#edf3f7}main{max-width:1000px;margin:auto;padding:24px}h1{font-size:26px;margin:0}h2{font-size:19px;margin:0 0 8px}p{margin:10px 0}small{color:#b8cbd5}.warning{border-left:4px solid #f1ba62;background:#342c20;padding:14px;margin:20px 0}.players{display:grid;grid-template-columns:1fr 1fr;gap:16px}section,details{background:#192c38;border:1px solid #385463;border-radius:8px;padding:16px}audio{width:100%;margin:12px 0}button,select{font:inherit;background:#294b60;color:#fff;border:1px solid #6b92a5;border-radius:5px;padding:7px 12px;cursor:pointer}.controls{display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin:18px 0}input{accent-color:#79c8ed}table{width:100%;border-collapse:collapse;margin:20px 0}th,td{text-align:left;border-bottom:1px solid #385463;padding:9px}a{color:#8ed1f5}.bar{height:12px;position:relative;background:#0c161e;margin:8px 0}.cue{position:absolute;background:#f1ba62;top:0;height:100%}.head{position:absolute;background:#fff;width:2px;top:-3px;height:18px}.time{font-variant-numeric:tabular-nums}@media(max-width:680px){.players{grid-template-columns:1fr}main{padding:16px}td,th{padding:7px;font-size:14px}}</style>
<main><h1>{{TITLE}} · one voicing change</h1><p>Bars {{START}}–{{END}} · change in bar {{BAR}}, around {{CUE}} seconds.<br><small>{{TRACK}}</small></p>
<p><b>{{CHANGECOUNT}} notes change register; {{SAMECOUNT}} stays.</b> Other notes, rhythm, parts, dynamics, effects and strings stay fixed.</p>
<div class="warning"><b>Playability is unresolved.</b> Keeping the strings fixed gives frets <b>{{FRETS}}</b>: a {{SPAN}}-fret simultaneous span. No tapping or other technique was added.</div>
<div class="controls"><label>Listen to <select id="mix"><option value="focused">Guitar only</option><option value="ensemble">All instruments</option></select></label><label>Speed <input id="speed" type="range" min="0" max="1" step="0.1" value="1"><output id="rate">1.0×</output></label><label><input id="loop" type="checkbox"> Loop</label></div>
<div class="players"><section><h2>0% · exact reconstruction</h2><audio id="zero" controls preload="auto" src="zero/focused.wav"></audio><div class="bar"><span class="cue"></span><span class="head"></span></div><div class="time">0.00s</div><button data-audio="zero">Hear change area</button><p><a href="zero/score.gp">Download GP</a></p></section>
<section><h2>Voicing used elsewhere in this song</h2><audio id="changed" controls preload="auto" src="changed/focused.wav"></audio><div class="bar"><span class="cue"></span><span class="head"></span></div><div class="time">0.00s</div><button data-audio="changed">Hear change area</button><p><a href="changed/score.gp">Download GP</a></p></section></div>
<table><thead><tr><th>Same string</th><th>Original</th><th>Changed</th><th>Expression</th></tr></thead><tbody>ROWS</tbody></table>
<p>The alternative occurs {{DONORS}} times in bars {{DONORBARS}}: same guitar, {{PCS}} pitch classes and duration. Surrounding parts and some markings differ there. The test retains the target’s original markings and accompaniment.</p>
<details><summary>Verified / still open</summary><p>✓ All {{FACTS}} source fields/containers recovered at 0%.<br>✓ Only {{CHANGECOUNT}} source fret values changed.<br>✓ Same pitch/interval and string/fret equations in both directions.<br>✓ Native GP: only the selected notes’ dependent pitch/fret fields changed.<br>✓ Source and 0% audio are sample-identical.<br>✓ Changed audio has a measured waveform difference.<br>○ Musical suitability and human execution remain unjudged.</p><p>{{COUNTS}} This observed alternative requires both coordinates released; either alone correctly refuses it.</p><p><a href="zero/score.exact-model-bends.json">0% bend companion</a> · <a href="changed/score.exact-model-bends.json">Changed bend companion</a></p></details>
</main><script>const cfg=CONFIG;const players=[document.querySelector('#zero'),document.querySelector('#changed')];const speed=document.querySelector('#speed');
function applySpeed(){const n=Number(speed.value);document.querySelector('#rate').textContent=n===0?'Paused':n.toFixed(1)+'×';for(const p of players){if(n===0)p.pause();else p.playbackRate=n;}}
speed.addEventListener('input',applySpeed);document.querySelector('#loop').addEventListener('change',e=>players.forEach(p=>p.loop=e.target.checked));
for(const p of players){const section=p.closest('section'),cue=section.querySelector('.cue'),head=section.querySelector('.head');cue.style.left=(100*cfg.cue/cfg.duration)+'%';cue.style.width=(100*(cfg.end-cfg.cue)/cfg.duration)+'%';p.addEventListener('play',()=>{if(Number(speed.value)===0){p.pause();return;}players.filter(q=>q!==p).forEach(q=>q.pause());});p.addEventListener('timeupdate',()=>{head.style.left=(100*Math.min(p.currentTime,cfg.duration)/cfg.duration)+'%';section.querySelector('.time').textContent=p.currentTime.toFixed(2)+'s';});}
document.querySelector('#mix').addEventListener('change',e=>{for(const p of players){p.pause();p.src=p.id+'/'+e.target.value+'.wav';p.load();}applySpeed();});
for(const button of document.querySelectorAll('[data-audio]'))button.addEventListener('click',async()=>{const p=document.getElementById(button.dataset.audio);if(Number(speed.value)===0){speed.value='1';applySpeed();}await p.play();if(p.readyState<2)await new Promise(resolve=>p.addEventListener('loadeddata',resolve,{once:true}));p.currentTime=Math.max(0,cfg.cue-.4);});</script></html>'''
    page=page.replace('ROWS',''.join(rows)).replace('CONFIG',json.dumps(config))
    for key,value in fields.items():page=page.replace('{{'+key+'}}',escape(value))
    (artifacts/'index.html').write_text(page,encoding='utf-8');return artifacts/'index.html'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('qa',type=Path);p.add_argument('artifacts',type=Path);a=p.parse_args();print(build(a.qa,a.artifacts))
