import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {restoreSourcePercussion} from './restore_source_percussion.mjs';
import {checkSourcePercussion} from './check_source_percussion.mjs';
const modulePath=process.env.ALPHATAB_MODULE||'.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
const at=fs.existsSync(modulePath)?await import(pathToFileURL(path.resolve(modulePath))):null;
const json=score=>at.model.JsonConverter.scoreToJson(score);
function fixture(mode='onBeat') {
  const score=new at.model.Score(),track=new at.model.Track(),staff=new at.model.Staff();score.addMasterBar(new at.model.MasterBar());score.addTrack(track);track.addStaff(staff);staff.isPercussion=true;track.playbackInfo.primaryChannel=9;track.playbackInfo.secondaryChannel=9;
  const bar=new at.model.Bar(),voice=new at.model.Voice();staff.addBar(bar);bar.addVoice(voice);
  const rows=mode?[{duration:[1,4],notes:[{rest:true}]},{duration:[1,128],graceNote:mode,notes:[{fret:38,string:1.5},{fret:44,string:4.5}]},{duration:[1,4],notes:[{fret:38,string:1.5}]},{duration:[1,2],notes:[{fret:36,string:5.5},{fret:44,string:4.5}]}]:[{duration:[1,4],notes:[{fret:36,string:5.5}]},{duration:[1,4],notes:[{fret:38,string:1.5}]},{duration:[1,2],notes:[{fret:44,string:4.5}]}];
  for(const row of rows){const b=new at.model.Beat();voice.addBeat(b);b.duration=row.graceNote?4:row.duration[1];for(const raw of row.notes){if(raw.rest)continue;const n=new at.model.Note();n.percussionArticulation=raw.fret;b.addNote(n);}}
  const parts=[{partId:0,instrumentId:1024,measures:[{voices:[{beats:rows}]}]}],settings=new at.Settings();settings.notation.notationMode=at.NotationMode.GuitarPro;score.finish(settings);
  return{score,track,staff,voice,parts,settings,rows};
}
function roundtrip(f){return at.importer.ScoreLoader.loadScoreFromBytes(new at.exporter.Gp7Exporter().export(f.score,f.settings),f.settings);}
function midi(score,settings){
  const file=new at.midi.MidiFile(),handler=new at.midi.AlphaSynthMidiFileHandler(file,false),calls=[];
  const add=handler.addNote.bind(handler);handler.addNote=(track,start,length,key,velocity,channel)=>{calls.push({track,start,length,key,velocity,channel});return add(track,start,length,key,velocity,channel);};
  new at.midi.MidiFileGenerator(score,settings,handler).generate();return{events:JSON.parse(JSON.stringify(file.events)),calls};
}
function doubleDotFixture() {
  const f=fixture(null);
  const rows=[
    [{type:4,dots:1,duration:[3,8],notes:[{fret:38,string:1.5}]},{type:8,duration:[1,8],notes:[{fret:44,string:4.5}]},{type:16,duration:[1,16],notes:[{fret:38,string:1.5}]},{type:4,dots:2,duration:[7,16],notes:[{fret:36,string:5.5}]}],
    [{type:2,duration:[1,2],notes:[{fret:36,string:5.5}]},{type:4,dots:1,duration:[3,8],notes:[{fret:38,string:1.5}]},{type:16,duration:[1,16],notes:[{fret:44,string:4.5}]},{type:32,dots:2,duration:[7,128],notes:[{rest:true}]},{type:128,duration:[1,128],notes:[{fret:36,string:5.5}]}]
  ];
  f.score.addMasterBar(new at.model.MasterBar());
  const bar=new at.model.Bar(),voice=new at.model.Voice();f.staff.addBar(bar);bar.addVoice(voice);
  for(const[mi,source]of rows.entries()){
    const v=f.staff.bars[mi].voices[0];v.beats=[];
    for(const row of source){const b=new at.model.Beat();v.addBeat(b);b.duration=row.type;b.dots=row.dots?1:0;
      for(const raw of row.notes){if(raw.rest)continue;const n=new at.model.Note();n.percussionArticulation=raw.fret;b.addNote(n);}}
  }
  f.parts[0].measures=rows.map(beats=>({voices:[{beats}]}));f.doubleDotRows=rows;f.score.finish(f.settings);return f;
}

