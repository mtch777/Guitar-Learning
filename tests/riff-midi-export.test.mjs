import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRiffMidi, createRiffMpe, riffMidiFilename} from '../src/riff-midi-export.js';
import {DROP_E, toEventScore} from '../src/riff-event-score.js';
const nativePath=resolve('.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs');
const at=existsSync(nativePath)?await import(pathToFileURL(nativePath).href):null;
const skip=at?false:'Native alphaTab 1.8.4 not installed';
const note=(string_number,fret,duration_q,marks={})=>({string_number,fret,pitch:DROP_E[string_number-1]+fret,duration_q,marks});

// Independent Standard MIDI File parser: inspect the bytes a DAW receives,
// not alphaTab's pre-serialization event objects.
function parse(bytes) {
  const data=Buffer.from(bytes);let p=0;
  const ascii=n=>{const x=data.toString('ascii',p,p+n);p+=n;return x;};
  const u16=()=>{const x=data.readUInt16BE(p);p+=2;return x;};
  const u32=()=>{const x=data.readUInt32BE(p);p+=4;return x;};
  const vlq=()=>{let n=0,b,count=0;do{assert(++count<=4);b=data[p++];n=(n<<7)|(b&127);}while(b&128);return n;};
  assert.equal(ascii(4),'MThd');assert.equal(u32(),6);
  const format=u16(),tracks=u16(),division=u16(),events=[];
  for(let track=0;track<tracks;track++) {
    assert.equal(ascii(4),'MTrk');const length=u32(),end=p+length;let tick=0,running;
    while(p<end) {
      tick+=vlq();let status=data[p++];
      if(status<128){assert(running);p--;status=running;}else if(status<240)running=status;
      if(status===255){const type=data[p++],size=vlq(),payload=[...data.subarray(p,p+size)];p+=size;events.push({track,tick,type,payload});}
      else {
        assert(status>=128&&status<240,`Nonstandard MIDI status ${status}`);
        const kind=status>>4,channel=status&15,size=[12,13].includes(kind)?1:2;
        const payload=[...data.subarray(p,p+size)];p+=size;
        assert(payload.every(x=>x<128));events.push({track,tick,kind,channel,payload});
      }
    }
    assert.equal(p,end);
  }
  assert.equal(p,data.length);return {format,tracks,division,events};
}
const sorted=rows=>rows.sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));
function compareNative(result) {
  const calls=[];
  new at.midi.MidiFileGenerator(toEventScore(at,result),new at.Settings(),
    new Proxy({},{get:(_,method)=>(...args)=>calls.push({method,args})})).generate();
  const midi=parse(createRiffMidi(at,result));
  assert.equal(midi.format,1);assert.equal(midi.tracks,1+new Set(result.events.flatMap(e=>e.members.map(n=>n.string_number))).size);assert.equal(midi.division,960);
  const expected=calls.filter(c=>c.method==='addNote').map(c=>c.args);
  assert.deepEqual(sorted(midi.events.filter(e=>e.kind===9&&e.payload[1]>0).map(e=>[e.tick,e.payload[0],e.payload[1]])),
    sorted(expected.map(a=>[a[1],a[3],a[4]])));
  assert.deepEqual(sorted(midi.events.filter(e=>e.kind===8).map(e=>[e.tick,e.payload[0]])),
    sorted(expected.map(a=>[a[1]+a[2],a[3]])));
  assert.equal(midi.events.filter(e=>e.type===47).length,midi.tracks);
  for(const end of midi.events.filter(e=>e.type===47))assert.equal(end.tick,Number(result.duration_q)*960);
  const tempo=midi.events.find(e=>e.type===81);
  const microseconds=tempo.payload.reduce((n,b)=>n*256+b,0);
  assert.equal(tempo.tick,0);assert(Math.abs(60000000/microseconds-result.tempo)<.001);
  assert(midi.events.some(e=>e.kind===12&&e.payload[0]===30));
  return midi;
}
const fixture={request:{mode:'Dorian'},tempo:142,tuning:DROP_E,duration_q:'8.5',meter:[3,4],bar_map:[
  {onset_q:'0',span_q:'3',meter:[3,4]}, {onset_q:'3',span_q:'3.5',meter:[7,8]}, {onset_q:'6.5',span_q:'2',meter:[4,4]}],events:[
  {onset_q:'1/2',members:[note(8,0,'1/3'),note(5,7,'5')]},
  {onset_q:'5/6',members:[note(8,3,'1/3',{velocity:'f'})]},
  {onset_q:'7/6',members:[note(8,5,'1/3')]},
  {onset_q:'6',members:[note(7,2,'1/2',{palm_mute:true})]},
]};

