// Read-only playback comparison. The payload contains measured native MIDI attacks.
export function noteKey(n){return JSON.stringify([n.part,n.voice,Math.round(n.start*44100),Math.round(n.end*44100),n.pitch,n.velocity,n.fret,n.string,n.dead,n.ghost]);}
export function difference(current,baseline){
 const available=new Map();for(const n of baseline){const k=noteKey(n);if(!available.has(k))available.set(k,[]);available.get(k).push(n);}
 const shown=current.map(n=>{const matches=available.get(noteKey(n));return {...n,change:matches?.length?(matches.pop(),'same'):'new'};});
 const removed=[...available.values()].flat().map(n=>({...n,change:'old'}));return {shown,removed};
}
export function pitchName(n){return ['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'][((n%12)+12)%12]+'_'+(Math.floor(n/12)-1);}
export function partRange(versions,part){const pitches=versions.flatMap(v=>v.notes.filter(n=>n.part===part).map(n=>n.pitch));return {low:Math.min(...pitches)-1,high:Math.max(...pitches)+1};}
export function pitchedLaneGeometry(range){
 const rowCount=range.high-range.low+1,rowSize=Math.min(9,(280-34)/rowCount);
 return {rowCount,rowSize,height:Math.max(90,34+rowCount*rowSize),noteHeight:7*rowSize/9,outlineWidth:1.7*rowSize/9,
  mapY:p=>34+(range.high-p)*rowSize+rowSize/2};
}
export function barAt(data,time){return Math.min(data.bars[1],[...data.bar_times].reverse().find(b=>b.time<=time+1/44100)?.bar??data.bars[0]);}
export function formatTime(seconds){return `${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;}
export function comparisonView(current,baseline,onlyChanged=false){
 const base=baseline&&baseline.id!==current.id?baseline:null;
 const result=base?difference(current.notes,base.notes):{shown:current.notes.map(n=>({...n,change:'same'})),removed:[]};
 const changes=[...result.shown.filter(n=>n.change==='new'),...result.removed];
 const canFilter=Boolean(base&&changes.length);
 return {...result,base,changes,canFilter,filterActive:onlyChanged&&canFilter,changedParts:new Set(changes.map(n=>n.part))};
}
export function changeScrollLeft(changes,left,visibleWidth,pxPerSecond){
 if(!changes.length||changes.some(n=>n.end*pxPerSecond>left&&n.start*pxPerSecond<left+visibleWidth))return left;
 return Math.max(0,Math.min(...changes.map(n=>n.start))*pxPerSecond-20);
}
export function playbackSwitchState(){
 let serial=0,pending=null;
 return {
  begin(position,playing){pending={...(pending||{position,playing}),token:++serial};return serial;},
  seek(position){if(!pending)return false;pending.position=position;return true;},
  position(actual){return pending?.position??actual;},
  isCurrent(token){return token===serial;},
  complete(token,duration){
   if(!pending||token!==serial||!Number.isFinite(duration)||duration<0)return null;
   const target={position:Math.min(pending.position,duration),playing:pending.playing};pending=null;return target;
  }
 };
}

if(typeof document!=='undefined')boot().catch(error=>{const e=document.querySelector('#error');e.hidden=false;e.className='error';e.textContent='The comparison could not load: '+error.message;console.error(error);});
async function boot(){
 const response=await fetch('comparison.json');if(!response.ok)throw Error('Missing comparison data');const data=await response.json();
 const $=s=>document.querySelector(s),audio=$('#audio'),viewport=$('#viewport'),roll=$('#roll'),axes=$('#axes'),compare=$('#compare');
 const byId=new Map(data.versions.map(v=>[v.id,v])),switchState=playbackSwitchState();let selected=data.default_version||data.original_version,drawn=[],head,lastActive='';
 if(!byId.has(data.original_version)||!byId.has(selected)||!data.questions?.length)throw Error('Original audio and listening questions are required.');
 const width=Math.max(620,(data.bars[1]-data.bars[0]+1)*155),pxPerSecond=width/data.seconds,svgNS='http://www.w3.org/2000/svg';
 const percussionNames={35:'Bass drum',36:'Kick',37:'Side stick',38:'Snare',40:'Snare',42:'Closed hat',44:'Pedal hat',46:'Open hat',41:'Low tom',43:'Low tom',45:'Mid tom',47:'Mid tom',48:'High tom',49:'Crash',51:'Ride',52:'China',55:'Splash',57:'Crash',59:'Ride'};
 const element=(name,attributes,text)=>{const e=document.createElementNS(svgNS,name);for(const[k,v]of Object.entries(attributes))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;};
 document.title=data.title+' · Compare';$('#title').textContent=data.title;$('#artist').textContent=data.artist+' · SONGSTERR SCORE PLAYBACK';
 $('#scope').textContent=`Bars ${data.bars[0]}–${data.bars[1]}${data.context_label?' · '+data.context_label:''}`;
 $('#rollHint').textContent=`Scroll sideways to see all ${data.bars[1]-data.bars[0]+1} bars · tap a note for details`;
 $('#settings').textContent=data.playback_note;
 $('.versions').style.gridTemplateColumns=`repeat(${Math.min(3,data.versions.length)},1fr)`;
 for(const [index,v] of data.versions.entries()){
  const button=document.createElement('button');button.dataset.version=v.id;button.setAttribute('aria-pressed',String(v.id===selected));
  const number=document.createElement('span');number.className='number';number.textContent=index+1;const label=document.createElement('span');label.textContent=v.label;
  const subtitle=document.createElement('small');subtitle.textContent=v.subtitle||'';label.append(subtitle);button.append(number,label);$('.versions').append(button);
  const option=document.createElement('option');option.value=v.id;option.textContent=v.label;compare.append(option);
  const link=document.createElement('a');link.href=v.audio;link.download='';link.textContent='Download '+v.label;$('.downloads').append(link);
 }
 const none=document.createElement('option');none.value='none';none.textContent='No overlay';compare.append(none);
 for(const question of data.questions){const li=document.createElement('li');li.textContent=question;$('#questions').append(li);}
 const sections=data.sections;
 for(const section of sections){const b=document.createElement('button');b.dataset.bar=section.first;b.addEventListener('click',()=>{const position=seekTo(timeOf(section.first));viewport.scrollLeft=Math.max(0,position*pxPerSecond-30);tick();});$('#timeline').append(b);}
 function timeOf(bar){return data.bar_times.find(b=>b.bar===bar).time;}
 function seekTo(position){const target=Math.min(data.seconds,Math.max(0,position));if(!switchState.seek(target))audio.currentTime=target;return target;}
 function render(revealChanges=false){
  const current=byId.get(selected),result=comparisonView(current,byId.get(compare.value),$('#changedOnly').checked),base=result.base;
  if(!base)compare.value='none';for(const option of compare.options)option.disabled=option.value===selected;
  $('#changedOnly').disabled=!result.canFilter;$('#changedOnly').checked=result.filterActive;
  $('#changedOnly').title=base?(result.canFilter?'Keep parts that contain changed notes':'No note differences in this comparison'):'Select a comparison first';
  $('#rollHint').textContent=result.filterActive?`Changed notes start in bar ${barAt(data,Math.min(...result.changes.map(n=>n.start)))} · tap a note for details`:`Scroll sideways to see all ${data.bars[1]-data.bars[0]+1} bars · tap a note for details`;
  const tracks=data.tracks.filter(t=>!result.filterActive||result.changedParts.has(t.id));axes.replaceChildren();roll.replaceChildren();roll.style.width=width+'px';drawn=[];
  const top=document.createElement('div');top.style.height='28px';top.className='axis';top.textContent='Bar';top.style.padding='4px 8px';top.style.fontSize='12px';axes.append(top);
  const ruler=element('svg',{width,height:28,role:'img','aria-label':'Bar numbers'});
  for(const b of data.bar_times.filter(b=>b.bar>=data.bars[0]&&b.bar<=data.bars[1])){const x=Math.max(0,b.time)*pxPerSecond,w=(timeOf(b.bar+1)-b.time)*pxPerSecond;ruler.append(element('rect',{x,y:0,width:w,height:28,fill:data.focus_bars&&b.bar>=data.focus_bars[0]&&b.bar<=data.focus_bars[1]?'#293c3e':'#192a32'}));ruler.append(element('text',{x:x+6,y:19,fill:'#c4d3d9','font-size':12},b.bar));}
  roll.append(ruler);
  for(const track of tracks){
   const range=partRange(data.versions,track.id),pitchValues=track.percussion?[...new Set(data.versions.flatMap(v=>v.notes.filter(n=>n.part===track.id).map(n=>n.pitch)))].sort((a,b)=>b-a):null;
   const pitched=track.percussion?null:pitchedLaneGeometry(range);
   const rowSize=track.percussion?19:pitched.rowSize,rowCount=track.percussion?pitchValues.length:pitched.rowCount;
   const height=track.percussion?Math.max(90,34+rowCount*rowSize):pitched.height,mapY=track.percussion?p=>34+pitchValues.indexOf(p)*rowSize+rowSize/2:pitched.mapY;
   const axis=document.createElement('div');axis.className='axis';axis.style.height=height+'px';const title=document.createElement('div');title.className='axis-title';title.textContent=track.name;axis.append(title);
   const labels=track.percussion?pitchValues:Array.from({length:rowCount},(_,i)=>range.high-i).filter(p=>p%12===0||p===range.high-1||p===range.low+1);
   // End labels stay far enough apart to remain readable when a part has one pitch.
   let lastLabel=-100;for(const p of labels){const y=mapY(p);if(y-lastLabel<13)continue;lastLabel=y;const label=document.createElement('span');label.className='pitch-label';label.style.top=y+'px';label.textContent=track.percussion?(percussionNames[p]||'Drum '+p):pitchName(p);axis.append(label);}axes.append(axis);
   const svg=element('svg',{width,height,role:'img','aria-label':track.name+' piano roll','data-part':track.id});svg.append(element('rect',{x:0,y:0,width,height,fill:'#15252e'}));
   for(let row=0;row<rowCount;row++){const p=track.percussion?pitchValues[row]:range.high-row,y=mapY(p)-rowSize/2;svg.append(element('rect',{x:0,y,width,height:rowSize,fill:!track.percussion&&[1,3,6,8,10].includes(p%12)?'#13212a':'#192c36'}));}
   for(const b of data.bar_times.filter(b=>b.bar>=data.bars[0]&&b.bar<=data.bars[1])){const x=Math.max(0,b.time)*pxPerSecond;svg.append(element('line',{x1:x,x2:x,y1:28,y2:height,stroke:sections.some(s=>s.first===b.bar)?'#809174':'#3b535e','stroke-width':1}));for(const beatTime of b.beat_times||[])svg.append(element('line',{x1:beatTime*pxPerSecond,x2:beatTime*pxPerSecond,y1:28,y2:height,stroke:'#253d48','stroke-width':0.6}));}
   const notes=[...result.removed,...result.shown].filter(n=>n.part===track.id);
   for(const n of notes){const x=n.start*pxPerSecond,w=Math.max(2,(n.end-n.start)*pxPerSecond-0.7),h=track.percussion?12:pitched.noteHeight,outline=track.percussion?1.7:pitched.outlineWidth;
    const rect=element('rect',{x,y:mapY(n.pitch)-h/2,width:w,height:h,rx:1,fill:n.change==='new'?'#5ce4ba':n.change==='old'?'none':'#748c99',stroke:n.change==='old'?'#ff9bb2':'none','stroke-width':n.change==='old'?outline:0,'stroke-dasharray':n.change==='old'?'4 2':'none',class:'note','data-change':n.change,'data-start':n.start,'data-end':n.end});
    const name=track.percussion?(percussionNames[n.pitch]||'Drum '+n.pitch):pitchName(n.pitch);const wording=`${track.name} · bar ${n.bar} · ${name} · ${n.change==='old'?'removed / replaced':n.change==='new'?'new / changed':'unchanged'}`;rect.append(element('title',{},wording));rect.addEventListener('click',()=>{$('#details').textContent=wording;});svg.append(rect);drawn.push({element:rect,n});}
   svg.addEventListener('click',event=>{if(event.target.classList.contains('note'))return;const box=svg.getBoundingClientRect();seekTo((event.clientX-box.left)/pxPerSecond);tick();});roll.append(svg);
  }
  head=document.createElement('div');head.className='playhead';head.setAttribute('aria-hidden','true');roll.append(head);
  $('#description').textContent=current.description;$('#coverage').textContent=`${tracks.length} of ${data.tracks.length} playing parts shown. ${data.silent_tracks.length} other parts are silent here. ${base?`Colors compare with “${base.label}”.`:'No comparison overlay.'} Drums appear on named rows.`;
  for(const b of document.querySelectorAll('#timeline button')){const first=Number(b.dataset.bar),section=sections.find(s=>s.first===first);const strong=document.createElement('strong');strong.textContent=`${first}–${section.last}`;const small=document.createElement('small');small.textContent=Math.round(timeOf(first))+'s';b.replaceChildren(strong,document.createTextNode(current.section_labels?.[first]||section.label),small);}
  if(!tracks.length){const empty=document.createElement('p');empty.className='load';empty.textContent='No changed parts in this comparison.';roll.append(empty);}
  for(const button of document.querySelectorAll('[data-version]'))button.setAttribute('aria-pressed',String(button.dataset.version===selected));lastActive='';tick();
  if(revealChanges&&result.filterActive){
   viewport.scrollLeft=changeScrollLeft(result.changes,viewport.scrollLeft,viewport.clientWidth,pxPerSecond);
   const controls=$('#changedOnly').closest('.controls');
   controls.style.scrollMarginTop=($('.player').getBoundingClientRect().height+12)+'px';
   controls.scrollIntoView({block:'start',inline:'nearest'});
  }
 }
 async function choose(id){
  if(id===selected&&audio.getAttribute('src'))return;const token=switchState.begin(audio.currentTime||0,!audio.paused);audio.pause();selected=id;
  compare.value=byId.get(id).compare_to||'none';if(id===data.original_version)$('#changedOnly').checked=false;render($('#changedOnly').checked);
  audio.src=byId.get(id).audio;audio.load();
  try{await new Promise((resolve,reject)=>{
   const cleanup=()=>{audio.removeEventListener('loadedmetadata',loaded);audio.removeEventListener('error',failed);};
   const loaded=()=>{if(audio.readyState<1||!Number.isFinite(audio.duration))return;cleanup();resolve();};
   const failed=()=>{cleanup();reject(Error('Audio failed to load'));};
   audio.addEventListener('loadedmetadata',loaded);audio.addEventListener('error',failed);
  });}catch(error){if(!switchState.isCurrent(token))return;throw error;}
  const target=switchState.complete(token,audio.duration);if(!target)return;
  audio.currentTime=target.position;audio.playbackRate=Number($('#speed').value);tick();
  if(target.playing)try{await audio.play();}catch(error){if(switchState.isCurrent(token))throw error;}
 }
 for(const button of document.querySelectorAll('[data-version]'))button.addEventListener('click',()=>choose(button.dataset.version).catch(console.error));
 compare.addEventListener('change',()=>{if(compare.value==='none')$('#changedOnly').checked=false;render($('#changedOnly').checked);});$('#changedOnly').addEventListener('change',()=>render($('#changedOnly').checked));$('#speed').addEventListener('change',()=>{audio.playbackRate=Number($('#speed').value);});
 function tick(){const t=switchState.position(audio.currentTime||0),x=t*pxPerSecond;if(head)head.style.left=x+'px';const bar=barAt(data,t);$('#clock').textContent=`Bar ${bar} · ${formatTime(t)} / ${formatTime(data.seconds)}`;
  for(const b of document.querySelectorAll('#timeline button')){const section=sections.find(s=>s.first===Number(b.dataset.bar));b.setAttribute('aria-current',String(bar>=section.first&&bar<=section.last));}
  const key=Math.round(t*30)+':'+selected;if(key!==lastActive){for(const {element,n}of drawn)element.classList.toggle('active',n.change!=='old'&&n.start<=t&&n.end>t);lastActive=key;}
  if(!audio.paused&&$('#follow').checked&&(x<viewport.scrollLeft||x>viewport.scrollLeft+viewport.clientWidth*.8))viewport.scrollLeft=Math.max(0,x-viewport.clientWidth*.2);
 }
 audio.addEventListener('timeupdate',tick);audio.addEventListener('seeked',tick);audio.addEventListener('play',()=>{const frame=()=>{tick();if(!audio.paused)requestAnimationFrame(frame);};frame();});
 await choose(selected);render();document.body.dataset.ready='true';
}
