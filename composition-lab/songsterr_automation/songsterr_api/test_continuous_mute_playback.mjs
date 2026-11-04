import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {registerContinuousMutePlayback,unregisterContinuousMutePlayback} from './continuous_mute_playback.mjs';
const modulePath=process.env.ALPHATAB_MODULE||'.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
assert.ok(fs.existsSync(modulePath),'Native alphaTab is required; do not report skipped native tests as passes');
const at=await import(pathToFileURL(path.resolve(modulePath)));
const serialized=s=>at.model.JsonConverter.scoreToJson(s);

function fixture({kind='tie',muted=true,ghost=false,bend=false,bendAt=0,tempo=120,coattack=false,crossBar=false}={}){
 const score=new at.model.Score(),master=new at.model.MasterBar();
 if(crossBar)master.timeSignatureNumerator=2;
 master.tempoAutomations.push(at.model.Automation.buildTempoAutomation(false,0,tempo,2));score.addMasterBar(master);
 const track=new at.model.Track();score.addTrack(track);track.playbackInfo.program=25;
 const staff=new at.model.Staff();track.addStaff(staff);staff.stringTuning.tunings=[64,59,55,50,45,40];
 let bar=new at.model.Bar();staff.addBar(bar);let voice=new at.model.Voice();bar.addVoice(voice);const notes=[];
 for(let i=0;i<4;i++){
  if(crossBar&&i===2){const m=new at.model.MasterBar();m.timeSignatureNumerator=2;score.addMasterBar(m);bar=new at.model.Bar();staff.addBar(bar);voice=new at.model.Voice();bar.addVoice(voice);}
  const beat=new at.model.Beat();beat.duration=at.model.Duration.Quarter;voice.addBeat(beat);
  const note=new at.model.Note();note.string=6;note.fret=kind==='legato'?[0,2,5,7][i]:0;
  note.isPalmMute=muted;note.isGhost=ghost;note.dynamics=at.model.DynamicValue.MF;
  if(kind==='tie'&&(i===1||i===2))note.isTieDestination=true;
  if(kind==='legato'&&i<2)note.slideOutType=at.model.SlideOutType.Legato;
  beat.addNote(note);notes.push(note);
  if(coattack){const other=new at.model.Note();other.string=5;other.fret=3;other.isPalmMute=muted;beat.addNote(other);}
 }
 const settings=new at.Settings();settings.notation.notationMode=at.NotationMode.GuitarPro;score.finish(settings);
 if(bend){const note=notes[bendAt];note.addBendPoint(new at.model.BendPoint(0,0));note.addBendPoint(new at.model.BendPoint(60,4));note.bendType=at.model.BendType.Custom;note.bendStyle=at.model.BendStyle.Default;}
 return{score,notes,settings};
}
function generate(f){
 const file=new at.midi.MidiFile(),handler=new at.midi.AlphaSynthMidiFileHandler(file,false),calls=[];
 const add=handler.addNote.bind(handler);let current=null;
 handler.addNote=(track,start,length,key,velocity,channel)=>{calls.push({id:current?.id,track,start,length,key,velocity,channel});return add(track,start,length,key,velocity,channel);};
 const generator=new at.midi.MidiFileGenerator(f.score,f.settings,handler),note=generator._generateNote;
 generator._generateNote=function(n,...args){const prior=current;current=n;try{return note.call(this,n,...args);}finally{current=prior;}};
 generator.generate();return{calls,events:file.events.map(e=>({kind:e.constructor.name,...JSON.parse(JSON.stringify(e))}))};
}
const call=(result,note)=>result.calls.find(c=>c.id===note.id);
const curves=result=>result.events.filter(e=>e.kind.includes('Bend')).map(({kind,tick,noteKey,value})=>({kind,tick,noteKey,value}));