test('standard MIDI preserves full-riff notes, triplets, chord holds, rests, tempo and changing meters',{skip},()=>{
  const midi=compareNative(fixture);
  assert.deepEqual(midi.events.filter(e=>e.type===88).map(e=>[e.tick,e.payload[0],2**e.payload[1]]),[[0,3,4],[2880,7,8],[6240,4,4]]);
  assert.equal(midi.events.filter(e=>e.kind===9).length,5,'Ties must not reattack');
});
test('repeat exports are identical and never change the generated data',{skip},()=>{
  const before=structuredClone(fixture),first=createRiffMidi(at,fixture);
  assert.deepEqual(createRiffMidi(at,fixture),first);assert.deepEqual(fixture,before);
});
test('connected legato slides and bends become standard pitch-wheel events with native note clocks',{skip},()=>{
  const bend={points:[{offset_fraction:'0',semitones:'0'},{offset_fraction:'1',semitones:'2'}]};
  const input={tempo:120,tuning:DROP_E,duration_q:'8',events:[
    {onset_q:'0',members:[note(5,7,'1/4',{slide:'legato'})]},
    {onset_q:'1/4',members:[note(5,9,'1/4',{slide:'legato'})]},
    {onset_q:'1/2',members:[note(5,7,'1/4')]},
    {onset_q:'2',members:[note(8,3,'2',{bend})]},
  ]};
  const midi=compareNative(input),wheels=midi.events.filter(e=>e.kind===14);
  assert(wheels.some(e=>e.tick===240&&e.payload[0]+128*e.payload[1]===9216));
  assert(wheels.some(e=>e.tick===3840&&e.payload[0]+128*e.payload[1]===9216));
  assert.equal(midi.events.filter(e=>e.kind===9).length,2);
});
test('invalid score clocks refuse without exporting rounded MIDI',{skip},()=>{
  const input={tempo:120,tuning:DROP_E,duration_q:'1/7',events:[{onset_q:'0',members:[note(8,3,'1/7')]}]};
  assert.throws(()=>createRiffMidi(at,input),/native tick grid/);
});
test('MIDI filenames are timestamped, mode-labelled and filesystem-safe',()=>{
  const one=riffMidiFilename(fixture,new Date('2026-11-07T01:02:03.004Z'));
  assert.equal(one,'drop-e-dorian-riff-2026-11-07T01-02-03-004Z.mid');
  assert.notEqual(one,riffMidiFilename(fixture,new Date('2026-11-07T01:02:03.005Z')));
  assert(!/[\\/:]/.test(riffMidiFilename({request:{mode:'../bad:name'}})));
});

