import test from 'node:test';
import assert from 'node:assert/strict';
import {difference,partRange,pitchedLaneGeometry,barAt,formatTime,comparisonView,changeScrollLeft,playbackSwitchState,versionClock,mapClockTime,clockProjector,boot} from './arrangement-review.mjs';
const note=(part,pitch,start=0,extra={})=>({part,pitch,start,end:start+1,voice:0,velocity:80,fret:0,string:1,dead:false,ghost:false,...extra});
test('coattacks and repeated identical notes are counted, never collapsed',()=>{
 const base=[note(0,40),note(0,47),note(0,47),note(1,40)];
 const current=[note(1,40),note(0,47),note(0,52)];
 const d=difference(current,base);assert.deepEqual(d.shown.map(n=>n.change),['same','same','new']);
 assert.deepEqual(d.removed.map(n=>n.pitch),[40,47]);assert.equal(base.length,4);
});
test('reordered addresses cannot disguise a changed pitch, duration, or voice',()=>{
 const base=[note(0,40,0,{ref:'old:0'}),note(0,43,1,{ref:'old:1'}),note(0,47,2)];
 const current=[note(0,45,1,{ref:'old:1'}),note(0,40,0,{ref:'new:99'}),note(0,47,2,{end:4}),note(0,47,2,{voice:1})];
 const d=difference(current,base);assert.equal(d.shown.filter(n=>n.change==='same').length,1);assert.equal(d.removed.length,2);
});
test('pitch bounds include all versions, low notes and high removed notes',()=>{
 const versions=[{notes:[note(0,27),note(0,90),note(1,10)]},{notes:[note(0,15),note(0,60)]}];
 assert.deepEqual(partRange(versions,0),{low:14,high:91});
});

test('a full MIDI range fits without cropping or overlapping adjacent pitched notes',()=>{
 const versions=[{notes:[note(0,0),note(0,127)]},{notes:[note(0,60)]}],before=JSON.stringify(versions);
 const geometry=pitchedLaneGeometry(partRange(versions,0));
 assert.equal(geometry.height,280);assert.equal(geometry.rowCount,130);
 const extent=(geometry.noteHeight+geometry.outlineWidth)/2;
 for(let pitch=0;pitch<=127;pitch++){
  assert(geometry.mapY(pitch)-extent>=34);assert(geometry.mapY(pitch)+extent<=geometry.height);
  if(pitch<127){
   assert(geometry.mapY(pitch+1)+extent<geometry.mapY(pitch)-extent);
   assert(Math.abs(geometry.mapY(pitch)-geometry.mapY(pitch+1)-geometry.rowSize)<1e-10);
  }
 }
 assert.equal(JSON.stringify(versions),before);
});

test('wide all-version bounds keep removed extremes and equal pitch distances',()=>{
 const versions=[{notes:[note(0,27),note(0,90)]},{notes:[note(0,15),note(0,60)]}];
 const geometry=pitchedLaneGeometry(partRange(versions,0));
 assert.equal(geometry.height,280);assert.equal(geometry.rowCount,78);
 assert(Math.abs((geometry.mapY(15)-geometry.mapY(27))-(geometry.mapY(60)-geometry.mapY(72)))<1e-10);
 assert(geometry.mapY(90)>34);assert(geometry.mapY(15)<280);
});

test('single-pitch and short ranges retain their original lane and glyph sizes',()=>{
 const single=pitchedLaneGeometry(partRange([{notes:[note(0,42)]}],0));
 assert.deepEqual([single.rowCount,single.rowSize,single.height,single.noteHeight,single.outlineWidth,single.mapY(42)],[3,9,90,7,1.7,47.5]);
 const short=pitchedLaneGeometry(partRange([{notes:[note(0,48),note(0,60)]}],0));
 assert.deepEqual([short.rowCount,short.rowSize,short.height,short.noteHeight,short.outlineWidth],[15,9,169,7,1.7]);
});
test('different bar numbers and unequal bar durations use the supplied clock',()=>{
 const data={bars:[21,23],bar_times:[{bar:21,time:0},{bar:22,time:1.5},{bar:23,time:3},{bar:24,time:5}]};
 assert.equal(barAt(data,0),21);assert.equal(barAt(data,1.5-1e-6),22);assert.equal(barAt(data,4.8),23);assert.equal(barAt(data,5),23);
 assert.equal(formatTime(65.8),'1:05');
});
test('filter without a distinct comparison cannot erase the original',()=>{
 const current={id:'source',notes:[{part:1,pitch:60,start:0,end:1}]};
 for(const base of [undefined,current,{id:'same-notes',notes:current.notes}]){
  const view=comparisonView(current,base,true);
  assert.equal(view.canFilter,false);assert.equal(view.filterActive,false);assert.equal(view.shown.length,1);assert.equal(view.removed.length,0);
 }
});
test('changed-part filter keeps context notes and reveals offscreen changes without moving audio',()=>{
 const common={part:1,voice:0,pitch:60,start:0,end:1};
 const current={id:'edit',notes:[common,{...common,pitch:65,start:15,end:16},{...common,part:2}]};
 const baseline={id:'source',notes:[common,{...common,pitch:64,start:15,end:16},{...common,part:2}]};
 const view=comparisonView(current,baseline,true);
 assert.equal(view.filterActive,true);assert.deepEqual([...view.changedParts],[1]);assert.equal(view.shown.filter(n=>view.changedParts.has(n.part)).length,2);
 assert.equal(changeScrollLeft(view.changes,0,400,100),1480);
 assert.equal(changeScrollLeft(view.changes,2200,400,100),1480);
 assert.equal(changeScrollLeft(view.changes,1400,400,100),1400);
 assert.equal(current.notes[1].start,15);
});

