const $=id=>document.getElementById(id),root='./composition-passage-review/',a=$('a'),b=$('b');
const qa=new URLSearchParams(location.search).get('qa')==='1';
let manifest,reviews={},active=a,epoch=0;
const key=()=>`phrase-passages:${manifest.version}${qa?':qa':''}`;
const id=()=>$('passage').value+':'+$('variant').value;
const fields=['difference','preference','thread','holds','resolution','notes'];
function status(text){$('status').textContent=text;}
function persist(){try{localStorage.setItem(key(),JSON.stringify(reviews));$('saved').textContent=qa?'QA storage · not human feedback':'Saved on this device';}catch{$('saved').textContent='Saving unavailable: export feedback.';}}
function ready(player){return player.readyState?Promise.resolve():new Promise((resolve,reject)=>{
  const done=()=>{clearTimeout(timer);player.removeEventListener('loadedmetadata',ok);player.removeEventListener('error',bad);};
  const ok=()=>{done();resolve();},bad=()=>{done();reject(new Error('Audio unavailable'));};
  const timer=setTimeout(bad,10000);player.addEventListener('loadedmetadata',ok);player.addEventListener('error',bad);
});}
async function play(player,position=active.ended?0:active.currentTime){
  const token=epoch;a.pause();b.pause();await ready(player);if(token!==epoch)return;
  player.currentTime=Math.min(position,Math.max(0,player.duration-.01));active=player;
  try{await player.play();status('Playing '+(player===a?'A · Before':'B · After'));}catch{status('Tap the audio play control to start.');}
}
function load(preserve=false){
  const time=preserve?active.currentTime:0,wasPlaying=!active.paused;epoch++;a.pause();b.pause();
  const passage=manifest.passages.find(p=>p.id===$('passage').value),mode=$('mode').value,variant=$('variant').value;
  a.src=root+`${passage.id}-baseline-${mode}.wav`;b.src=root+`${passage.id}-${variant}-${mode}.wav`;a.load();b.load();
  for(const [player,name] of [[a,'baseline'],[b,variant]]){
    const link=$(player===a?'gpA':'gpB');link.href=root+`${passage.family}-${name}${mode==='solo'?'-solo':''}.gp`;link.download='';
  }
  $('explanation').textContent=variant==='rhythm'?'B adds pickups, gaps, unequal attack lengths and held answers, using pitches from the existing generated lead.':'B adds those rhythm changes plus a shared contour, inversion/contraction across sections, a monophonic lead and targeted held answers. This changes several dimensions together.';
  for(const field of fields)$(field).value=reviews[id()]?.[field]||'';
  $('saved').textContent=reviews[id()]?'Feedback restored':qa?'QA storage · not human feedback':'Not reviewed';status('');
  if(preserve){const token=epoch;Promise.all([ready(a),ready(b)]).then(()=>{if(token!==epoch)return;a.currentTime=time;b.currentTime=time;if(wasPlaying)play(active,time).catch(e=>status(e.message));}).catch(e=>status(e.message));}
}
fetch(root+'cases.json').then(r=>{if(!r.ok)throw new Error('Review unavailable');return r.json();}).then(data=>{
  manifest=data;try{reviews=JSON.parse(localStorage.getItem(key())||'{}');}catch{}
  for(const p of data.passages)$('passage').add(new Option(p.title,p.id));
  for(const field of fields)$(field).oninput=()=>{reviews[id()]={...reviews[id()],...Object.fromEntries(fields.map(f=>[f,$(f).value])),updatedAt:new Date().toISOString(),lastMode:$('mode').value};persist();};
  $('passage').onchange=()=>load();$('variant').onchange=()=>load();$('mode').onchange=()=>load(true);
  $('playA').onclick=()=>play(a).catch(e=>status(e.message));$('playB').onclick=()=>play(b).catch(e=>status(e.message));
  $('switch').onclick=()=>play(active===a?b:a).catch(e=>status(e.message));
  $('stop').onclick=()=>{a.pause();b.pause();a.currentTime=0;b.currentTime=0;status('Stopped');};
  $('loop').onchange=()=>{a.loop=b.loop=$('loop').checked;};
  for(const player of [a,b]){player.addEventListener('play',()=>{(player===a?b:a).pause();active=player;});player.addEventListener('error',()=>status('Audio unavailable; refresh and try again.'));}
  $('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({format:'phrase-passages-v2',ratingLabels:{thread:'Idea development',holds:'Meaningful pauses/holds',resolution:'Meaningful ending',ending:'Legacy combined breathing/endings rating'},version:manifest.version,testRun:qa,reviews},null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='phrase-passage-feedback.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  load();
}).catch(e=>status(e.message));