for(const mpe of [false,true])test(`${mpe?'MPE':'MIDI'} button exports accepted riff through repeats, preview changes and failed/new generation`,{skip},async()=>{
  const button=mpe?'download-mpe':'download-midi',exportFile=mpe?createRiffMpe:createRiffMidi;
  const {mountBuilder}=await import('../src/riff-builder-view.js');
  const old={};for(const key of ['document','window','Worker','setTimeout','clearTimeout'])old[key]=globalThis[key];
  const oldCreate=URL.createObjectURL,oldRevoke=URL.revokeObjectURL;
  const downloads=[],blobs=new Map(),timers=new Map();let worker,api,serial=0;
  class Element {
    constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.dataset={};this.attributes={};this.classList={add(){},remove(){},toggle(){}};}
    addEventListener(name,fn){this.listeners[name]=fn;}
    fire(name,event={}){return this.listeners[name]?.(event);}
    append(...children){for(const child of children){child.parent=this;this.children.push(child);}}
    prepend(...children){this.children.unshift(...children);}
    replaceChildren(...children){this.children=[];this.append(...children);}
    setAttribute(name,value){this.attributes[name]=value;}
    querySelectorAll(){return this.children.filter(e=>e.tag==='button');}
    remove(){if(this.parent)this.parent.children=this.parent.children.filter(e=>e!==this);}
    click(){downloads.push({name:this.download,blob:blobs.get(this.href)});}
  }
  const elements=new Map(),get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const body=new Element();
  class FakeApi {
    constructor(){api=this;for(const name of ['error','scoreLoaded','playerReady','playerStateChanged','playerPositionChanged'])this[name]={on:fn=>this[name].emit=fn};}
    stop(){} pause(){} play(){} playPause(){}
    load(score){this.score=score;this.scoreLoaded.emit();this.playerReady.emit();}
  }
  try {
    globalThis.document={body,baseURI:'http://localhost/',getElementById:get,createElement:tag=>new Element(tag),querySelectorAll:()=>[]};
    globalThis.window={alphaTab:{...at,AlphaTabApi:FakeApi}};
    globalThis.Worker=class {constructor(){worker=this;}postMessage(message){this.last=message;}terminate(){}};
    globalThis.setTimeout=(fn,ms)=>{const id=++serial;timers.set(id,{fn,ms});return id;};
    globalThis.clearTimeout=id=>timers.delete(id);
    URL.createObjectURL=blob=>{const url=`blob:${++serial}`;blobs.set(url,blob);return url;};URL.revokeObjectURL=url=>blobs.delete(url);
    mountBuilder();
    assert.equal(get(button).disabled,true);
    get(button).fire('click');assert.equal(downloads.length,0);
    const accepted={...structuredClone(fixture),status:'generated',phrases:[{offset_q:'0',length_q:'17/2',label:'Full riff',blocks:[]}]};
    get('generate').fire('click');assert.equal(get(button).disabled,true);
    await worker.onmessage({data:{id:worker.last.id,type:'result',result:accepted}});
    assert.equal(get(button).disabled,false);
    get(button).fire('click');
    const bytes=Buffer.from(await downloads[0].blob.arrayBuffer());
    assert.equal(downloads[0].blob.type,'audio/midi');assert.match(downloads[0].name,new RegExp(`^drop-e-dorian-${mpe?'mpe-':''}riff-.*\\.mid$`));
    assert.deepEqual(bytes,Buffer.from(exportFile(at,accepted)));
    assert.equal(body.children.length,0,'Temporary download anchor removed');
    const half=new Element('button');half.dataset.speed='0.5';get('speeds').append(half);
    get('speeds').fire('click',{target:{closest:()=>half}});
    get('seek').value='6';get('seek').fire('input');
    get('section-playback').children[0].fire('click');
    get(button).fire('click');
    assert.equal(api.playbackSpeed,.5);assert.deepEqual(Buffer.from(await downloads[1].blob.arrayBuffer()),bytes);
    get('generate').fire('click');get(button).fire('click');
    assert.equal(downloads.length,2,'Busy handler guard prevents exporting even if invoked directly');
    await worker.onmessage({data:{id:worker.last.id,type:'result',result:{status:'no_choice',message:'No choice'}}});
    assert.equal(get(button).disabled,false);
    get(button).fire('click');assert.deepEqual(Buffer.from(await downloads[2].blob.arrayBuffer()),bytes);
    get('generate').fire('click');const newer=structuredClone(accepted);newer.tempo=120;
    await worker.onmessage({data:{id:worker.last.id,type:'result',result:newer}});
    get(button).fire('click');assert.notDeepEqual(Buffer.from(await downloads[3].blob.arrayBuffer()),bytes);
    // Export failures do not destroy or disable the accepted riff.
    URL.createObjectURL=()=>{throw new Error('Download unavailable');};
    get(button).fire('click');assert.match(get('status').textContent,/MIDI export failed: Download unavailable/);
    assert.equal(get(button).disabled,false);assert.equal(body.children.length,0);
    for(const timer of timers.values())if(timer.ms===1000)timer.fn();
    assert.equal(blobs.size,0,'Every created object URL is released');
  } finally {
    for(const [key,value] of Object.entries(old)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}
    URL.createObjectURL=oldCreate;URL.revokeObjectURL=oldRevoke;
  }
});

