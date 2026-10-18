const key=document.querySelector('meta[name="study-key"]').content;
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
 const selected=new Set((previous.selected_notes||[]).map(n=>typeof n==='string'?n:n.occurrence));
 function refresh(){for(const n of notes){const yes=selected.has(n.dataset.note);n.classList.toggle('selected',yes);n.setAttribute('aria-pressed',String(yes));}
  c.querySelector('.selection-summary').textContent=selected.size?`${selected.size} anchor note${selected.size===1?'':'s'} marked by you.`:'No notes marked by you.';
 }
 function persist(){saved[c.dataset.id]={...previous,answer:s.value,notes:t.value,selected_notes:notes.filter(n=>selected.has(n.dataset.note)).map(n=>({occurrence:n.dataset.note,pitch:Number(n.dataset.pitch),bar:Number(n.dataset.bar)}))};localStorage.setItem(key,JSON.stringify(saved));refresh();}
 for(const n of notes){const toggle=()=>{selected.has(n.dataset.note)?selected.delete(n.dataset.note):selected.add(n.dataset.note);persist();};n.addEventListener('click',toggle);n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle();}});}
 c.querySelector('.clear-notes').onclick=()=>{selected.clear();persist();};s.onchange=persist;t.oninput=persist;refresh();
 let active=c.querySelector('audio');
 function update(){const time=active.currentTime,x=positionAt(time,map);line.setAttribute('x1',x);line.setAttribute('x2',x);for(const n of notes)n.classList.toggle('sounding',!active.paused&&time>=Number(n.dataset.start)&&time<Number(n.dataset.end));}
 for(const audio of c.querySelectorAll('audio')){
  audio.addEventListener('play',()=>{for(const other of document.querySelectorAll('audio'))if(other!==audio)other.pause();active=audio;update();});
  for(const event of ['timeupdate','seeking','seeked','pause','ended'])audio.addEventListener(event,()=>{if(audio===active)update();});
 }
 function animate(){if(!active.paused)update();requestAnimationFrame(animate);}requestAnimationFrame(animate);
}
document.querySelector('#export').onclick=()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify({study:key,schema:'source-pattern-feedback-v2',judgments:saved},null,2)],{type:'application/json'}));a.href=url;a.download='source-pattern-feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