for(const kind of ['tie','legato'])test(`fully muted ${kind} preserves one attack, all targets and terminal release`,()=>{
 const f=fixture({kind}),before=serialized(f.score),native=generate(f);
 assert.equal(call(native,f.notes[0]).length,160,'Retain native truncation counterexample');
 assert.equal(native.calls.length,2);
 const receipt=registerContinuousMutePlayback(at,f.score),actual=generate(f);
 assert.equal(receipt.continuous_gestures,1);assert.equal(receipt.interior_notes,2);
 assert.equal(call(actual,f.notes[0]).length,2*960+160);
 assert.equal(actual.calls.length,2,'No attacks invented for destinations');
 assert.equal(call(actual,f.notes[3]).length,160,'Isolated mute unchanged');
 for(let i=0;i<actual.calls.length;i++)assert.deepEqual({...actual.calls[i],length:native.calls[i].length},native.calls[i]);
 assert.equal(serialized(f.score),before,'No model or notation mutation');
 assert.equal(unregisterContinuousMutePlayback(at,f.score),true);
 assert.deepEqual(generate(f),native,'Removing registration restores original behavior');
});

test('legato pitch transitions retain the unmuted source clock, not the early local cap',()=>{
 const source=fixture({kind:'legato',muted:false}),expected=curves(generate(source));
 const f=fixture({kind:'legato'}),incorrect=curves(generate(f));assert.notDeepEqual(incorrect,expected);
 registerContinuousMutePlayback(at,f.score);assert.deepEqual(curves(generate(f)),expected);
 const times=expected.map(e=>e.tick);assert.ok(times.includes(960));assert.ok(times.includes(1920));
});

test('mixed mute chains refuse atomically and retain native input exactly',()=>{
 for(const index of[0,1,2]){
  const f=fixture();f.notes[index].isPalmMute=false;const before=serialized(f.score),native=generate(f);
  assert.throws(()=>registerContinuousMutePlayback(at,f.score),/mixed mute/);
  assert.equal(serialized(f.score),before);assert.deepEqual(generate(f),native);
 }
});

test('unmuted chains and all isolated notes remain byte-identical in native events',()=>{
 for(const opts of[{muted:false},{kind:'none'},{kind:'none',muted:false}]){
  const f=fixture(opts),native=generate(f),receipt=registerContinuousMutePlayback(at,f.score);
  assert.equal(receipt.continuous_gestures,0);assert.deepEqual(generate(f),native);
 }
});

test('registered policy does not leak into a second score or a saved/reloaded score',()=>{
 const f=fixture(),other=fixture(),before=generate(other);registerContinuousMutePlayback(at,f.score);
 assert.deepEqual(generate(other),before);assert.equal(call(generate(f),f.notes[0]).length,2080);
 const data=new at.exporter.Gp7Exporter().export(other.score,other.settings);
 const loaded=at.importer.ScoreLoader.loadScoreFromBytes(data,other.settings);
 const notes=loaded.tracks[0].staves[0].bars[0].voices[0].beats.map(b=>b.notes[0]);
 const reloaded={score:loaded,settings:other.settings,notes};assert.equal(call(generate(reloaded),notes[0]).length,160);
 registerContinuousMutePlayback(at,loaded);assert.equal(call(generate(reloaded),notes[0]).length,2080);
});

test('ghost velocity, bend shape and isolated coattack members survive the policy',()=>{
 const f=fixture({ghost:true,bend:true,bendAt:3,coattack:true}),before=serialized(f.score),native=generate(f);
 registerContinuousMutePlayback(at,f.score);const actual=generate(f);
 assert.equal(actual.calls.length,native.calls.length);assert.deepEqual(actual.calls.map(c=>[c.key,c.velocity,c.channel]),native.calls.map(c=>[c.key,c.velocity,c.channel]));
 assert.deepEqual(curves(actual),curves(native),'Supported isolated bend timing and values remain exactly native');
 for(const row of actual.calls)if(row.id!==f.notes[0].id)assert.equal(row.length,160);
 assert.equal(serialized(f.score),before);
});

test('native terminal cap follows tempo without changing interior written clocks',()=>{
 for(const tempo of[60,90,180]){
  const f=fixture({tempo});registerContinuousMutePlayback(at,f.score);
  assert.equal(call(generate(f),f.notes[0]).length,1920+Math.floor(tempo*80/60));
 }
});