test('rapid A/B/C switches preserve position and playback through every load completion order',()=>{
 for(const order of [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]){
  const state=playbackSwitchState(),tokens=[state.begin(219,true),state.begin(0,false),state.begin(0,false)];
  assert.equal(state.position(0),219);
  let actualPosition=0,applied=[];
  for(const index of order){
   const target=state.complete(tokens[index],290.55);
   if(target){applied.push(target);actualPosition=target.position;}
   assert.equal(state.position(actualPosition),219);
  }
  assert.deepEqual(applied,[{position:219,playing:true}]);
  assert.equal(state.isCurrent(tokens[0]),false);assert.equal(state.isCurrent(tokens[2]),true);
 }
});

test('explicit seeks while loading survive later version clicks and retain paused intent',()=>{
 const state=playbackSwitchState(),a=state.begin(219,false);
 assert.equal(state.seek(88),true);assert.equal(state.position(0),88);
 const b=state.begin(0,false);assert.equal(state.seek(112),true);
 const c=state.begin(0,false);
 assert.equal(state.complete(a,290.55),null);assert.equal(state.complete(b,290.55),null);
 assert.deepEqual(state.complete(c,290.55),{position:112,playing:false});
 assert.equal(state.seek(45),false);assert.equal(state.position(45),45);
});

test('incomplete metadata cannot consume the pending target and a settled switch captures the new position',()=>{
 const state=playbackSwitchState(),a=state.begin(219,true);
 assert.equal(state.complete(a,NaN),null);assert.equal(state.position(0),219);
 assert.deepEqual(state.complete(a,220),{position:219,playing:true});
 const b=state.begin(250,false);
 assert.deepEqual(state.complete(b,240),{position:240,playing:false});
});

// Small DOM/audio boundary fixture: execute the real boot and event handlers.
// It does not simulate browser rendering or actual sound reproduction.
function reviewDom(duration){
 class Element{
  constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.attributes={};this.style={};this.events=new Map();this.className='';this.textContent='';this.value='';this.checked=false;this.scrollLeft=0;this.clientWidth=500;
   this.classList={contains:name=>this.className.split(' ').includes(name),toggle:(name,on)=>{const set=new Set(this.className.split(' ').filter(Boolean));on?set.add(name):set.delete(name);this.className=[...set].join(' ');}};}
  append(...items){for(const item of items){item.parentElement=this;this.children.push(item);}}
  prepend(...items){for(const item of items)item.parentElement=this;this.children.unshift(...items);}
  replaceChildren(...items){this.children=[];this.append(...items);}
  setAttribute(name,value){this.attributes[name]=String(value);if(name==='class')this.className=String(value);if(name.startsWith('data-'))this.dataset[name.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=String(value);}
  getAttribute(name){return name==='src'?this.src:this.attributes[name];}
  addEventListener(name,fn){if(!this.events.has(name))this.events.set(name,new Set());this.events.get(name).add(fn);}
  removeEventListener(name,fn){this.events.get(name)?.delete(fn);}
  fire(name,event={}){for(const fn of this.events.get(name)||[])fn(event);}
  closest(selector){for(let p=this;p;p=p.parentElement)if(selector.startsWith('.')?p.classList.contains(selector.slice(1)):p.tagName===selector)return p;return null;}
  scrollIntoView(){this.scrolledIntoView=true;}
  get options(){return this.children;}
  get previousElementSibling(){return this.parentElement.children[this.parentElement.children.indexOf(this)-1];}
  getBoundingClientRect(){return {left:0,height:80};}
 }
 const body=new Element('body'),map=new Map(),all=()=>{const out=[];const visit=e=>{out.push(e);e.children.forEach(visit);};visit(body);return out;};
 function add(tag,id,cls='',parent=body){const e=new Element(tag);e.id=id;e.className=cls;parent.append(e);if(id)map.set('#'+id,e);if(cls)map.set('.'+cls,e);return e;}
 for(const id of ['title','artist','scope','rollHint','settings','questions','coverage','details','clock','error'])add('div',id);
 add('div',null,'versions');add('div',null,'downloads');add('div',null,'legend');
 const description=add('p');add('strong',null,'',description);add('span','description','',description);
 const player=add('div',null,'player'),audio=add('audio','audio','',player),controls=add('div',null,'controls',player);
 for(const id of ['compare','speed'])add('select',id,'',add('label',null,'',controls));
 const rollControls=add('div',null,'controls');
 for(const id of ['follow','changedOnly'])add('input',id,'',add('label',null,'',rollControls));
 map.get('#speed').value='1';map.get('#follow').checked=true;
 add('div','timeline');add('div','axes');add('div','roll','',add('div','viewport'));
 Object.assign(audio,{paused:true,currentTime:0,duration,readyState:0,playbackRate:1,playCalls:0,
  pause(){this.paused=true;},play(){this.playCalls++;this.paused=false;return Promise.resolve();},
  load(){queueMicrotask(()=>{this.readyState=1;this.fire('loadedmetadata');});}});
 const document={body,title:'',createElement:t=>new Element(t),createElementNS:(_,t)=>new Element(t),createTextNode:t=>Object.assign(new Element('#text'),{textContent:t}),
  querySelector:s=>map.get(s)||all().find(e=>s==='#'+e.id),
  querySelectorAll:s=>s==='[data-version]'?all().filter(e=>e.dataset.version!==undefined):s==='#timeline button'?map.get('#timeline').children.filter(e=>e.tagName==='button'&&e.dataset.bar!==undefined):[]};
 return {document,audio,map,all};
}


