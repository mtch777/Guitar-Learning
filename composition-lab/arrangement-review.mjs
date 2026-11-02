// Read-only playback comparison. The payload contains measured native MIDI attacks.
export function noteKey(n){return JSON.stringify([n.part,n.voice,Math.round(n.start*44100),Math.round(n.end*44100),n.pitch,n.velocity,n.fret,n.string,n.dead,n.ghost]);}
export function difference(current,baseline){
 const available=new Map();for(const n of baseline){const k=noteKey(n);if(!available.has(k))available.set(k,[]);available.get(k).push(n);}
 const shown=current.map(n=>{const matches=available.get(noteKey(n));return {...n,change:matches?.length?(matches.pop(),'same'):'new'};});
 const removed=[...available.values()].flat().map(n=>({...n,change:'old'}));return {shown,removed};
}
export function pitchName(n){return ['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'][((n%12)+12)%12]+'_'+(Math.floor(n/12)-1);}
export function partRange(versions,part){const pitches=versions.flatMap(v=>v.notes.filter(n=>n.part===part).map(n=>n.pitch));return {low:Math.min(...pitches)-1,high:Math.max(...pitches)+1};}

if(typeof document!=='undefined')boot().catch(error=>{const e=document.querySelector('#error');e.hidden=false;e.className='error';e.textContent='The comparison could not load: '+error.message;console.error(error);});
async function boot(){
 const response=await fetch('comparison.json');if(!response.ok)throw Error('Missing comparison data');const data=await response.json();
 const $=s=>document.querySelector(s),audio=$('#audio'),viewport=$('#viewport'),roll=$('#roll'),axes=$('#axes'),compare=$('#compare');
 const byId=new Map(data.versions.map(v=>[v.id,v]));let selected='backing',drawn=[],head,lastActive='',switchToken=0;
 const width=16*155,pxPerSecond=width/data.seconds,svgNS='http://www.w3.org/2000/svg';
 const percussionNames={35:'Bass drum',36:'Kick',37:'Side stick',38:'Snare',40:'Snare',42:'Closed hat',44:'Pedal hat',46:'Open hat',41:'Low tom',43:'Low tom',45:'Mid tom',47:'Mid tom',48:'High tom',49:'Crash',51:'Ride',52:'China',55:'Splash',57:'Crash',59:'Ride'};
 const element=(name,attributes,text)=>{const e=document.createElementNS(svgNS,name);for(const[k,v]of Object.entries(attributes))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;};
 const descriptions={source:'Untouched captured score: no guitar or backing edits.',guitar:'The approved guitar variation, with the song’s original backing.',backing:'The approved guitar stays. Lighter rhythm-guitar and drum backing in bars 49–52; dense backing returns at bar 53.'};
 const sections=[['4 bars before',45,48],['First half',49,52],['Second half',53,56],['4 bars after',57,60]];
 for(const[label,first,last]of sections){const b=document.createElement('button');b.dataset.bar=first;b.innerHTML=`<strong>${first}–${last}</strong>${label}<small>${Math.round(timeOf(first))}s</small>`;b.addEventListener('click',()=>{audio.currentTime=Math.max(0,timeOf(first));viewport.scrollLeft=Math.max(0,audio.currentTime*pxPerSecond-30);tick();});$('#timeline').append(b);}
 function timeOf(bar){return data.bar_times.find(b=>b.bar===bar).time;}
 function render(){
  const current=byId.get(selected),base=byId.get(compare.value);const result=base?difference(current.notes,base.notes):{shown:current.notes.map(n=>({...n,change:'same'})),removed:[]};
  const changedParts=new Set([...result.shown.filter(n=>n.change==='new'),...result.removed].map(n=>n.part));
  const tracks=data.tracks.filter(t=>!$('#changedOnly').checked||changedParts.has(t.id));axes.replaceChildren();roll.replaceChildren();roll.style.width=width+'px';drawn=[];
  const top=document.createElement('div');top.style.height='28px';top.className='axis';top.textContent='Bar';top.style.padding='4px 8px';top.style.fontSize='12px';axes.append(top);
  const ruler=element('svg',{width,height:28,role:'img','aria-label':'Bar numbers'});
  for(const b of data.bar_times.filter(b=>b.bar<=60)){const x=Math.max(0,b.time)*pxPerSecond;ruler.append(element('rect',{x,y:0,width:155,height:28,fill:b.bar>=49&&b.bar<=56?'#293c3e':'#192a32'}));ruler.append(element('text',{x:x+6,y:19,fill:'#c4d3d9','font-size':12},b.bar));}
  roll.append(ruler);
  for(const track of tracks){
   const range=partRange(data.versions,track.id),pitchValues=track.percussion?[...new Set(data.versions.flatMap(v=>v.notes.filter(n=>n.part===track.id).map(n=>n.pitch)))].sort((a,b)=>b-a):null;
   const rowSize=track.percussion?19:9,rowCount=track.percussion?pitchValues.length:range.high-range.low+1;
   const height=Math.max(90,34+rowCount*rowSize),mapY=p=>34+(track.percussion?pitchValues.indexOf(p):range.high-p)*rowSize+rowSize/2;
   const axis=document.createElement('div');axis.className='axis';axis.style.height=height+'px';const title=document.createElement('div');title.className='axis-title';title.textContent=track.name;axis.append(title);
   const labels=track.percussion?pitchValues:Array.from({length:rowCount},(_,i)=>range.high-i).filter(p=>p%12===0||p===range.high-1||p===range.low+1);
   // End labels stay far enough apart to remain readable when a part has one pitch.
   let lastLabel=-100;for(const p of labels){const y=mapY(p);if(y-lastLabel<13)continue;lastLabel=y;const label=document.createElement('span');label.className='pitch-label';label.style.top=y+'px';label.textContent=track.percussion?(percussionNames[p]||'Drum '+p):pitchName(p);axis.append(label);}axes.append(axis);
   const svg=element('svg',{width,height,role:'img','aria-label':track.name+' piano roll','data-part':track.id});svg.append(element('rect',{x:0,y:0,width,height,fill:'#15252e'}));
   for(let row=0;row<rowCount;row++){const p=track.percussion?pitchValues[row]:range.high-row,y=mapY(p)-rowSize/2;svg.append(element('rect',{x:0,y,width,height:rowSize,fill:!track.percussion&&[1,3,6,8,10].includes(p%12)?'#13212a':'#192c36'}));}
   for(const b of data.bar_times.filter(b=>b.bar<=60)){const x=Math.max(0,b.time)*pxPerSecond;svg.append(element('line',{x1:x,x2:x,y1:28,y2:height,stroke:[49,53,57].includes(b.bar)?'#809174':'#3b535e','stroke-width':1}));for(let q=1;q<4;q++)svg.append(element('line',{x1:x+q*155/4,x2:x+q*155/4,y1:28,y2:height,stroke:'#253d48','stroke-width':0.6}));}
   const notes=[...result.removed,...result.shown].filter(n=>n.part===track.id);
   for(const n of notes){const x=n.start*pxPerSecond,w=Math.max(2,(n.end-n.start)*pxPerSecond-0.7),h=track.percussion?12:7;
    const rect=element('rect',{x,y:mapY(n.pitch)-h/2,width:w,height:h,rx:1,fill:n.change==='new'?'#5ce4ba':n.change==='old'?'none':'#748c99',stroke:n.change==='old'?'#ff9bb2':'none','stroke-width':n.change==='old'?1.7:0,'stroke-dasharray':n.change==='old'?'4 2':'none',class:'note','data-change':n.change,'data-start':n.start,'data-end':n.end});
    const name=track.percussion?(percussionNames[n.pitch]||'Drum '+n.pitch):pitchName(n.pitch);const wording=`${track.name} · bar ${n.bar} · ${name} · ${n.change==='old'?'removed / replaced':n.change==='new'?'new / changed':'unchanged'}`;rect.append(element('title',{},wording));rect.addEventListener('click',()=>{$('#details').textContent=wording;});svg.append(rect);drawn.push({element:rect,n});}
   svg.addEventListener('click',event=>{if(event.target.classList.contains('note'))return;const box=svg.getBoundingClientRect();audio.currentTime=Math.min(data.seconds,Math.max(0,(event.clientX-box.left)/pxPerSecond));tick();});roll.append(svg);
  }
  head=document.createElement('div');head.className='playhead';head.setAttribute('aria-hidden','true');roll.append(head);
  $('#description').textContent=descriptions[selected];$('#coverage').textContent=`${tracks.length} of ${data.tracks.length} playing parts shown. ${data.silent_tracks.length} other parts are silent here. ${base?`Colors compare with “${base.label}”.`:'No comparison overlay.'} Drums appear on named rows.`;
  for(const b of document.querySelectorAll('#timeline button')){const first=Number(b.dataset.bar),last=first+3;const label=first===45?'4 bars before':first===57?'4 bars after':first===49?(selected==='backing'?'Lighter backing':'First half'):(selected==='backing'?'Dense return':selected==='guitar'?'Changed guitar':'Second half');b.innerHTML=`<strong>${first}–${last}</strong>${label}<small>${Math.round(timeOf(first))}s</small>`;}
  if(!tracks.length){const empty=document.createElement('p');empty.className='load';empty.textContent='No changed parts in this comparison.';roll.append(empty);}
  for(const button of document.querySelectorAll('[data-version]'))button.setAttribute('aria-pressed',String(button.dataset.version===selected));lastActive='';tick();
 }
 async function choose(id){
  if(id===selected&&audio.getAttribute('src'))return;const token=++switchToken,position=audio.currentTime||0,playing=!audio.paused;audio.pause();selected=id;
  compare.value=id==='source'?'none':id==='guitar'?'source':'guitar';if(id==='source')$('#changedOnly').checked=false;render();
  audio.src=byId.get(id).audio;audio.load();await new Promise((resolve,reject)=>{audio.addEventListener('loadedmetadata',resolve,{once:true});audio.addEventListener('error',()=>reject(Error('Audio failed to load')),{once:true});});
  if(token!==switchToken)return;audio.currentTime=Math.min(position,audio.duration);audio.playbackRate=Number($('#speed').value);tick();if(playing)await audio.play();
 }
 for(const button of document.querySelectorAll('[data-version]'))button.addEventListener('click',()=>choose(button.dataset.version).catch(console.error));
 compare.addEventListener('change',()=>{if(compare.value==='none')$('#changedOnly').checked=false;render();});$('#changedOnly').addEventListener('change',render);$('#speed').addEventListener('change',()=>{audio.playbackRate=Number($('#speed').value);});
 function tick(){const t=audio.currentTime||0,x=t*pxPerSecond;if(head)head.style.left=x+'px';const bar=[...data.bar_times].reverse().find(b=>b.time<=t+1/44100)?.bar||45;$('#clock').textContent=`Bar ${Math.min(60,bar)} · ${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')} / 0:30`;
  for(const b of document.querySelectorAll('#timeline button'))b.setAttribute('aria-current',String(bar>=Number(b.dataset.bar)&&bar<Number(b.dataset.bar)+4));
  const key=Math.round(t*30)+':'+selected;if(key!==lastActive){for(const {element,n}of drawn)element.classList.toggle('active',n.change!=='old'&&n.start<=t&&n.end>t);lastActive=key;}
  if(!audio.paused&&$('#follow').checked&&(x<viewport.scrollLeft||x>viewport.scrollLeft+viewport.clientWidth*.8))viewport.scrollLeft=Math.max(0,x-viewport.clientWidth*.2);
 }
 audio.addEventListener('timeupdate',tick);audio.addEventListener('seeked',tick);audio.addEventListener('play',()=>{const frame=()=>{tick();if(!audio.paused)requestAnimationFrame(frame);};frame();});
 await choose(selected);render();document.body.dataset.ready='true';
}