test('GP5 double-dot loss restores source drum hits and rests with exact native notation and MIDI starts',{skip:!at},()=>{
  const f=doubleDotFixture(),source=structuredClone(f.parts),beats=f.staff.bars.flatMap(b=>b.voices[0].beats);
  const occurrences=beats.map(b=>b.notes.map(n=>n.id)),clocks=beats.map(b=>[b.displayStart,b.displayDuration,b.playbackStart,b.playbackDuration]);
  assert.equal(checkSourcePercussion(f.score,f.parts).status,'FAIL_INDEPENDENT_SOURCE_PERCUSSION');
  const report=restoreSourcePercussion(f.score,f.parts,at);assert.equal(report.restoredDoubleDots,2);assert.equal(report.witnesses.filter(w=>w.restored_double_dot).length,2);
  assert.deepEqual(f.parts,source);assert.deepEqual(beats.map(b=>b.notes.map(n=>n.id)),occurrences);
  assert.deepEqual(beats.map(b=>[b.displayStart,b.displayDuration,b.playbackStart,b.playbackDuration]),clocks,'restoration queues notation only; finish owns clock consequences');
  f.score.finish(f.settings);const actual=roundtrip(f);assert.equal(checkSourcePercussion(actual,f.parts).status,'PASS_INDEPENDENT_SOURCE_PERCUSSION');
  const bars=actual.tracks[0].staves[0].bars;
  assert.deepEqual([bars[0].voices[0].beats[3].duration,bars[0].voices[0].beats[3].dots,bars[0].voices[0].beats[3].displayDuration],[4,2,1680]);
  assert.deepEqual([bars[1].voices[0].beats[3].duration,bars[1].voices[0].beats[3].dots,bars[1].voices[0].beats[3].displayDuration],[32,2,210]);
  assert.deepEqual(midi(actual,f.settings).calls.map(c=>[c.key,c.start]),[[38,0],[44,1440],[38,1920],[36,2160],[36,3840],[38,5760],[44,7200],[36,7650]]);
  const saved=json(actual);assert.equal(restoreSourcePercussion(actual,f.parts,at).restoredDoubleDots,0);assert.equal(json(actual),saved);
});

test('double-dot recovery refuses false signatures and later bad members without partial notation writes',{skip:!at},()=>{
  for(const mutate of [
    f=>f.doubleDotRows[0][3].duration=[1,2],
    f=>f.doubleDotRows[0][3].type=8,
    f=>delete f.doubleDotRows[0][3].dots,
    f=>f.staff.bars[0].voices[0].beats[3].dots=0,
    f=>f.staff.bars[1].voices[0].beats[4].notes[0].percussionArticulation=37
  ]){
    const f=doubleDotFixture();mutate(f);const before=json(f.score),source=structuredClone(f.parts);
    assert.throws(()=>restoreSourcePercussion(f.score,f.parts,at));assert.equal(json(f.score),before);assert.deepEqual(f.parts,source);
  }
  const f=doubleDotFixture();restoreSourcePercussion(f.score,f.parts,at);f.score.finish(f.settings);
  const actual=roundtrip(f);actual.tracks[0].staves[0].bars[0].voices[0].beats[3].dots=1;const before=json(actual);
  assert.throws(()=>restoreSourcePercussion(actual,f.parts,at),/duration\/identity mismatch/);assert.equal(json(actual),before,'native corruption must not be mistaken for the GP5 bridge signature');
});