const bend=semitones=>({points:[{offset_fraction:'0',semitones:'0'},{offset_fraction:'1',semitones:String(semitones)}]});
function nativeCalls(result) {
  const calls=[];
  new at.midi.MidiFileGenerator(toEventScore(at,result),new at.Settings(),
    new Proxy({},{get:(_,method)=>(...args)=>calls.push({method,args})})).generate();
  return calls;
}
function oldSharedChannelMidi(result) {
  const midi=new at.midi.MidiFile();
  new at.midi.MidiFileGenerator(toEventScore(at,result),new at.Settings(),new at.midi.AlphaSynthMidiFileHandler(midi,true)).generate();
  return parse(midi.toBinary());
}
const nativeWheelAt=(input,key,tick)=>Math.floor(nativeCalls(input).filter(e=>e.method==='addNoteBend'&&e.args[3]===key&&e.args[1]<=tick).sort((a,b)=>a.args[1]-b.args[1]).at(-1)?.args[4]??8192);
const wheelAt=(midi,channel,tick)=>midi.events.filter(e=>e.kind===14&&e.channel===channel&&e.tick<=tick).at(-1)?.payload.reduce((n,b,i)=>n+b*128**i,0)??8192;

test('new attacks cannot reset a held bend or make another string inherit it',{skip},()=>{
  const input={tempo:120,duration_q:'4',events:[
    {onset_q:'0',members:[note(8,3,'4',{bend:bend(2)})]},
    {onset_q:'1',members:[note(5,7,'1')]},
  ]};
  const old=oldSharedChannelMidi(input),fixed=compareNative(input);
  assert.equal(wheelAt(old,0,960),8192,'Reproduce original bug: ordinary attack zeroes ongoing bend');
  assert.equal(wheelAt(fixed,7,960),8448,'Held low string keeps its half-semitone bend');
  assert.equal(wheelAt(fixed,4,1440),8192,'Other sounding string stays unbent');
  assert.notEqual(wheelAt(old,0,1440),8192,'Original export also bends the unrelated held note');
});

test('simultaneous opposite bends retain independent string channels and named tracks',{skip},()=>{
  const input={tempo:120,duration_q:'4',events:[{onset_q:'0',members:[
    note(8,3,'4',{bend:bend(2)}),note(5,7,'4',{bend:bend(-1)})]}]};
  const midi=compareNative(input),notes=midi.events.filter(e=>e.kind===9);
  assert.deepEqual(new Set(notes.map(e=>e.channel)),new Set([4,7]));
  assert.equal(wheelAt(midi,7,1920),nativeWheelAt(input,31,1920));assert.equal(wheelAt(midi,4,1920),nativeWheelAt(input,52,1920));
  for(const [channel,key] of [[7,31],[4,52]])for(const event of nativeCalls(input).filter(e=>e.method==='addNoteBend'&&e.args[3]===key)) {
    assert.equal(wheelAt(midi,channel,event.args[1]),nativeWheelAt(input,key,event.args[1]));
  }
  const names=midi.events.filter(e=>e.type===3).map(e=>Buffer.from(e.payload).toString());
  assert.deepEqual(names,['Riff tempo and meter','Drop E string 5','Drop E string 8']);
  for(const channel of [4,7]) {
    const lane=midi.events.filter(e=>e.channel===channel),track=notes.find(e=>e.channel===channel).track;
    assert(lane.every(e=>e.track===track));
    const controls=lane.filter(e=>e.kind===11&&e.tick===0).map(e=>e.payload);
    for(const pair of [[100,0],[101,0],[38,0],[6,16]])assert(controls.some(c=>c[0]===pair[0]&&c[1]===pair[1]));
    assert(lane.some(e=>e.kind===12&&e.payload[0]===30));
  }
});