test('ambiguous, dangling, cyclic or conflicting execution refuses without mutation',()=>{
 for(const change of[
  f=>{f.notes[0].slideOutType=at.model.SlideOutType.Legato;f.notes[0].slideTarget=f.notes[1];},
  f=>{f.notes[1].tieOrigin=null;},
  f=>{f.notes[2].tieDestination=f.notes[0];f.notes[0].tieOrigin=f.notes[2];f.notes[0].isTieDestination=true;},
  f=>{f.notes[1].isDead=true;},
  f=>{f.notes[1].isStaccato=true;},
  f=>{f.notes[1].beat.graceType=at.model.GraceType.BeforeBeat;}
 ]){const f=fixture();change(f);const before=serialized(f.score);assert.throws(()=>registerContinuousMutePlayback(at,f.score));assert.equal(serialized(f.score),before);}
});

test('post-registration timing, pitch, mute and target edits require explicit re-registration',()=>{
 for(const change of[f=>f.notes[2].isPalmMute=false,f=>f.notes[1].fret++,f=>f.notes[1].tieOrigin=null,f=>f.notes[2].beat.playbackDuration=480]){
  const f=fixture();registerContinuousMutePlayback(at,f.score);change(f);
  assert.throws(()=>generate(f),/registered continuation changed/);
 }
});

test('repeated registration is idempotent and does not add events or nested overrides',()=>{
 const f=fixture();const first=registerContinuousMutePlayback(at,f.score);const expected=generate(f);
 assert.deepEqual(registerContinuousMutePlayback(at,f.score),first);assert.deepEqual(generate(f),expected);
});


test('tied bend rescaling counterexample refuses under native extension setting without replacing registration',()=>{
 const f=fixture();const receipt=registerContinuousMutePlayback(at,f.score);
 const n=f.notes[0];n.addBendPoint(new at.model.BendPoint(0,0));n.addBendPoint(new at.model.BendPoint(60,4));n.bendType=at.model.BendType.Custom;
 const before=serialized(f.score);
 assert.throws(()=>registerContinuousMutePlayback(at,f.score,f.settings),/tied bend with extendBendArrowsOnTiedNotes/);
 assert.equal(serialized(f.score),before);assert.equal(f.settings.notation.extendBendArrowsOnTiedNotes,true);
 assert.throws(()=>generate(f),/registered continuation changed/,'Failed registration cannot overwrite the prior guarded state');
 assert.equal(unregisterContinuousMutePlayback(at,f.score),true);assert.equal(receipt.continuous_gestures,1);
});

test('explicit fixed bend clock remains supported without altering generator settings',()=>{
 const source=fixture({muted:false,bend:true});source.settings.notation.extendBendArrowsOnTiedNotes=false;
 const expected=curves(generate(source));const f=fixture({bend:true});f.settings.notation.extendBendArrowsOnTiedNotes=false;
 registerContinuousMutePlayback(at,f.score,f.settings);assert.deepEqual(curves(generate(f)),expected);
 f.settings.notation.extendBendArrowsOnTiedNotes=true;
 assert.throws(()=>generate(f),/bend clock setting changed/);
});

for(const kind of['tie-then-legato','legato-then-tie'])test(`${kind} retains one attack and both transition relationships`,()=>{
 function make(muted){
  const f=fixture({kind:'none',muted});
  if(kind==='tie-then-legato'){
   f.notes[1].isTieDestination=true;f.notes[1].slideOutType=at.model.SlideOutType.Legato;f.notes[2].fret=5;
  }else{
   f.notes[0].slideOutType=at.model.SlideOutType.Legato;f.notes[1].fret=5;f.notes[2].fret=5;f.notes[2].isTieDestination=true;
  }
  f.score.finish(f.settings);return f;
 }
 const source=make(false),f=make(true),before=serialized(f.score);
 registerContinuousMutePlayback(at,f.score,f.settings);const actual=generate(f);
 assert.equal(actual.calls.length,2);assert.equal(call(actual,f.notes[0]).length,2080);
 assert.deepEqual(curves(actual),curves(generate(source)));assert.equal(serialized(f.score),before);
});


