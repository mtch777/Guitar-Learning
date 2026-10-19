"""Build a private, clearly labelled review of frozen generated comparisons."""
import argparse,hashlib,json,os,wave
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote
from playback_review import read_midi_notes


def build(manifest_path,output):
    manifest_path,output=Path(manifest_path),Path(output)
    if 'local-artifacts' not in output.resolve().parts:raise ValueError('Private output required')
    if output.exists():raise FileExistsError('Preserve existing review')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'));cases=[]
    for row in manifest['cases']:
        gp,audio=Path(row['gp']),Path(row['audio'])
        if hashlib.sha256(audio.read_bytes()).hexdigest()!=row['audio_sha256']:raise ValueError('Audio checksum mismatch')
        with wave.open(str(audio),'rb') as stream:
            if abs(stream.getnframes()/stream.getframerate()-row['seconds'])>1/stream.getframerate():raise ValueError('Audio duration mismatch')
        _,notes=read_midi_notes(gp.with_suffix('.mid'))
        if not notes or any(a<0 or b<a or b>row['seconds']+.01 for a,b,*_ in notes):raise ValueError('Invalid note timeline')
        if {n[4] for n in notes}!={0,2,4}:raise ValueError('Explicit three-role MIDI channel mapping required')
        score=json.loads(gp.with_suffix('.expected.json').read_text(encoding='utf-8'))
        if [t['name'] for t in score['tracks']]!=['harmony','melody','bass']:raise ValueError('Explicit ordered roles required')
        from compose_controlled import plain_core
        plain_core(gp,score)
        tempo=Fraction(score['tempo_bpm'])
        bars=[dict(seconds=float(Fraction(m['onset_q'])*60/tempo),number=m['number']) for m in score['tracks'][0]['measures']]
        case=dict(row,notes=notes,bars=bars,gp_sha256=hashlib.sha256(gp.read_bytes()).hexdigest())
        for key,path in [('gp',gp),('audio',audio)]:
            case[key]=quote(Path(os.path.relpath(path.resolve(),output.parent.resolve())).as_posix(),safe='/')
        cases.append(case)
    if any(len({c['seconds'] for c in cases if c['core']==core})!=1 for core in {c['core'] for c in cases}):raise ValueError('Matched durations required')
    pairs={(c['core'],c['method']) for c in cases}
    if len(pairs)!=len(cases) or any({c['method'] for c in cases if c['core']==core}!={'bar_reset','carry','register_carry'} for core,_ in pairs):
        raise ValueError('Exactly three matched methods per core required')
    data=json.dumps(dict(cases=cases,version=hashlib.sha256(manifest_path.read_bytes()).hexdigest()),separators=(',',':')).replace('<','\\u003c')
    output.write_text(TEMPLATE.replace('__DATA__',data),encoding='utf-8')
    return dict(cases=len(cases),output=str(output),human_reviews=0)


