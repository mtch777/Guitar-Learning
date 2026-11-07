import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRiffMidi, riffMidiFilename} from '../src/riff-midi-export.js';
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
      if(status===255){const type=data[p++],size=vlq(),payload=[...data.subarray(p,p+size)];p+=size;events.push({tick,type,payload});}
      else {
        assert(status>=128&&status<240,`Nonstandard MIDI status ${status}`);
        const kind=status>>4,channel=status&15,size=[12,13].includes(kind)?1:2;
        const payload=[...data.subarray(p,p+size)];p+=size;
        assert(payload.every(x=>x<128));events.push({tick,kind,channel,payload});
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
  assert.equal(midi.format,0);assert.equal(midi.tracks,1);assert.equal(midi.division,960);
  const expected=calls.filter(c=>c.method==='addNote').map(c=>c.args);
  assert.deepEqual(sorted(midi.events.filter(e=>e.kind===9&&e.payload[1]>0).map(e=>[e.tick,e.payload[0],e.payload[1],e.channel])),
    sorted(expected.map(a=>[a[1],a[3],a[4],a[5]])));
  assert.deepEqual(sorted(midi.events.filter(e=>e.kind===8).map(e=>[e.tick,e.payload[0],e.channel])),
    sorted(expected.map(a=>[a[1]+a[2],a[3],a[5]])));
  assert.equal(midi.events.find(e=>e.type===47)?.tick,Number(result.duration_q)*960);
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

test('button exports accepted riff through repeats, preview changes and failed/new generation',{skip},async()=>{
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
    assert.equal(get('download-midi').disabled,true);
    get('download-midi').fire('click');assert.equal(downloads.length,0);
    const accepted={...structuredClone(fixture),status:'generated',phrases:[{offset_q:'0',length_q:'17/2',label:'Full riff',blocks:[]}]};
    get('generate').fire('click');assert.equal(get('download-midi').disabled,true);
    await worker.onmessage({data:{id:worker.last.id,type:'result',result:accepted}});
    assert.equal(get('download-midi').disabled,false);
    get('download-midi').fire('click');
    const bytes=Buffer.from(await downloads[0].blob.arrayBuffer());
    assert.equal(downloads[0].blob.type,'audio/midi');assert.match(downloads[0].name,/^drop-e-dorian-riff-.*\.mid$/);
    assert.deepEqual(bytes,Buffer.from(createRiffMidi(at,accepted)));
    assert.equal(body.children.length,0,'Temporary download anchor removed');
    const half=new Element('button');half.dataset.speed='0.5';get('speeds').append(half);
    get('speeds').fire('click',{target:{closest:()=>half}});
    get('seek').value='6';get('seek').fire('input');
    get('section-playback').children[0].fire('click');
    get('download-midi').fire('click');
    assert.equal(api.playbackSpeed,.5);assert.deepEqual(Buffer.from(await downloads[1].blob.arrayBuffer()),bytes);
    get('generate').fire('click');get('download-midi').fire('click');
    assert.equal(downloads.length,2,'Busy handler guard prevents exporting even if invoked directly');
    await worker.onmessage({data:{id:worker.last.id,type:'result',result:{status:'no_choice',message:'No choice'}}});
    assert.equal(get('download-midi').disabled,false);
    get('download-midi').fire('click');assert.deepEqual(Buffer.from(await downloads[2].blob.arrayBuffer()),bytes);
    get('generate').fire('click');const newer=structuredClone(accepted);newer.tempo=120;
    await worker.onmessage({data:{id:worker.last.id,type:'result',result:newer}});
    get('download-midi').fire('click');assert.notDeepEqual(Buffer.from(await downloads[3].blob.arrayBuffer()),bytes);
    // Export failures do not destroy or disable the accepted riff.
    URL.createObjectURL=()=>{throw new Error('Download unavailable');};
    get('download-midi').fire('click');assert.match(get('status').textContent,/MIDI export failed: Download unavailable/);
    assert.equal(get('download-midi').disabled,false);assert.equal(body.children.length,0);
    for(const timer of timers.values())if(timer.ms===1000)timer.fn();
    assert.equal(blobs.size,0,'Every created object URL is released');
  } finally {
    for(const [key,value] of Object.entries(old)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}
    URL.createObjectURL=oldCreate;URL.revokeObjectURL=oldRevoke;
  }
});