test('a newly muted chain after registration cannot silently fall through native truncation',()=>{
 const f=fixture({muted:false});registerContinuousMutePlayback(at,f.score);
 for(const note of f.notes)note.isPalmMute=true;
 assert.throws(()=>generate(f),/unregistered muted continuation/);
 registerContinuousMutePlayback(at,f.score);assert.equal(call(generate(f),f.notes[0]).length,2080);
});


for(const kind of['tie','legato'])test(`continuous ${kind} crosses a bar without changing voice identity or timing`,()=>{
 const f=fixture({kind,crossBar:true}),before=serialized(f.score);
 assert.notEqual(f.notes[1].beat.voice,f.notes[2].beat.voice,'Native voices are separate objects per bar');
 registerContinuousMutePlayback(at,f.score);const actual=generate(f);
 assert.equal(actual.calls.length,2);assert.equal(call(actual,f.notes[0]).length,2080);
 assert.equal(serialized(f.score),before);
});


for(const kind of['tie','legato'])test(`${kind} crossing a tempo step caps terminal release at terminal BPM`,()=>{
 const f=fixture({kind,crossBar:true,tempo:120});
 f.score.masterBars[1].tempoAutomations.push(at.model.Automation.buildTempoAutomation(false,0,180,2));
 f.score.finish(f.settings);const before=serialized(f.score);
 registerContinuousMutePlayback(at,f.score,f.settings);const actual=generate(f),root=call(actual,f.notes[0]);
 assert.equal(root.start,0);assert.equal(root.length,2*960+Math.floor(180*80/60));
 assert.notEqual(root.length,2*960+Math.floor(120*80/60),'Origin BPM cannot supply the terminal cap');
 assert.equal(call(actual,f.notes[3]).length,240);assert.equal(actual.calls.length,2);
 assert.equal(serialized(f.score),before);
});

test('an in-bar tempo step before terminal onset determines release, while later tempo edits require registration',()=>{
 const f=fixture({tempo:120});
 f.score.masterBars[0].tempoAutomations.push(at.model.Automation.buildTempoAutomation(false,0.5,90,2));
 f.score.finish(f.settings);registerContinuousMutePlayback(at,f.score,f.settings);
 assert.equal(call(generate(f),f.notes[0]).length,1920+120);
 f.score.masterBars[0].tempoAutomations[1].value=150;
 assert.throws(()=>generate(f),/tempo context changed/);
 registerContinuousMutePlayback(at,f.score,f.settings);assert.equal(call(generate(f),f.notes[0]).length,1920+200);
});

test('unmodelled tempo ramps and repeated traversal across a gesture refuse atomically',()=>{
 for(const change of[
  f=>f.score.masterBars[1].tempoAutomations.push(at.model.Automation.buildTempoAutomation(true,0,180,2)),
  f=>f.score.masterBars[0].repeatCount=2,
 ]){
  const f=fixture({crossBar:true});change(f);const before=serialized(f.score);
  assert.throws(()=>registerContinuousMutePlayback(at,f.score,f.settings),/tempo ramp|repeated or redirected/);
  assert.equal(serialized(f.score),before);
 }
});


test('runtime swing cannot silently alter the registered written continuation clock',()=>{
 const f=fixture();f.score.masterBars[0].timeSignatureNumerator=2;
 f.score.masterBars[0].tripletFeel=at.model.TripletFeel.Triplet8th;
 for(const note of f.notes)note.beat.duration=at.model.Duration.Eighth;
 f.score.finish(f.settings);const before=serialized(f.score);
 assert.equal(f.notes[0].beat.playbackDuration,480);
 registerContinuousMutePlayback(at,f.score,f.settings);
 assert.throws(()=>generate(f),/runtime beat duration differs from registered written clock/);
 assert.equal(serialized(f.score),before);
});
