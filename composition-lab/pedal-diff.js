const $=s=>document.querySelector(s),catalogue=await(await fetch('catalogue.json')).json();
const frac=s=>{const[a,b=1]=String(s).split('/').map(Number);return a/b;};
const pitch=p=>['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'][((p%12)+12)%12]+(Math.floor(p/12)-1);
let direction='lost',mode='before',detail,part,active=$('#focused'),drawn=[],generation=0;
const counts=catalogue.counts;
$('#counts').textContent=`${counts.lost_spans} spans lost the label · ${counts.gained_spans} gained it. Entire source sections changing yes/no: ${counts.whole_scopes_removed} removed, ${counts.whole_scopes_added} added. ${counts.compared_source_scopes} source sections compared.`;
$('#definition').textContent=catalogue.definition;
function seconds(q){const map=part.time_map,t=frac(q);for(let i=1;i<map.length;i++)if(t<=frac(map[i].q)){const a=map[i-1],b=map[i];return a.seconds+(b.seconds-a.seconds)*(t-frac(a.q))/(frac(b.q)-frac(a.q));}return map.at(-1).seconds;}
function xAt(t){const map=part.time_map;for(let i=1;i<map.length;i++)if(t<=map[i].seconds){const a=map[i-1],b=map[i],q=frac(a.q)+(frac(b.q)-frac(a.q))*(t-a.seconds)/(b.seconds-a.seconds);return(q-frac(part.base_q))/(frac(part.end_q)-frac(part.base_q))*960;}return 960;}
function update(){if(!part)return;const line=$('#roll .cursor');if(line){const x=52+xAt(active.currentTime)/960*($('#roll').clientWidth-64);line.setAttribute('x1',x);line.setAttribute('x2',x);}for(const n of drawn)n.el.classList.toggle('active',!active.paused&&active.currentTime>=n.start&&active.currentTime<n.end);}
function draw(){
 const svg=$('#roll');svg.replaceChildren();drawn=[];if(!part.notes.length){$('#range').textContent='No pitched notes in this part.';return;}
 const low=Math.min(...part.notes.map(n=>n.pitch)),high=Math.max(...part.notes.map(n=>n.pitch)),height=340,width=svg.clientWidth||960,plotWidth=width-64;
 const step=Math.min(18,(height-32)/Math.max(12,high-low+1)),top=(height-(high-low+1)*step)/2,noteHeight=Math.min(12,step*.75),y=p=>top+(high-p)*step;
 svg.setAttribute('viewBox',`0 0 ${width} ${height}`);$('#range').textContent=`${mode==='before'?'Before':'After'} · ${part.notes.length} written notes · ${pitch(low)}–${pitch(high)} · selected track, full pitch range.`;
 const ns='http://www.w3.org/2000/svg',node=(tag,attrs)=>{const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);svg.append(n);return n;};
 const base=frac(part.base_q),length=frac(part.end_q)-base;
 const left=52+Math.max(0,(frac(detail.start_q)-base)/length*plotWidth),right=52+Math.min(plotWidth,(frac(detail.end_q)-base)/length*plotWidth);
 if(right>left)node('rect',{x:left,y:0,width:right-left,height,fill:'#493e32',opacity:.55});
 for(let p=low;p<=high;p++)node('line',{x1:52,x2:width-12,y1:y(p)+noteHeight/2,y2:y(p)+noteHeight/2,stroke:'#294454'});
 for(const p of new Set([low,high])){const label=node('text',{x:8,y:y(p)+noteHeight/2+4,fill:'#d2e2ed','font-size':12});label.textContent=pitch(p);}
 for(const n of part.notes){const q=frac(n.onset_q),end=q+frac(n.duration_q),role=n[mode],x=52+Math.max(0,(q-base)/length*plotWidth),noteWidth=Math.max(1,(Math.min(end,frac(part.end_q))-Math.max(q,base))/length*plotWidth);
  const r=node('rect',{x,y:y(n.pitch),width:noteWidth,height:noteHeight,fill:role==='call'?'#f6c85f':role==='response'?'#65c7f7':'#748998',tabindex:0,role:'button','aria-label':`${pitch(n.pitch)}, ${role}, bar ${n.bar}`});r.classList.add('note');
  const inspect=()=>{$('#note-info').textContent=`${pitch(n.pitch)} · bar ${n.bar} · before: ${n.before} · after: ${n.after}${n.tied?' · tied continuation':''} · duration ${n.duration_q} quarter-note beats · ${n.id}`;if(Number.isFinite(active.duration))active.currentTime=Math.max(0,seconds(Math.max(q,base)));update();};r.onclick=inspect;r.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect();}};
  drawn.push({el:r,start:seconds(Math.max(q,base)),end:seconds(Math.min(end,frac(part.end_q)))});
 }
 node('line',{x1:52,x2:52,y1:0,y2:height,class:'cursor'});update();
}
function loadPart(){generation++;for(const a of[$('#focused'),$('#context')]){a.pause();a.removeAttribute('src');a.load();}part=detail.windows[Number($('#window').value)];$('#previous').disabled=Number($('#window').value)===0;$('#next').disabled=Number($('#window').value)===detail.windows.length-1;$('#prepare').disabled=!part.playable;$('#status').textContent=part.playable?'Audio is prepared locally when requested.':'Audio preview unavailable for this playback range (repeat mapping or duration). All notes and the full GP remain available.';draw();}
async function loadCase(id){const token=++generation;const next=await(await fetch(`cases/${id}.json`)).json();if(token!==generation)return;detail=next;
 $('#source').textContent=`${detail.song} · ${detail.track} · bars ${detail.start_bar}–${detail.end_bar}`;
 $('#change').textContent=detail.direction==='lost'?'Counted as pedal before; not counted now in the shaded range.':'Not counted as pedal before; counted now in the shaded range.';
 $('#scope').textContent=`${detail.whole_scope_flip?'The whole source section changed yes/no.':'This range changed within a source section that still has a pedal tag elsewhere.'} Exact changed range: ${detail.start_q}–${detail.end_q} quarter-note beats. One bar of surrounding context is included where available.`;
 $('#quality').textContent=detail.roundtrip_pass?'Source conversion passed the existing detailed roundtrip checks.':'Source conversion has an existing fidelity flag; interpret the preview alongside the source GP.';
 $('#gp').href=`scores/${detail.song_id}.gp`;$('#window').replaceChildren(...detail.windows.map((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`Part ${i+1} of ${detail.windows.length} · bars ${w.start_bar}–${w.end_bar}`;return o;}));history.replaceState(null,'','?case='+encodeURIComponent(id));loadPart();
}
function filter(preferred){const search=$('#search').value.toLowerCase(),list=catalogue.cases.filter(c=>c.direction===direction&&(!$('#whole').checked||c.whole_scope_flip)&&`${c.song} ${c.track}`.toLowerCase().includes(search)).sort((a,b)=>Number(b.whole_scope_flip)-Number(a.whole_scope_flip)||a.song.localeCompare(b.song)||a.start_bar-b.start_bar);$('#shown').textContent=`${list.length} of ${catalogue.cases.filter(c=>c.direction===direction).length} ${direction==='lost'?'removed':'added'} spans shown.`;$('#passage').replaceChildren(...list.map(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=`${c.song} · ${c.track} · bars ${c.start_bar}–${c.end_bar}${c.whole_scope_flip?' · whole section':' · partial change'}`;return o;}));document.querySelector('section.panel').hidden=!list.length;if(!list.length){generation++;for(const a of[$('#focused'),$('#context')])a.pause();}if(list.length){const id=list.some(c=>c.id===preferred)?preferred:list[0].id;$('#passage').value=id;loadCase(id);}}
for(const d of['lost','gained'])$('#'+d).onclick=()=>{direction=d;for(const b of['lost','gained'])$('#'+b).setAttribute('aria-pressed',String(b===d));filter();};
for(const m of['before','after'])$('#'+m).onclick=()=>{mode=m;for(const b of['before','after'])$('#'+b).setAttribute('aria-pressed',String(b===m));draw();};
$('#search').oninput=()=>filter();$('#whole').onchange=()=>filter();$('#passage').onchange=e=>loadCase(e.target.value);$('#window').onchange=loadPart;
for(const[id,delta]of[['previous',-1],['next',1]])$('#'+id).onclick=()=>{$('#window').value=Number($('#window').value)+delta;loadPart();};
$('#prepare').onclick=async()=>{const id=part.id,token=generation;$('#prepare').disabled=true;$('#status').textContent='Preparing unchanged source audio…';try{const res=await fetch('/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});const data=await res.json();if(!res.ok)throw Error(data.error||'Render failed');if(token!==generation)return;for(const m of['focused','context'])$('#'+m).src=`audio/${id}.${m}.wav`;$('#status').textContent='Ready. Before and after use this same audio.';}catch(e){if(token===generation){$('#status').textContent=e.message;$('#prepare').disabled=false;}}};
for(const a of[$('#focused'),$('#context')]){a.onplay=()=>{for(const other of[$('#focused'),$('#context')])if(other!==a)other.pause();active=a;update();};for(const e of['timeupdate','seeking','pause','ended'])a.addEventListener(e,update);}
function animate(){if(!active.paused)update();requestAnimationFrame(animate);}requestAnimationFrame(animate);
const requested=new URLSearchParams(location.search).get('case'),entry=catalogue.cases.find(c=>c.id===requested);if(entry){direction=entry.direction;for(const d of['lost','gained'])$('#'+d).setAttribute('aria-pressed',String(d===direction));}filter(requested);
new ResizeObserver(()=>{if(part)draw();}).observe($('#roll'));