test('legacy two-member fallback loses grace time and ordinary GM keys on actual GP7 roundtrip',{skip:!at},()=>{
  const f=fixture(),actual=roundtrip(f),check=checkSourcePercussion(actual,f.parts),keys=midi(actual,f.settings).calls.map(c=>c.key);
  assert.equal(check.status,'FAIL_INDEPENDENT_SOURCE_PERCUSSION');assert(check.differences.some(x=>x.code==='GRACE_MODE'));assert(check.differences.some(x=>x.code==='GM_KEY_MEMBERSHIP'));assert(keys.includes(61));assert(keys.includes(64));assert(keys.includes(60));
});
for(const mode of ['onBeat','beforeBeat'])test(`complete two-member ${mode} grace before one-note host survives GP7 and actual MIDI`,{skip:!at},()=>{
  const f=fixture(mode),source=structuredClone(f.parts),clocks=f.voice.beats.map(b=>[b.displayStart,b.displayDuration,b.playbackStart,b.playbackDuration]);
  const r=restoreSourcePercussion(f.score,f.parts,at);assert.equal(r.restoredGraceTypes,1);assert.equal(r.graceBeats,1);assert.equal(r.notesChecked,5);assert.equal(r.tables[0].canonical_default_required,true);
  assert.deepEqual(f.parts,source);assert.deepEqual(f.voice.beats.map(b=>[b.displayStart,b.displayDuration,b.playbackStart,b.playbackDuration]),clocks,'restorer must not write clocks');
  f.score.finish(f.settings);assert.equal(checkSourcePercussion(f.score,f.parts).status,'PASS_INDEPENDENT_SOURCE_PERCUSSION');
  const before=midi(f.score,f.settings),actual=roundtrip(f),after=midi(actual,f.settings);assert.equal(checkSourcePercussion(actual,f.parts).status,'PASS_INDEPENDENT_SOURCE_PERCUSSION');assert.deepEqual(after.events,before.events);
  assert.deepEqual(after.calls.map(c=>c.key),[38,44,38,36,44]);assert(after.calls.every(c=>c.length>0));
  const v=actual.tracks[0].staves[0].bars[0].voices[0];assert.equal(v.beats[1].displayDuration,0);assert.equal(v.beats[2].displayStart,960);assert.equal(v.beats[2].displayDuration,960);assert.equal(v.beats[3].displayStart,1920);
  const prior=json(actual),again=restoreSourcePercussion(actual,f.parts,at);assert.equal(again.remappedArticulations,0);assert.equal(again.restoredGraceTypes,0);assert.equal(again.tables[0].canonical_default_required,false);assert.equal(json(actual),prior);
});
test('ordinary source GM36/38/44 retain complete MIDI and native metadata',{skip:!at},()=>{
  const f=fixture(null),before=midi(f.score,f.settings),original=JSON.parse(json(f.score));restoreSourcePercussion(f.score,f.parts,at);
  const after=JSON.parse(json(f.score));after.tracks[0].percussionarticulations=original.tracks[0].percussionarticulations;
  for(let i=0;i<3;i++)after.tracks[0].staves[0].bars[0].voices[0].beats[i].notes[0].percussionarticulation=original.tracks[0].staves[0].bars[0].voices[0].beats[i].notes[0].percussionarticulation;
  assert.deepEqual(after,original,'Only articulation table/index representation may change');f.score.finish(f.settings);
  const actual=roundtrip(f);assert.equal(checkSourcePercussion(actual,f.parts).status,'PASS_INDEPENDENT_SOURCE_PERCUSSION');assert.deepEqual(midi(actual,f.settings).events,before.events);
});
test('source articulation ID30 stays ID30 with the native declared output49',{skip:!at},()=>{
  const f=fixture(null);f.rows[0].notes[0].fret=30;f.rows[0].notes[0].string=-1.5;f.voice.beats[0].notes[0].percussionArticulation=30;
  const original=midi(f.score,f.settings);assert.equal(original.calls[0].key,49);restoreSourcePercussion(f.score,f.parts,at);f.score.finish(f.settings);
  const actual=roundtrip(f),note=actual.tracks[0].staves[0].bars[0].voices[0].beats[0].notes[0];assert.equal(actual.tracks[0].percussionArticulations[note.percussionArticulation].id,30);assert.equal(checkSourcePercussion(actual,f.parts).status,'PASS_INDEPENDENT_SOURCE_PERCUSSION');assert.deepEqual(midi(actual,f.settings).events,original.events);
});
test('known existing notation choice remains, including alternate articulation with the same GM output',{skip:!at},()=>{
  const f=fixture(null);restoreSourcePercussion(f.score,f.parts,at);const note=f.voice.beats[1].notes[0],table=f.track.percussionArticulations;
  const alternatives=table.flatMap((a,i)=>a.outputMidiNumber===38?[i]:[]);assert(alternatives.length>1);note.percussionArticulation=alternatives.at(-1);
  const prior=json(f.score),report=restoreSourcePercussion(f.score,f.parts,at);assert.equal(report.remappedArticulations,0);assert.equal(json(f.score),prior);
});
function duplicateFixture(){
  const f=fixture(null),raw={fret:87,string:5,accentuated:2};f.rows[0].notes=[{...raw},{...raw}];
  const n=f.voice.beats[0].notes[0];n.percussionArticulation=87;n.accentuated=2;
  const other=new at.model.Note();other.percussionArticulation=87;other.accentuated=2;f.voice.beats[0].addNote(other);return f;
}
test('identical simultaneous percussion occurrences retain multiplicity, native identities and order',{skip:!at},()=>{
  const f=duplicateFixture(),members=[...f.voice.beats[0].notes],ids=members.map(n=>n.id),source=structuredClone(f.parts);
  restoreSourcePercussion(f.score,f.parts,at);assert.deepEqual(f.voice.beats[0].notes,members);assert.deepEqual(members.map(n=>n.id),ids);assert.deepEqual(f.parts,source);
  f.score.finish(f.settings);const actual=roundtrip(f);assert.equal(checkSourcePercussion(actual,f.parts).status,'PASS_INDEPENDENT_SOURCE_PERCUSSION');assert.deepEqual(midi(actual,f.settings).calls.map(c=>c.key),[87,87,38,44]);
});
test('missing/extra duplicate and differing duplicate source/native flags refuse atomically',{skip:!at},()=>{
  for(const mutate of [f=>f.voice.beats[0].notes.pop(),f=>f.rows[0].notes.push({...f.rows[0].notes[0]}),f=>f.rows[0].notes[1].ghost=true,f=>f.voice.beats[0].notes[1].isGhost=true,f=>f.rows[0].notes[1].accentuated=1]){
    const f=duplicateFixture();mutate(f);const before=json(f.score),source=structuredClone(f.parts);assert.throws(()=>restoreSourcePercussion(f.score,f.parts,at));assert.equal(json(f.score),before);assert.deepEqual(f.parts,source);
  }
  const f=duplicateFixture();restoreSourcePercussion(f.score,f.parts,at);f.score.finish(f.settings);f.rows[0].notes[1].ghost=true;assert.equal(checkSourcePercussion(f.score,f.parts).status,'FAIL_INDEPENDENT_SOURCE_PERCUSSION');
});
test('attached grace fret key is restored only when its table candidate is unique',{skip:!at},()=>{
  const f=fixture();f.rows[1].notes=[{fret:44,string:4.5}];f.voice.beats[1].notes.splice(1,1);const note=f.voice.beats[1].notes[0];note.percussionArticulation=-1;note.fret=44;note.string=5;f.voice.beats[1].graceType=1;
  const r=restoreSourcePercussion(f.score,f.parts,at);assert.equal(r.restoredAttachedGraceKeys,1);assert.equal(note.fret,-1);assert.equal(note.string,-1);f.score.finish(f.settings);assert.equal(checkSourcePercussion(roundtrip(f),f.parts).status,'PASS_INDEPENDENT_SOURCE_PERCUSSION');
});
test('corrupt later member, duplicate key, orphan/mixed grace, bad duration and unsupported key refuse atomically',{skip:!at},()=>{
  for(const mutate of [f=>f.rows[3].notes[0].fret=37,f=>f.rows[1].notes[1].fret=38,f=>f.rows[3].graceNote='onBeat',f=>f.rows[2].graceNote='beforeBeat',f=>f.rows[3].duration=[1,4],f=>f.rows[1].graceNote='afterBeat',f=>{f.rows[3].notes[0].fret=999;f.voice.beats[3].notes[0].percussionArticulation=999;},f=>f.voice.beats[3].notes.pop()]){
    const f=fixture();mutate(f);const before=json(f.score),source=structuredClone(f.parts);assert.throws(()=>restoreSourcePercussion(f.score,f.parts,at));assert.equal(json(f.score),before);assert.deepEqual(f.parts,source);
  }
});
test('ambiguous existing-table attached grace refuses without choosing a notation',{skip:!at},()=>{
  const f=fixture();restoreSourcePercussion(f.score,f.parts,at);const note=f.voice.beats[1].notes[0];note.percussionArticulation=-1;note.fret=38;note.string=2;const before=json(f.score);
  assert.throws(()=>restoreSourcePercussion(f.score,f.parts,at),/Ambiguous percussion articulation/);assert.equal(json(f.score),before);
});
test('independent source checker catches corrupt exported mode, key, index and regular timing without mutation',{skip:!at},()=>{
  for(const mutate of [f=>f.voice.beats[1].graceType=0,f=>f.voice.beats[1].notes[0].percussionArticulation=999,f=>f.voice.beats[2].notes[0].percussionArticulation=f.voice.beats[3].notes[0].percussionArticulation,f=>f.voice.beats[2].displayStart++,f=>f.voice.beats[2].duration=8,f=>f.voice.beats[2].duration=NaN,f=>f.voice.beats[2].dots=Infinity,f=>f.voice.beats[2].tupletNumerator=0]){
    const f=fixture();restoreSourcePercussion(f.score,f.parts,at);f.score.finish(f.settings);mutate(f);const before=json(f.score);assert.equal(checkSourcePercussion(f.score,f.parts).status,'FAIL_INDEPENDENT_SOURCE_PERCUSSION');assert.equal(json(f.score),before);
  }
});
test('pitched-only scores remain untouched',{skip:!at},()=>{
  const f=fixture(null);f.parts[0].instrumentId=27;f.staff.isPercussion=false;const before=json(f.score);const r=restoreSourcePercussion(f.score,f.parts,at);assert.equal(r.notesChecked,0);assert.equal(json(f.score),before);
});
test('explicit percussion option refuses an existing cached passing report without changing files',{skip:!at},()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'source-percussion-')),folder=path.join(root,'source');fs.mkdirSync(folder);
  const files={'capture.json':JSON.stringify({capture_complete:true,song_id:1}),'score.gp':'retained GP sentinel','gp7-validation.json':JSON.stringify({roundtripPass:true})};
  try{
    for(const[name,data]of Object.entries(files))fs.writeFileSync(path.join(folder,name),data);
    const cli=new URL('./export_csv_gp7.mjs',import.meta.url);
    const result=spawnSync(process.execPath,[fileURLToPath(cli),path.resolve(modulePath),root,'--native-bends-only','--restore-source-percussion'],{encoding:'utf8'});
    assert.notEqual(result.status,0);assert.match(result.stderr,/percussion repair requires a fresh copied output/);
    for(const[name,data]of Object.entries(files))assert.equal(fs.readFileSync(path.join(folder,name),'utf8'),data);
  }finally{
    assert.equal(path.dirname(fs.realpathSync(root)),fs.realpathSync(os.tmpdir()));assert(path.basename(root).startsWith('source-percussion-'));fs.rmSync(root,{recursive:true});
  }
});