test('unison notes on separate strings keep independent curves and releases',{skip},()=>{
  const input={tempo:120,duration_q:'4',events:[{onset_q:'0',members:[
    note(8,12,'4',{bend:bend(2)}),note(6,0,'2')]}]};
  const midi=compareNative(input);
  assert.equal(midi.events.filter(e=>e.kind===9&&e.payload[0]===40).length,2);
  assert.equal(wheelAt(midi,5,960),8192);assert.equal(wheelAt(midi,7,960),nativeWheelAt(input,40,960));
  assert(midi.events.some(e=>e.kind===8&&e.channel===5&&e.tick===1920));
  assert(midi.events.some(e=>e.kind===8&&e.channel===7&&e.tick===3840));
});

test('same-string bend endings reset before new attacks; let-ring does not leak to other strings',{skip},()=>{
  const input={tempo:120,duration_q:'4',events:[
    {onset_q:'0',members:[note(8,3,'1',{bend:bend(2)}),note(5,7,'1',{let_ring:true})]},
    {onset_q:'1',members:[note(8,5,'1')]},
    {onset_q:'2',members:[note(5,9,'1')]},
  ]};
  const midi=compareNative(input);
  assert.equal(wheelAt(midi,7,960),8192);assert.equal(wheelAt(midi,4,480),8192);
  const atBoundary=midi.events.filter(e=>e.channel===7&&e.tick===960);
  const attack=atBoundary.findIndex(e=>e.kind===9),reset=atBoundary.findLastIndex(e=>e.kind===14&&e.payload[0]===0&&e.payload[1]===64);
  assert(reset>=0&&reset<attack,'Reset must precede the new attack, after old curve events');
});

test('export routing never changes the native player or source and avoids percussion channel',{skip},()=>{
  const input={tempo:120,duration_q:'4',events:[{onset_q:'0',members:Array.from({length:8},(_,i)=>note(i+1,3,'1',{bend:bend(1)}))}]};
  const before=structuredClone(input),calls=nativeCalls(input);
  const determine=at.midi.MidiFileGenerator.prototype._determineChannel,generateTrack=at.midi.MidiFileGenerator.prototype._generateTrack;
  const midi=compareNative(input);
  assert.equal(midi.tracks,9);assert(!midi.events.some(e=>e.channel===9));
  assert.deepEqual(nativeCalls(input),calls);assert.deepEqual(input,before);
  assert.equal(at.midi.MidiFileGenerator.prototype._determineChannel,determine);
  assert.equal(at.midi.MidiFileGenerator.prototype._generateTrack,generateTrack);
});

