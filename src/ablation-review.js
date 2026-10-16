import {METRICS,storageKey,reviewed,recordReview,revealReview,mergeFeedback,csvFeedback} from './ablation-review-state.mjs';
import {preparePrivateMedia} from './private-review-bundle.mjs';

const $=id=>document.getElementById(id), ROOT=new URLSearchParams(location.search).get('study')==='phrases'?'./composition-phrase-review/':'./composition-ablation-review/';
const A=$('audioA'),B=$('audioB');
const QA=new URLSearchParams(location.search).get('qa')==='1';
const store=()=>storageKey(manifest.version)+(QA?':qa':'');
let manifest,state={reviews:{},favorites:{}},family='cloud',selected=null,roll=null,rollRequest=0,hits=[],keys=[],flash=null,context=null;
let privateMedia=null;
const asset=name=>privateMedia?privateMedia.asset(name):ROOT+name;
const audioAsset=name=>privateMedia?privateMedia.audio(name):Promise.resolve(ROOT+name);
const metrics=()=>manifest?.ratingMetrics||METRICS;
const rollPlayer=()=>$('rollPlayer').value==='B'?B:A;
const current=()=>manifest?.cases.find(c=>c.id===selected);
const familyCases=()=>manifest.cases.filter(c=>c.family===family);
const answer=()=>state.reviews[selected]||{};
const status=message=>$('status').textContent=message;
function persist(){
  try{localStorage.setItem(store(),JSON.stringify({...state,selected,family}));$('storageStatus').textContent=QA?'QA test storage · not human feedback':'Saved on this device';}
  catch{$('storageStatus').textContent='Browser saving is unavailable. Export feedback to keep it.';}
}
function progress(){
  $('progress').textContent=`${manifest.cases.filter(c=>reviewed(state.reviews[c.id])).length} of ${manifest.cases.length} reviewed`;
  $('saved').textContent=reviewed(answer())?'Judgment saved':'Not reviewed';
  $('reveal').disabled=!reviewed(answer());
  for(const button of $('playlist').children){const c=manifest.cases.find(c=>c.id===button.dataset.id);button.lastChild.textContent=reviewed(state.reviews[c.id])?'✓':'';}
}
function save(patch){state.reviews[selected]=recordReview(answer(),patch);persist();progress();}
function ratingFields(){
  for(const [key,label] of metrics()){
    const field=document.createElement('label');field.textContent=label;const select=document.createElement('select');select.id='rating-'+key;select.setAttribute('aria-label',label);
    const options=[['','Not rated'],['1','1 · Very weak'],['2','2 · Weak'],['3','3 · Mixed'],['4','4 · Good'],['5','5 · Strong'],['uncertain','Cannot judge']];
    if(key!=='coherence') options.push(['absent','Not present / not applicable']);
    for(const [value,text] of options)select.add(new Option(text,value));
    select.onchange=()=>save({[key]:select.value});field.append(select);$('ratings').append(field);
  }
}
function renderMethod(){
  const revealed=Boolean(answer().revealedAt);$('method').hidden=!revealed;$('method').replaceChildren();
  $('blindBadge').textContent=revealed?'Method revealed':'Method hidden';$('reveal').textContent=revealed?'Method revealed':'Reveal method';
  if(!revealed)return;
  const c=current(),title=document.createElement('strong');title.textContent=c.method;$('method').append(title);
  const text=document.createElement('p');text.textContent=c.tracks.map(t=>`${t.strings}-string ${t.name}`).join(' · ');$('method').append(text);
  const link=document.createElement('a');link.href=asset(c.gp);link.download=c.gp;link.textContent='Download Guitar Pro score';$('method').append(link);
}
function playlist(){
  $('playlist').replaceChildren();
  for(const c of familyCases()){
    const button=document.createElement('button');button.dataset.id=c.id;button.className=c.id===selected?'active':'';button.setAttribute('aria-current',c.id===selected?'true':'false');
    const label=document.createElement('span');label.textContent=c.label;const done=document.createElement('span');done.className='done';button.append(label,done);button.onclick=()=>select(c.id);$('playlist').append(button);
  }
}
async function select(id,autoplay=false){
  A.pause();B.pause();selected=id;const c=current();family=c.family;roll=null;hits=[];keys=[];persist();
  $('listenTitle').textContent=c.label;$('studyTitle').textContent=c.familyTitle;
  document.querySelectorAll('[data-family]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.family===family)));
  $('playA').disabled=true;A.removeAttribute('src');A.load();
  const audioUrl=await audioAsset(c.audio);if(selected!==id)return;A.src=audioUrl;A.load();$('playA').disabled=false;
  $('compare').replaceChildren();$('favorite').replaceChildren(new Option('Not chosen',''));
  for(const other of familyCases()){
    if(other.id!==id)$('compare').add(new Option(other.label,other.id));
    $('favorite').add(new Option(other.label,other.id));
  }
  $('favorite').value=state.favorites[family]||'';setComparison();
  for(const [key] of metrics())$('rating-'+key).value=answer()[key]||'';
  $('notes').value=answer().notes||'';const index=familyCases().findIndex(c=>c.id===selected);
  $('prev').disabled=index===0;$('saveNext').textContent=index===familyCases().length-1?'Save · next study →':'Save and play next →';
  $('viewStart').value=0;$('viewStart').max=Math.max(0,c.seconds-8);playlist();progress();renderMethod();status('');draw();
  loadRoll();
  if(autoplay)await play(A);
}
function loadRoll(){
  const player=rollPlayer(),c=player===A?current():manifest.cases.find(c=>c.id===$('compare').value);
  const request=++rollRequest;roll=null;hits=[];keys=[];flash=null;
  $('part').replaceChildren(new Option('All parts','all'));
  $('rollTitle').textContent=(player===A?'A':'B')+' / '+c.label;
  $('roll').setAttribute('aria-label','Interactive piano roll for '+$('rollTitle').textContent);
  $('viewStart').value=0;$('pitchStatus').textContent='';draw();
  fetch(asset(c.roll)).then(r=>{if(!r.ok)throw new Error('Piano roll unavailable');return r.json();}).then(data=>{
    if(request!==rollRequest)return;roll=data;
    for(const part of [...new Set(roll.notes.map(n=>n.part))].sort((a,b)=>a-b))$('part').add(new Option('Part '+(part+1),String(part)));
    const span=$('zoom').value==='all'?Infinity:Number($('zoom').value);
    if(Number.isFinite(span))$('viewStart').value=Math.floor(player.currentTime/span)*span;
    draw();
  }).catch(e=>{if(request===rollRequest)status(e.message);});
}
function followPlayer(player){
  const value=player===A?'A':'B';
  if($('rollPlayer').value!==value){$('rollPlayer').value=value;loadRoll();}
}
async function setComparison(){B.pause();$('playB').disabled=true;B.removeAttribute('src');B.load();const selection=selected,c=manifest.cases.find(c=>c.id===$('compare').value);if(c){try{const url=await audioAsset(c.audio);if(selected!==selection||$('compare').value!==c.id)return;B.src=url;B.load();$('playB').disabled=false;}catch(e){status(e.message);return;}}applyPlayback();if($('rollPlayer').value==='B')loadRoll();}
function applyPlayback(){for(const player of [A,B]){player.playbackRate=Number($('speed').value);player.loop=$('loop').checked;}}
async function play(player){
  (player===A?B:A).pause();applyPlayback();
  try{await player.play();status(player===A?'Playing A · '+current().label:'Playing B · '+$('compare').selectedOptions[0].textContent);}
  catch{status('Playback did not start. Tap the audio player’s play control to try again.');}
}
async function switchPlayer(){
  const selection=selected,comparison=$('compare').value;
  const from=!B.paused?B:A,to=from===A?B:A;
  const fraction=Number.isFinite(from.duration)&&from.duration?from.currentTime/from.duration:0;
  from.pause();
  if(to.readyState===0)await new Promise((resolve,reject)=>{
    const cleanup=()=>{clearTimeout(timer);to.removeEventListener('loadedmetadata',loaded);to.removeEventListener('error',failed);};
    const loaded=()=>{cleanup();resolve();},failed=()=>{cleanup();reject(new Error('Audio unavailable'));};
    const timer=setTimeout(failed,10000);to.addEventListener('loadedmetadata',loaded,{once:true});to.addEventListener('error',failed,{once:true});
  });
  if(selected!==selection||$('compare').value!==comparison)return;
  if(Number.isFinite(to.duration))to.currentTime=Math.min(fraction*to.duration,Math.max(0,to.duration-.05));
  await play(to);
}
function download(body,name,type){const url=URL.createObjectURL(new Blob([body],{type})),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function payload(){return {format:'composition-ablation-feedback-v1',version:manifest.version,exportedAt:new Date().toISOString(),reviews:state.reviews,favorites:state.favorites,
  testRun:QA,
  cases:manifest.cases.map(c=>({id:c.id,gpSha256:c.gpSha256,audioSha256:c.audioSha256,notesSha256:c.notesSha256}))};}
const noteName=p=>['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'][p%12]+(Math.floor(p/12)-1);
const COLORS=['#91d1e0','#d9b6ed','#9fd4a5','#f0c98c'];
function draw(){
  if(!$('rollDetails').open)return;
  const canvas=$('roll'),ctx=canvas.getContext('2d'),width=Math.max(280,$('rollScroll').clientWidth-2),dpr=window.devicePixelRatio||1;
  const notes=(roll?.notes||[]).filter(n=>$('part').value==='all'||n.part===Number($('part').value));
  const low=notes.length?Math.max(0,Math.min(...notes.map(n=>n.pitch))-1):48,high=notes.length?Math.min(127,Math.max(...notes.map(n=>n.pitch))+1):72;
  const row=17,top=25,left=57,height=(high-low+1)*row+top;
  canvas.width=width*dpr;canvas.height=height*dpr;canvas.style.width=width+'px';canvas.style.height=height+'px';ctx.scale(dpr,dpr);
  const duration=roll?.duration||current()?.seconds||32,span=$('zoom').value==='all'?duration:Number($('zoom').value);
  const start=Math.min(Number($('viewStart').value),Math.max(0,duration-span)),end=start+span;
  $('viewStart').max=Math.max(0,duration-span);$('viewStart').disabled=span>=duration;
  ctx.fillStyle='#0c141e';ctx.fillRect(0,0,width,height);hits=[];keys=[];
  for(let pitch=low;pitch<=high;pitch++){
    const y=top+(high-pitch)*row,black=[1,3,6,8,10].includes(pitch%12);
    ctx.fillStyle=black?'#111d2a':'#192736';ctx.fillRect(left,y,width-left,row-1);
    ctx.fillStyle=flash?.pitch===pitch&&flash?.keyboard?'#92c8eb':black?'#243447':'#c6d4df';ctx.fillRect(0,y,left-4,row-1);
    ctx.fillStyle=black?'#d9e6ef':'#152332';ctx.font='10px system-ui';ctx.fillText(noteName(pitch),5,y+12);
    keys.push({pitch,x:0,y,w:left-4,h:row});
  }
  const x=time=>left+(time-start)/span*(width-left-10);
  ctx.font='10px system-ui';ctx.fillStyle='#a5bbca';
  for(let t=Math.ceil(start);t<=end;t+=Math.max(1,Math.ceil(span/8))){const px=x(t);ctx.fillText(t+'s',px+2,15);ctx.strokeStyle='#2e4053';ctx.beginPath();ctx.moveTo(px,top);ctx.lineTo(px,height);ctx.stroke();}
  const visible=notes.filter(n=>n.end>start&&n.start<end);
  for(const n of visible){
    const nx=x(Math.max(start,n.start)),y=top+(high-n.pitch)*row+5,w=Math.max(3,x(Math.min(end,n.end))-nx);
    ctx.fillStyle=flash?.note===n?'#ebf8ff':COLORS[n.part%COLORS.length];ctx.fillRect(nx,y,w,10);hits.push({note:n,x:nx,y:y-4,w,h:row});
  }
  if($('noteLabels').checked)for(const hit of hits){ctx.font='10px system-ui';ctx.lineWidth=3;ctx.strokeStyle='#0b141e';ctx.strokeText(noteName(hit.note.pitch),hit.x+1,hit.y+7);ctx.fillStyle='#eff6fc';ctx.fillText(noteName(hit.note.pitch),hit.x+1,hit.y+7);}
  const player=rollPlayer();
  if(player.currentTime>=start&&player.currentTime<=end){ctx.strokeStyle='#ffcd81';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x(player.currentTime),top);ctx.lineTo(x(player.currentTime),height);ctx.stroke();}
  canvas._view={start,span,left,width};
}
function audition(pitch,note=null,keyboard=false){
  const Audio=window.AudioContext||window.webkitAudioContext;if(!Audio){status('Note audition is unavailable in this browser.');return;}
  context??=new Audio();context.resume().catch(()=>{});const oscillator=context.createOscillator(),gain=context.createGain(),now=context.currentTime;
  oscillator.frequency.value=440*2**((pitch-69)/12);gain.gain.setValueAtTime(0,now);gain.gain.linearRampToValueAtTime(.12,now+.012);gain.gain.exponentialRampToValueAtTime(.001,now+.55);oscillator.connect(gain);gain.connect(context.destination);oscillator.start(now);oscillator.stop(now+.6);
  $('pitchStatus').textContent=noteName(pitch);flash={pitch,note,keyboard};draw();const token=flash;setTimeout(()=>{if(flash===token){flash=null;draw();}},220);
}
$('roll').addEventListener('click',event=>{
  const rect=$('roll').getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top;
  const hit=hits.find(h=>x>=h.x&&x<=h.x+h.w&&y>=h.y&&y<=h.y+h.h);
  if(hit){audition(hit.note.pitch,hit.note);return;}
  const key=keys.find(k=>x>=k.x&&x<=k.x+k.w&&y>=k.y&&y<=k.y+k.h);if(key){audition(key.pitch,null,true);return;}
  const player=rollPlayer(),view=$('roll')._view;if(view&&x>=view.left&&Number.isFinite(player.duration))player.currentTime=Math.max(0,Math.min(player.duration,view.start+(x-view.left)/(view.width-view.left-10)*view.span));
});
for(const player of [A,B]){
  player.addEventListener('timeupdate',()=>{
    if(player!==rollPlayer()||!$('rollDetails').open)return;
    const span=$('zoom').value==='all'?Infinity:Number($('zoom').value),start=Number($('viewStart').value);
    if(!player.paused&&(player.currentTime<start||player.currentTime>start+span))$('viewStart').value=Math.floor(player.currentTime/span)*span;
    draw();
  });
  player.addEventListener('play',()=>{(player===A?B:A).pause();followPlayer(player);});
  player.addEventListener('error',()=>status('Audio could not be loaded. Refresh the page or try another sketch.'));
}
async function activate(){
  state={reviews:{},favorites:{}};family='cloud';selected=null;
  try{const stored=JSON.parse(localStorage.getItem(store())||'null');if(stored){state={reviews:stored.reviews||{},favorites:stored.favorites||{}};family=stored.family||family;selected=stored.selected;}}catch{}
  if(!manifest.cases.some(c=>c.id===selected))selected=manifest.cases[0].id;
  if(manifest.title){document.querySelector('h1').textContent=manifest.title;document.querySelector('.top p').textContent=manifest.intro;document.querySelector('aside .hint').textContent=manifest.asideIntro||'Each study contains three pitch-only experiments, the unchanged previous roles baseline, and V2 in hidden order.';document.querySelector('#judgmentTitle').parentElement.nextElementSibling.textContent=manifest.guidance;}
  $('ratings').replaceChildren();ratingFields();
  document.querySelectorAll('[data-family]').forEach(b=>b.onclick=()=>select(manifest.cases.find(c=>c.family===b.dataset.family).id));
  $('notes').oninput=()=>save({notes:$('notes').value});$('favorite').onchange=()=>{state.favorites[family]=$('favorite').value;persist();};
  $('playA').onclick=()=>play(A);$('playB').onclick=()=>play(B);$('switch').onclick=()=>switchPlayer().catch(()=>status('Comparison audio is not ready. Tap Play B.'));
  $('stop').onclick=()=>{A.pause();B.pause();A.currentTime=0;B.currentTime=0;status('Stopped');draw();};
  $('speed').onchange=applyPlayback;$('loop').onchange=applyPlayback;$('compare').onchange=setComparison;
  $('prev').onclick=()=>select(familyCases()[familyCases().findIndex(c=>c.id===selected)-1].id);
  $('saveNext').onclick=()=>{
    if(!reviewed(answer())){status('Choose an overall judgment, including Cannot judge, before saving and moving on.');$('rating-coherence').focus();return;}
    persist();const cases=familyCases(),index=cases.findIndex(c=>c.id===selected);
    if(index<cases.length-1)select(cases[index+1].id,true);
    else select(manifest.cases.find(c=>c.family!==(family)).id,true);
  };
  $('reveal').onclick=()=>{try{state.reviews[selected]=revealReview(answer());persist();renderMethod();}catch(e){status(e.message);}};
  $('export').onclick=()=>download(JSON.stringify(payload(),null,2),'composition-listening-feedback.json','application/json');
  $('exportCsv').onclick=()=>download(csvFeedback(manifest,state.reviews,state.favorites),'composition-listening-feedback.csv','text/csv');
  $('import').onchange=async event=>{
    const file=event.target.files?.[0];if(!file)return;
    try{const imported=JSON.parse(await file.text());if(imported.testRun&&!QA)throw new Error('QA test data cannot become human feedback.');state.reviews=mergeFeedback(state.reviews,imported,manifest);
      for(const [key,id] of Object.entries(imported.favorites||{}))if(!state.favorites[key]&&manifest.cases.some(c=>c.family===key&&c.id===id))state.favorites[key]=id;
      persist();await select(selected);status('Feedback restored. Newer local judgments were kept.');}
    catch(e){status('Restore failed: '+e.message);}event.target.value='';
  };
  $('rollPlayer').onchange=loadRoll;
  $('rollDetails').ontoggle=draw;for(const id of ['zoom','part','noteLabels','viewStart'])$(id).oninput=draw;
  window.onresize=draw;await select(selected);
}
async function boot(){
  if(new URLSearchParams(location.search).get('study')==='final'){
    document.querySelector('h1').textContent='Consolidated composition review';
    document.querySelector('.top p').textContent='Load the private generated review bundle. Music stays on this device; nothing is uploaded.';
    $('progress').textContent='Waiting for private review bundle';
    const label=document.createElement('label');label.textContent='Load private review bundle ';const input=document.createElement('input');input.type='file';input.accept='.json,application/json';input.id='privateBundle';label.append(input);document.querySelector('.toolbar').prepend(label);
    const load=async text=>{A.pause();B.pause();
      try{status('Checking local bundle and preparing previews…');const next=await preparePrivateMedia(JSON.parse(text));privateMedia?.dispose();privateMedia=next;manifest=next.manifest;await activate();}
      catch(e){status('Bundle could not be loaded: '+e.message);}};
    input.onchange=async()=>{const file=input.files?.[0];if(file)await load(await file.text());};
    const fallback=document.createElement('details'),summary=document.createElement('summary');summary.textContent='File picker unavailable? Paste review JSON';fallback.append(summary);
    const pasted=document.createElement('textarea');pasted.id='pastedBundle';pasted.setAttribute('aria-label','Private review JSON');pasted.placeholder='Paste the contents of your generated review bundle';fallback.append(pasted);
    const loadButton=document.createElement('button');loadButton.textContent='Load pasted bundle';loadButton.onclick=async()=>{await load(pasted.value);pasted.value='';fallback.open=false;};fallback.append(loadButton);document.querySelector('.toolbar').after(fallback);
    return;
  }
  const response=await fetch(ROOT+'cases.json');if(!response.ok)throw new Error('Review set could not be loaded.');manifest=await response.json();await activate();
}
boot().catch(e=>{status(e.message);$('progress').textContent='Review unavailable';});