const clockReview=()=>({title:'Clock comparison',artist:'Invent Animate',seconds:8,bars:[10,12],
 original_version:'source',default_version:'source',all_parts:1,
 tracks:[{id:7,name:'Guitar',percussion:false}],silent_tracks:[],questions:['Does the tempo change preserve the idea?'],
 sections:[{first:11,last:12,label:'Changed passage'}],focus_bars:[11,12],
 bar_times:[{bar:10,time:0},{bar:11,time:2},{bar:12,time:5},{bar:13,time:8}],playback_note:'Matched audio settings; each version retains its tempo.',
 versions:[{id:'source',label:'Original',description:'No musical edits.',compare_to:null,audio:'source.wav',
 notes:[note(7,40,.5),note(7,52,2.25),note(7,59,5.5)]}]});

test('written coordinates distinguish musical edits from tempo-scaled playback and mute release',()=>{
 const written={comparison_identity:'source:0',score_start_tick:960,score_end_tick:1920};
 const original=note(7,60,1,{end:2,...written}),faster={...original,start:.5,end:.72};
 assert.equal(difference([faster],[original]).shown[0].change,'same');
 for(const change of[{pitch:61},{score_start_tick:1200},{score_end_tick:2400},{velocity:95}]){
  const result=difference([{...faster,...change}],[original]);assert.equal(result.shown[0].change,'new');assert.equal(result.removed.length,1);
 }
 assert.throws(()=>difference([{...faster,score_end_tick:undefined}],[original]),/written score/);
 assert.throws(()=>difference([{...faster,comparison_identity:undefined}],[original]),/written score/);
});

test('clock projection keeps beat fraction across unequal tempo regions and exact audio end',()=>{
 const from={bars:[7,8],seconds:8.00001,bar_times:[{bar:7,time:0,beat_times:[1,3]},{bar:8,time:4,beat_times:[5,7]},{bar:9,time:8}]};
 const to={bars:[7,8],seconds:4.00001,bar_times:[{bar:7,time:0,beat_times:[.5,1]},{bar:8,time:2,beat_times:[2.5,3]},{bar:9,time:4}]};
 assert.equal(mapClockTime(2,from,to),.75);assert.equal(mapClockTime(.75,to,from),2);
 assert.equal(mapClockTime(5,from,to),2.5);assert.equal(mapClockTime(from.seconds,from,to),to.seconds);
 assert.equal(mapClockTime(-1,from,to),0);assert.equal(mapClockTime(.123456789,from,from),.123456789);
 const project=clockProjector(from,to);assert.equal(project(2),.75);
 assert.throws(()=>mapClockTime(1,from,{...to,bar_times:to.bar_times.map(b=>({...b,beat_times:[]}))}),/corresponding/);
});