test('18 fixed public-composer riffs preserve native note clocks and every sounding pitch path',{skip,timeout:120000},async t=>{
  const {execFileSync}=await import('node:child_process');
  const {fileURLToPath}=await import('node:url');
  const root=fileURLToPath(new URL('../',import.meta.url));
  const local=resolve(root,'.local/songsterr-venv/Scripts/python.exe');
  const python=existsSync(local)?local:(process.env.PYTHON||'python3');
  const script=[
    "import sys,json;sys.path.insert(0,'composition-lab')",
    'from test_procedural_riff_browser import ENGINE,PACK',
    "cases=[{'artists':[a],'mode':m,'seed':606} for a in ENGINE.ARTISTS for m in ENGINE.MODES]",
    'out=[]',
    'for request in cases:',
    ' r=ENGINE.generate(request,PACK)',
    " out.append({k:r[k] for k in ['status','request','tempo','tuning','duration_q','events','meter','bar_map'] if k in r})",
    'print(json.dumps(out))',
  ].join('\n');
  const cases=JSON.parse(execFileSync(python,['-B','-c',script],{cwd:root,encoding:'utf8',maxBuffer:20*1024*1024}));
  const report=[];
  for(const result of cases) {
    assert.equal(result.status,'generated');
    const midi=compareNative(result),mpe=compareMpe(result),old=oldSharedChannelMidi(result),calls=nativeCalls(result);
    const notes=calls.filter(e=>e.method==='addNote').map(e=>e.args);
    const bends=calls.filter(e=>e.method==='addNoteBend').map((e,index)=>({tick:e.args[1],key:e.args[3],value:Math.floor(e.args[4]),index})).sort((a,b)=>a.tick-b.tick||a.index-b.index);
    const q=value=>String(value).split('/').reduce((a,b)=>Number(a)/Number(b));
    const source=result.events.flatMap(event=>event.members.map(note=>({...note,start:q(note.onset_q??event.onset_q)})));
    let checked=0,oldMismatches=0;
    for(const n of notes) {
      const candidates=source.filter(s=>Math.abs(s.start*960-n[1])<1e-6&&s.pitch===n[3]);
      assert.equal(candidates.length,1,'Every sounding root must bind unambiguously to its physical string');
      const channel=candidates[0].string_number-1;
      const mpeNote=mpe.events.find(e=>e.kind===9&&e.tick===n[1]&&e.payload[0]===n[3]);
      assert(mpeNote);
      const sampleTicks=[...new Set([n[1],...bends.filter(b=>b.tick>=n[1]&&b.tick<n[1]+n[2]).map(b=>b.tick)])];
      for(const tick of sampleTicks) {
        const expected=bends.filter(b=>b.key===n[3]&&b.tick<=tick).at(-1)?.value??8192;
        assert.equal(wheelAt(midi,channel,tick),expected,`${result.request.artists}/${result.request.mode}, pitch ${n[3]}, tick ${tick}`);
        assert(Math.abs((wheelAt(mpe,mpeNote.channel,tick)-8192)*48/8192-(expected-8192)*16/8192)<=48/16384+1e-9,'MPE sounding pitch must match native within half a 14-bit step');
        if(wheelAt(old,0,tick)!==expected)oldMismatches++;
        checked++;
      }
    }
    report.push({artist:result.request.artists[0],mode:result.request.mode,notes:notes.length,pitchChecks:checked,oldMismatches});
  }
  assert.equal(cases.length,18);
  assert(report.reduce((sum,r)=>sum+r.oldMismatches,0)>0,'Actual examples must expose the previous exporter defect');
  t.diagnostic(JSON.stringify(report));
});

test('prebend preparation cannot bend a preceding different key and still precedes its own attack',{skip},()=>{
  for(const previousKey of [null,33,30]) {
    const events=[{onset_q:'1',members:[note(8,2,'1',{bend:{points:[{offset_fraction:'0',semitones:'1'},{offset_fraction:'1',semitones:'0'}]}})]}];
    if(previousKey!==null)events.unshift({onset_q:'0',members:[note(8,previousKey-28,'1')]});
    const midi=compareNative({tempo:120,duration_q:'4',events});
    assert.equal(wheelAt(midi,7,959),previousKey===33?8192:8704);
    assert.equal(wheelAt(midi,7,960),8704);
    const boundary=midi.events.filter(e=>e.channel===7&&e.tick===960);
    const attack=boundary.findIndex(e=>e.kind===9),setup=boundary.findLastIndex(e=>e.kind===14&&e.payload[0]+128*e.payload[1]===8704);
    assert(setup>=0&&setup<attack,'Prebend must be ready before the new note attack');
  }
});


function compareMpe(result) {
  const midi=parse(createRiffMpe(at,result)),standard=compareNative(result);
  assert.equal(midi.format,0);assert.equal(midi.tracks,1);assert.equal(midi.division,960);
  for(const kind of [8,9])assert.deepEqual(sorted(midi.events.filter(e=>e.kind===kind).map(e=>[e.tick,...e.payload])),
    sorted(standard.events.filter(e=>e.kind===kind).map(e=>[e.tick,...e.payload])));
  for(const type of [47,81,88])assert.deepEqual(midi.events.filter(e=>e.type===type).map(e=>[e.tick,...e.payload]),
    standard.events.filter(e=>e.type===type&&(type!==47||e.track===0)).map(e=>[e.tick,...e.payload]));
  const active=new Map();
  for(const event of midi.events) {
    if(event.kind===9) {
      assert(event.channel>=1&&event.channel<=8,'Notes must use member channels only, never manager or GM percussion');
      assert(!active.has(event.channel),'Each sounding voice needs its own member');
      active.set(event.channel,event.payload[0]);
    } else if(event.kind===8) {
      assert.equal(active.get(event.channel),event.payload[0],'Release precedes reuse and keeps the correct key');active.delete(event.channel);
    }
  }
  assert.equal(active.size,0);return midi;
}