TEMPLATE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Melody across bars — controlled comparison</title>
<style>body{font:16px system-ui;background:#101d25;color:#edf5fa;max-width:1100px;margin:24px auto;padding:0 18px}h1{font-size:27px}p{line-height:1.5}.muted{color:#bdd0dc}.box{background:#1c303d;padding:18px;border:1px solid #456273;border-radius:10px;margin:14px 0}button,select,textarea{font:inherit;background:#294454;color:white;padding:9px;border:1px solid #7795a5;border-radius:5px}button{cursor:pointer}button[aria-pressed=true]{background:#416d55;border:2px solid #b4f9ce}a{color:#8fdaff}audio,textarea{width:100%;box-sizing:border-box}canvas{display:block;width:100%;height:330px;background:#12222c;touch-action:manipulation}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}label{display:inline-block;margin:8px 12px 8px 0}#status{min-height:24px;color:#ffd98a}.small{font-size:14px}</style>
<h1>Does the melody connect across bars?</h1><p><b>These are generated pieces, not original artist songs.</b> Compare three versions of the same generated piece. Only melody pitches/fingering change; harmony, bass, rhythm, form, instruments and performance stay locked.</p>
<div class="box"><b>Research result: neither change passed the full gate.</b><p class="small">Carry improved interval behavior but shifted register. Register carry corrected register but slightly worsened the written harmony-offset measurement. Existing defaults remain unchanged. Listening remains unjudged.</p></div>
<div class="box"><label>Generated piece <select id="core"></select></label><div id="methods" class="row"></div><h2 id="title"></h2><p id="description"></p><audio id="player" controls preload="metadata"></audio><p class="small muted">Switching methods keeps the same time. All audio uses the same alphaTab / Sonivox instrument renderer and fixed gain; this is not physical guitar or Guitar Pro RSE.</p><div class="row"><button id="restart">Start over</button><a id="gp" download>Download this Guitar Pro file</a><span id="clock"></span></div></div>
<div class="box"><h2>Piano roll</h2><p class="small">Green: harmony · blue: melody · gold: bass. White line: playback; grey lines: bars. Click a note to identify it and seek. Audio always includes all three parts. Filter the roll for a closer look.</p><label>Show notes <select id="part"><option value="all">All parts</option><option value="2">Melody</option><option value="0">Harmony</option><option value="4">Bass</option></select></label><canvas id="roll" aria-label="All three generated parts with playback line"></canvas><p id="status" role="status"></p></div>
<div class="box"><h2>Optional notes for later review</h2><p class="small">No scores or feedback are uploaded. Save/export records only your own answers. Automated checks leave these blank.</p><label>Melody connects across bars <select id="continuity"><option value="">Not answered</option><option>Yes</option><option>Mixed</option><option>No</option><option>Cannot judge</option></select></label><label>Register suits accompaniment <select id="register"><option value="">Not answered</option><option>Yes</option><option>Mixed</option><option>No</option><option>Cannot judge</option></select></label><label>Harmony fits <select id="harmony"><option value="">Not answered</option><option>Yes</option><option>Mixed</option><option>No</option><option>Cannot judge</option></select></label><textarea id="notes" rows="3" placeholder="What happens, and at what time?"></textarea><button id="export">Export my notes</button></div>
<script id="data" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),player=$('player'),canvas=$('roll'),ctx=canvas.getContext('2d');
const labels={bar_reset:'Reset each bar',carry:'Carry previous melody',register_carry:'Carry + source register'};
const descriptions={bar_reset:'Existing method: melody context resets each bar. Explicit generated-theme returns stay intact.',carry:'Keep the actual preceding melody context across a barline within the same supplied section. Reset at rests/gaps/section changes.',register_carry:'Same carry method, plus a fixed source-learned relative-register preference at eligible bar starts.'};
let active=null,hits=[],pendingTime=0,feedback={};const key='barline-review:'+data.version;
try{feedback=JSON.parse(localStorage.getItem(key)||'{}')}catch{}
function save(){if(!active)return;feedback[active.core+':'+active.method]=Object.fromEntries(['continuity','register','harmony','notes'].map(k=>[k,$(k).value]));try{localStorage.setItem(key,JSON.stringify(feedback))}catch{$('status').textContent='Browser saving unavailable; export to retain your notes.'}}
function choose(core,method){save();pendingTime=active&&active.core===core?player.currentTime:0;player.pause();active=data.cases.find(c=>c.core===core&&c.method===method);player.src=active.audio;$('gp').href=active.gp;$('title').textContent='Piece '+core+' · '+labels[method];$('description').textContent=descriptions[method];for(const b of $('methods').children)b.setAttribute('aria-pressed',String(b.dataset.method===method));const f=feedback[core+':'+method]||{};for(const k of ['continuity','register','harmony','notes'])$(k).value=f[k]||'';$('status').textContent='';draw()}
function name(p){return ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'][p%12]+(Math.floor(p/12)-1)}
function draw(){if(!active)return;const rect=canvas.getBoundingClientRect(),w=rect.width,h=330,dpr=devicePixelRatio||1;if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr)}ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);const visible=active.notes.filter(n=>$('part').value==='all'||String(n[4])===$('part').value),ps=visible.map(n=>n[2]);let low=Math.max(0,Math.min(...ps)-2),high=Math.min(127,Math.max(...ps)+2);if(high-low<12){low=Math.max(0,low-6);high=Math.min(127,low+12)}const row=h/(high-low+1),start=Math.floor(player.currentTime/8)*8,left=48,scale=(w-left)/8;hits=[];ctx.font='11px system-ui';for(let p=low;p<=high;p++){const y=(high-p)*row;ctx.strokeStyle='#29404e';ctx.beginPath();ctx.moveTo(left,y+row);ctx.lineTo(w,y+row);ctx.stroke();if(p%12===0||row>15){ctx.fillStyle='#b5cbd9';ctx.fillText(name(p),2,y+row*.8)}}for(const bar of active.bars){if(bar.seconds<start||bar.seconds>=start+8)continue;const x=left+(bar.seconds-start)*scale;ctx.strokeStyle='#748894';ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();ctx.fillStyle='#c5d7e0';ctx.fillText('bar '+bar.number,x+3,12)}for(const n of visible){if(n[1]<=start||n[0]>=start+8)continue;const x=left+Math.max(0,n[0]-start)*scale,y=(high-n[2])*row,ww=Math.max(2,(Math.min(n[1],start+8)-Math.max(n[0],start))*scale);ctx.fillStyle=({0:'#73cd97',2:'#66caff',4:'#ffd276'})[n[4]]||'#ddd';ctx.fillRect(x,y+1,ww,Math.max(2,row-2));ctx.strokeStyle='#142630';ctx.strokeRect(x,y+1,ww,Math.max(2,row-2));hits.push({n,x,y,w:ww,h:row})}const x=left+(player.currentTime-start)*scale;ctx.strokeStyle='white';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();ctx.lineWidth=1;$('clock').textContent=player.currentTime.toFixed(1)+' / '+active.seconds.toFixed(1)+' seconds'}
for(const core of [...new Set(data.cases.map(c=>c.core))])$('core').add(new Option('Piece '+core,core));for(const method of Object.keys(labels)){const b=document.createElement('button');b.textContent=labels[method];b.dataset.method=method;b.onclick=()=>choose(Number($('core').value),method);$('methods').append(b)}
$('part').onchange=()=>{draw();$('status').textContent=''};$('core').onchange=()=>choose(Number($('core').value),active.method);player.onloadedmetadata=()=>{player.currentTime=Math.min(pendingTime,Math.max(0,player.duration-.05));draw()};$('restart').onclick=()=>{player.currentTime=0;draw()};for(const k of ['continuity','register','harmony','notes'])$(k).oninput=save;
canvas.onclick=e=>{const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top,hit=hits.find(v=>x>=v.x&&x<=v.x+v.w&&y>=v.y&&y<=v.y+v.h);if(hit){player.currentTime=hit.n[0];$('status').textContent=name(hit.n[2])+' · '+hit.n[0].toFixed(2)+'–'+hit.n[1].toFixed(2)+' sec · '+({0:'harmony',2:'melody',4:'bass'})[hit.n[4]];draw()}};
$('export').onclick=()=>{save();const url=URL.createObjectURL(new Blob([JSON.stringify({format:'barline-listening-feedback-v1',version:data.version,feedback},null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='barline-listening-feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
function frame(){draw();requestAnimationFrame(frame)}choose(Number($('core').value),'bar_reset');requestAnimationFrame(frame);
</script></html>'''

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(build(a.manifest,a.output)))