test('removed-note outlines use the selected version clock while current performed ends remain measured',()=>{
 const data={bars:[7,8],seconds:8,bar_times:[{bar:7,time:0},{bar:8,time:4},{bar:9,time:8}]};
 const n=note(7,60,2,{end:3,comparison_identity:'source:0',score_start_tick:960,score_end_tick:1920});
 const original={id:'original',notes:[n]},changed={id:'changed',seconds:4,bar_times:[{bar:7,time:0},{bar:8,time:2},{bar:9,time:4}],notes:[{...n,pitch:65,start:1,end:1.2}]};
 const before=JSON.stringify([data,original,changed]),view=comparisonView(changed,original,true,data);
 assert.equal(view.filterActive,true);assert.equal(view.removed[0].start,1);assert.equal(view.removed[0].end,1.5);
 assert.equal(view.shown[0].start,1);assert.equal(view.shown[0].end,1.2);
 assert.equal(JSON.stringify([data,original,changed]),before);
});

test('rapid switches project the retained musical position and pending seeks once per version',()=>{
 for(const order of[[0,1,2],[2,0,1],[1,2,0]]){
  const state=playbackSwitchState(),a=state.begin(6,true,x=>x/2),b=state.begin(0,false,x=>x*3),c=state.begin(0,false,x=>x/3);
  assert.equal(state.position(0),3);const tokens=[a,b,c],completed=[];
  for(const index of order){const result=state.complete(tokens[index],4);if(result)completed.push(result);}
  assert.deepEqual(completed,[{position:3,playing:true}]);
 }
 const state=playbackSwitchState();state.begin(6,false,x=>x/2);state.seek(1);
 const latest=state.begin(0,false,x=>x*2);assert.deepEqual(state.complete(latest,8),{position:2,playing:false});
});

test('real boot uses each WAV clock, musical-position switching, changed-part filter and section seeking without autoplay',async()=>{
 const data=clockReview();
 data.default_version='source';
 data.versions[0].notes=data.versions[0].notes.map((n,i)=>({...n,comparison_identity:'source:'+i,score_start_tick:i*960,score_end_tick:(i+1)*960}));
 data.versions[0].seconds=data.seconds;data.versions[0].bar_times=structuredClone(data.bar_times);
 data.versions.push({...data.versions[0],id:'fast',label:'Faster changed version',audio:'fast.wav',compare_to:'source',seconds:4,
  bar_times:data.bar_times.map(b=>({...b,time:b.time/2})),
  notes:data.versions[0].notes.map((n,i)=>({...n,pitch:n.pitch+(i===1?2:0),start:n.start/2,end:n.end/2}))});
 const dom=reviewDom(data.seconds),previous={document:globalThis.document,fetch:globalThis.fetch};
 dom.audio.load=function(){queueMicrotask(()=>{this.duration=data.versions.find(v=>v.audio===this.src).seconds;this.readyState=1;this.fire('loadedmetadata');});};
 globalThis.document=dom.document;globalThis.fetch=async()=>({ok:true,json:async()=>data});
 const settle=()=>new Promise(resolve=>setImmediate(resolve));
 try{
  await boot();dom.audio.currentTime=5.5;dom.audio.fire('seeked');
  const buttons=dom.document.querySelectorAll('[data-version]');buttons.find(b=>b.dataset.version==='fast').fire('click');await settle();
  assert.equal(dom.audio.src,'fast.wav');assert.equal(dom.audio.duration,4);assert.equal(dom.audio.currentTime,2.75);assert.equal(dom.audio.playCalls,0);
  assert.match(dom.map.get('#clock').textContent,/Bar 12/);assert.match(dom.map.get('#clock').textContent,/0:04/);
  const notes=dom.all().filter(e=>e.classList.contains('note'));assert.equal(notes.filter(e=>e.dataset.change==='new').length,1);assert.equal(notes.filter(e=>e.dataset.change==='same').length,2);
  dom.map.get('#changedOnly').checked=true;dom.map.get('#changedOnly').fire('change');
  assert.equal(dom.map.get('#changedOnly').checked,true);assert(dom.all().some(e=>e.classList.contains('note')));
  dom.document.querySelectorAll('#timeline button')[0].fire('click');assert.equal(dom.audio.currentTime,1);
  dom.audio.currentTime=4;dom.audio.fire('seeked');buttons.find(b=>b.dataset.version==='source').fire('click');await settle();
  assert.equal(dom.audio.duration,8);assert.equal(dom.audio.currentTime,8);assert.equal(dom.audio.playCalls,0);
  assert.equal(dom.map.get('#changedOnly').checked,false);
 }finally{if(previous.document===undefined)delete globalThis.document;else globalThis.document=previous.document;globalThis.fetch=previous.fetch;}
});