function rpnMessages(midi) {
  const state=Array.from({length:16},()=>({msb:127,lsb:127})),messages=[];
  for(const event of midi.events.filter(e=>e.kind===11)) {
    const [controller,value]=event.payload,s=state[event.channel];
    if(controller===101)s.msb=value;
    if(controller===100)s.lsb=value;
    if(controller===6)messages.push({channel:event.channel,number:s.msb*128+s.lsb,value,tick:event.tick});
  }
  return messages;
}

test('MPE writes actual zone configuration, ranges and manager controls before note expression',{skip},()=>{
  const midi=compareMpe(fixture),rpn=rpnMessages(midi);
  assert.deepEqual(rpn.filter(e=>e.number===6),[{channel:15,number:6,value:0,tick:0},{channel:0,number:6,value:8,tick:0}]);
  assert.deepEqual(rpn.filter(e=>e.number===0),Array.from({length:9},(_,channel)=>({channel,number:0,value:channel?48:2,tick:0})));
  const firstNote=midi.events.findIndex(e=>e.kind===9);
  assert(midi.events.findLastIndex(e=>e.kind===11&&[6,38].includes(e.payload[0]))<firstNote);
  assert(midi.events.filter(e=>e.kind===12).every(e=>e.channel===0));
  assert(midi.events.filter(e=>e.kind===11&&[0,32,7,10,11].includes(e.payload[0])).every(e=>e.channel===0));
  assert.equal(wheelAt(midi,0,100000),8192,'No member expression on manager');
  assert.equal(riffMidiFilename(fixture,new Date('2026-11-07T01:02:03.004Z'),true),'drop-e-dorian-mpe-riff-2026-11-07T01-02-03-004Z.mid');
  assert.deepEqual(createRiffMpe(at,fixture),createRiffMpe(at,fixture));
});

test('MPE preserves opposing bends and concurrent unisons without inventing pressure or timbre',{skip},()=>{
  const input={tempo:120,duration_q:'4',events:[{onset_q:'0',members:[
    note(8,12,'4',{bend:bend(2)}),note(6,0,'2'),note(5,7,'4',{bend:bend(-1)})]}]};
  const before=structuredClone(input),native=nativeCalls(input),midi=compareMpe(input);
  const attacks=midi.events.filter(e=>e.kind===9);
  assert.equal(new Set(attacks.map(e=>e.channel)).size,3);
  const unisons=attacks.filter(e=>e.payload[0]===40);
  assert.equal(unisons.length,2);
  const positive=unisons.find(e=>wheelAt(midi,e.channel,960)>8192),plain=unisons.find(e=>wheelAt(midi,e.channel,960)===8192);
  assert(positive&&plain);assert(wheelAt(midi,attacks.find(e=>e.payload[0]===52).channel,960)<8192);
  assert(!midi.events.some(e=>e.kind===13||(e.kind===11&&e.payload[0]===74)));
  assert.deepEqual(input,before);assert.deepEqual(nativeCalls(input),native);
});

