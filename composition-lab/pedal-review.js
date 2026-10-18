const qa=new URLSearchParams(location.search).has('qa');
const key=document.querySelector('meta[name="study-key"]').content+(qa?'-qa':'');
let saved={};try{const value=JSON.parse(localStorage.getItem(key)||'{}');if(value&&typeof value==='object'&&!Array.isArray(value))saved=value;}catch{}
const cards=[...document.querySelectorAll('article')];
function positionAt(time,map){
 if(time<=map[0].seconds)return map[0].x;
 for(let i=1;i<map.length;i++)if(time<=map[i].seconds){const a=map[i-1],b=map[i];return a.x+(b.x-a.x)*(time-a.seconds)/(b.seconds-a.seconds);}
 return map.at(-1).x;
}
for(const c of cards){
 const s=c.querySelector('select'),t=c.querySelector('textarea'),notes=[...c.querySelectorAll('.source-note')],svg=c.querySelector('svg'),line=c.querySelector('.playhead'),map=JSON.parse(svg.dataset.timeMap);
 const previous=saved[c.dataset.id]||{};s.value=previous.answer||'';t.value=previous.notes||'';
 const coverage=c.querySelector('.marking-coverage'),identity=c.querySelector('.anchor-identity'),extent=c.querySelector('.anchor-extent'),reveal=c.querySelector('.reveal');
 let revealed=previous.revealed_at||null,blindSelection=previous.pre_reveal_selection||null,blindJudgment=previous.pre_reveal_judgment||null;
 for(const [el,field] of [[coverage,'marking_coverage'],[identity,'anchor_identity'],[extent,'anchor_extent']])if(el)el.value=previous[field]||'';
 if(reveal&&revealed)c.classList.add('revealed');
 const selected=new Set((previous.selected_notes||[]).map(n=>typeof n==='string'?n:n.occurrence));
 function refresh(){for(const n of notes){const yes=selected.has(n.dataset.note);n.classList.toggle('selected',yes);n.setAttribute('aria-pressed',String(yes));}
  c.querySelector('.selection-summary').textContent=selected.size?`${selected.size} anchor note${selected.size===1?'':'s'} marked by you.`:'No notes marked by you.';
 }
 function selection(){return notes.filter(n=>selected.has(n.dataset.note)).map(n=>({occurrence:n.dataset.note,pitch:Number(n.dataset.pitch),bar:Number(n.dataset.bar)}));}
 function persist(){saved[c.dataset.id]={...previous,answer:s.value,notes:t.value,selected_notes:selection(),...(coverage?{marking_coverage:coverage.value,anchor_identity:identity.value,anchor_extent:extent.value,revealed_at:revealed,pre_reveal_selection:blindSelection,pre_reveal_judgment:blindJudgment,case_cohort:c.dataset.cohort}: {})};localStorage.setItem(key,JSON.stringify(saved));refresh();}
 for(const n of notes){const toggle=()=>{selected.has(n.dataset.note)?selected.delete(n.dataset.note):selected.add(n.dataset.note);persist();};n.addEventListener('click',toggle);n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle();}});}
 c.querySelector('.clear-notes').onclick=()=>{selected.clear();persist();};s.onchange=persist;t.oninput=persist;refresh();
 for(const el of [coverage,identity,extent])if(el)el.onchange=persist;
 if(reveal)reveal.onclick=()=>{if(!revealed){revealed=new Date().toISOString();blindSelection=selection();blindJudgment={answer:s.value,marking_coverage:coverage.value,notes:t.value,selected_notes:blindSelection};}c.classList.add('revealed');persist();};
 let active=c.querySelector('audio');
 function update(){const time=active.currentTime,x=positionAt(time,map);line.setAttribute('x1',x);line.setAttribute('x2',x);for(const n of notes)n.classList.toggle('sounding',!active.paused&&time>=Number(n.dataset.start)&&time<Number(n.dataset.end));}
 for(const audio of c.querySelectorAll('audio')){
  audio.addEventListener('play',()=>{for(const other of document.querySelectorAll('audio'))if(other!==audio)other.pause();active=audio;update();});
  for(const event of ['timeupdate','seeking','seeked','pause','ended'])audio.addEventListener(event,()=>{if(audio===active)update();});
 }
 function animate(){if(!active.paused)update();requestAnimationFrame(animate);}requestAnimationFrame(animate);
}
document.querySelector('#export').onclick=()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify({study:key,qa,schema:document.querySelector('.reveal')?'source-pattern-feedback-v3':'source-pattern-feedback-v2',judgments:saved},null,2)],{type:'application/json'}));a.href=url;a.download='source-pattern-feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