test('MPE reuses only released members, prefers matching keys and isolates early/late bends',{skip},()=>{
  const input={tempo:120,duration_q:'6',events:[
    {onset_q:'0',members:Array.from({length:8},(_,i)=>note(i+1,3,'1',{bend:bend(2)}))},
    {onset_q:'1',members:Array.from({length:8},(_,i)=>note(i+1,i===7?2:4,'1',i===7?{bend:{points:[{offset_fraction:'0',semitones:'1'},{offset_fraction:'1',semitones:'0'}]}}:{}))},
    {onset_q:'3',members:[note(8,2,'1')]},
  ]};
  const midi=compareMpe(input),first=midi.events.filter(e=>e.kind===9&&e.tick===0),second=midi.events.filter(e=>e.kind===9&&e.tick===960);
  assert.equal(first.length,8);assert.equal(second.length,8);
  for(const attack of second) {
    const expected=attack.payload[0]===30?Math.round(8192+512/3):8192;
    assert.equal(wheelAt(midi,attack.channel,960),expected,'Old endpoint curve must not affect reused member');
    const sequence=midi.events.filter(e=>e.tick===960&&e.channel===attack.channel);
    const off=sequence.findIndex(e=>e.kind===8),on=sequence.findIndex(e=>e.kind===9);
    const setup=sequence.findLastIndex(e=>e.kind===14);
    assert(off>=0&&off<setup&&setup<on,'Old release, new pitch, new attack order');
  }
  const prebend=second.find(e=>e.payload[0]===30);
  const prior=first.find(e=>e.channel===prebend.channel);
  assert(Math.abs((wheelAt(midi,prior.channel,959)-8192)*48/8192-nativeWheelAt(input,prior.payload[0],959)*16/8192+16)<.003);
  assert.equal(midi.events.find(e=>e.kind===9&&e.tick===2880).channel,prebend.channel,'Prefer released same-key member');
  assert.equal(wheelAt(midi,prebend.channel,2880),8192);
});

test('MPE allocates by voice instead of pinning a string to one member; preserves connected slide',{skip},()=>{
  const input={tempo:120,duration_q:'8',events:[
    {onset_q:'0',members:[note(8,3,'1')]},
    {onset_q:'1',members:[note(8,5,'1')]},
    {onset_q:'3',members:[note(5,7,'1/4',{slide:'legato'})]},
    {onset_q:'13/4',members:[note(5,9,'1/4',{slide:'legato'})]},
    {onset_q:'7/2',members:[note(5,7,'1/4')]},
  ]};
  const midi=compareMpe(input),attacks=midi.events.filter(e=>e.kind===9);
  assert.equal(attacks.length,3,'Legato chain stays one voice');
  assert.notEqual(attacks[0].channel,attacks[1].channel,'A new key prefers a longer-idle member');
  const slide=attacks[2];
  assert.equal(wheelAt(midi,slide.channel,3120),Math.round(8192+1024/3));
  assert.equal(midi.events.filter(e=>e.kind===8&&e.channel===slide.channel).length,1);
});


test('MPE terminal bend reaches its target before release, before a same-key reset or reuse',{skip},()=>{
  for(const nextFret of [null,3,5]) {
    const events=[{onset_q:'0',members:[note(8,3,'1',{bend:bend(2)})]}];
    if(nextFret!==null)events.push({onset_q:'1',members:[note(8,nextFret,'1')]});
    const input={tempo:120,duration_q:'4',events},midi=compareMpe(input);
    const first=midi.events.find(e=>e.kind===9),release=midi.events.findIndex(e=>e.kind===8&&e.channel===first.channel);
    const endpoint=midi.events.slice(0,release).findLast(e=>e.kind===14&&e.channel===first.channel);
    assert.equal(endpoint.tick,960);
    assert.equal(endpoint.payload[0]+128*endpoint.payload[1],Math.round(8192+1024/3),'Full two-semitone endpoint must precede Note Off');
    if(nextFret===3) {
      const next=midi.events.findIndex(e=>e.kind===9&&e.tick===960);
      const reset=midi.events.findIndex((e,i)=>i>release&&e.kind===14&&e.channel===first.channel);
      assert(reset>release&&reset<next);assert.equal(wheelAt(midi,first.channel,960),8192);
    }
  }
});


test('HTML distinguishes standard MIDI and MPE receiver setup',()=>{
  const html=readFileSync(new URL('../riff-builder.html',import.meta.url),'utf8');
  assert.match(html,/id="download-midi"[^>]*disabled/);assert.match(html,/id="download-mpe"[^>]*disabled/);
  assert.match(html,/MIDI Export: keep string tracks separate.*±16-semitone/);
  assert.match(html,/MPE Export: import into one MPE-enabled instrument.*manager channel 1.*members 2–9.*±48-semitone/);
});
