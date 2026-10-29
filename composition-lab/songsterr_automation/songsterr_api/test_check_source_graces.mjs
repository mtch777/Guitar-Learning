// Independent verifier tests. Native integration is optional, pure checks always run.
import test from 'node:test';import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import{spawnSync}from'node:child_process';import crypto from 'node:crypto';import {pathToFileURL,fileURLToPath}from'node:url';
import {checkSourceGraces}from'./check_source_graces.mjs';
const copy=x=>JSON.parse(JSON.stringify(x));
function fixture(){
  const rawBeat=(type,notes,graceNote)=>({type,duration:[1,type],notes,...(graceNote?{graceNote}:{})});
  const note=(string,fret,ghost)=>({string,fret,...(ghost===undefined?{}:{ghost})});
  const source=[rawBeat(32,[note(0,2),note(1,3,true)],'onBeat'),rawBeat(4,[note(0,4)]),rawBeat(4,[note(0,4)]),rawBeat(16,[note(0,5,true)],'beforeBeat'),rawBeat(16,[note(0,5,false)],'beforeBeat'),rawBeat(4,[note(0,7)]),rawBeat(4,[note(0,7)])];
  const raw={partId:0,instrumentId:25,tuning:[64,59],measures:[{signature:[4,4],voices:[{beats:source}]}]};
  const native=source.map((b,i)=>({index:i,isEmpty:false,graceType:i===0?1:i===3||i===4?2:0,duration:i===0?8:i===3||i===4?16:4,dots:0,tupletNumerator:-1,tupletDenominator:-1,
    displayStart:[0,0,960,1920,1920,1920,2880][i],displayDuration:[0,960,960,0,0,960,960][i],playbackStart:0,playbackDuration:120,
    notes:b.notes.map(n=>({string:raw.tuning.length-n.string,fret:n.fret,isGhost:n.ghost===true}))}));
  const score={tracks:[{staves:[{isPercussion:false,tuning:[64,59],capo:0,bars:[{voices:[{beats:native}]}]}]}]};
  return{score,parts:[raw],native,source};
}
const good=r=>assert.equal(r.status,'PASS_INDEPENDENT_PITCHED_SOURCE_GRACES',JSON.stringify(r));
const bad=r=>assert.equal(r.status,'FAIL_INDEPENDENT_PITCHED_SOURCE_GRACES',JSON.stringify(r));

test('full identity, exact nominal clock, normalized glyph qualification and purity',()=>{
  const f=fixture(),before=copy(f);const r=checkSourceGraces(f.score,f.parts);good(r);assert.deepEqual(f,before);
  assert.equal(r.counts.checkedVoiceBeats,7);assert.equal(r.counts.checkedNotes,8);assert.equal(r.counts.checkedGraceBeats,3);assert.equal(r.counts.checkedGraceNotes,4);
  assert.equal(r.witnesses[0].actual_native_total_ticks,3840);assert.equal(r.glyph_duration_differences.length,1);
});

test('wrong grace, ghost, native position or duration cannot pass',()=>{
  for(const kind of['grace','ghost','onset','duration','index','empty']){
    const f=fixture();if(kind==='grace')f.native[0].graceType=0;else if(kind==='ghost')f.native[0].notes[1].isGhost=false;
    else if(kind==='onset')f.native[5].displayStart+=1;else if(kind==='duration')f.native[2].displayDuration+=1;
    else if(kind==='index')f.native[2].index=9;else f.native[0].isEmpty=true;
    bad(checkSourceGraces(f.score,f.parts));
  }
});

test('wrong member, missing beat, note count, tuning and capo fail',()=>{
  for(const kind of['member','missing','count','tuning','capo','source_address']){
    const f=fixture();if(kind==='member')f.native[0].notes[0].fret++;else if(kind==='missing')f.native.pop();
    else if(kind==='count')f.native[0].notes.pop();else if(kind==='tuning')f.score.tracks[0].staves[0].tuning=[65,59];
    else if(kind==='capo')f.score.tracks[0].staves[0].capo=2;else f.parts[0].partId=1;
    bad(checkSourceGraces(f.score,f.parts));
  }
});

test('repeated identical geometry preserves source ordinal ghost identity',()=>{
  const f=fixture();good(checkSourceGraces(f.score,f.parts));
  [f.native[3].notes[0].isGhost,f.native[4].notes[0].isGhost]=[false,true];bad(checkSourceGraces(f.score,f.parts));
});

test('duplicate source/native strings and unknown source declarations fail closed',()=>{
  for(const kind of['source_duplicate','native_duplicate','unknown_grace','unknown_ghost','unknown_domain','false_tuplet']){
    const f=fixture();if(kind==='source_duplicate')f.source[0].notes[1]=copy(f.source[0].notes[0]);
    else if(kind==='native_duplicate')f.native[0].notes[1]=copy(f.native[0].notes[0]);
    else if(kind==='unknown_grace')f.source[0].graceNote='unknown';else if(kind==='unknown_ghost')f.source[0].notes[1].ghost=1;
    else if(kind==='unknown_domain')delete f.parts[0].instrumentId;else f.native[1].tupletDenominator=2;
    bad(checkSourceGraces(f.score,f.parts));
  }
});

test('mixed modes, trailing grace and missing ordinary host refuse',()=>{
  for(const kind of['mixed','trailing','rest_host']){
    const f=fixture();if(kind==='mixed')f.source[4].graceNote='onBeat';else if(kind==='trailing')f.source[6].graceNote='beforeBeat';else f.source[5].notes=[{rest:true}];
    bad(checkSourceGraces(f.score,f.parts));
  }
});

test('explicit no-tuplet sentinel and1/1 both work; other negatives do not',()=>{
  const f=fixture();good(checkSourceGraces(f.score,f.parts));f.native[1].tupletNumerator=1;f.native[1].tupletDenominator=1;good(checkSourceGraces(f.score,f.parts));
  f.native[1].tupletNumerator=-2;bad(checkSourceGraces(f.score,f.parts));
});

test('percussion counted as unchecked, not asserted source-grace fidelity',()=>{
  const f=fixture();f.parts[0].instrumentId=1024;f.native[0].graceType=0;
  const r=checkSourceGraces(f.score,f.parts);good(r);assert.equal(r.counts.pitchedGraceVoicesChecked,0);assert.equal(r.counts.uncheckedPercussionGraceBeats,3);assert.equal(r.unchecked_percussion[0].status,'UNCHECKED_PERCUSSION_DOMAIN');
  assert.equal(r.pitched_scope_status,'NO_COVERED_PITCHED_GRACE_VOICES');f.source[0].graceNote='unknown percussion declaration';good(checkSourceGraces(f.score,f.parts));
});

test('performed clocks are intentionally not source nominal truth',()=>{
  const f=fixture();f.native[0].playbackDuration=999;f.native[1].playbackStart=999;good(checkSourceGraces(f.score,f.parts));
});

const modulePath=process.env.ALPHATAB_MODULE||'.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
const at=fs.existsSync(modulePath)?await import(pathToFileURL(path.resolve(modulePath))):null;
test('actual GP7 reimport passes raw source oracle; ghost and timing corruptions fail',{skip:!at},()=>{
  const f=fixture(),score=new at.model.Score();score.addMasterBar(new at.model.MasterBar());const t=new at.model.Track();score.addTrack(t);
  const st=new at.model.Staff();t.addStaff(st);st.stringTuning.tunings=[64,59];const bar=new at.model.Bar();st.addBar(bar);const v=new at.model.Voice();bar.addVoice(v);
  for(const b of f.source){const beat=new at.model.Beat();v.addBeat(beat);beat.duration=b.type;beat.graceType=b.graceNote==='onBeat'?1:b.graceNote==='beforeBeat'?2:0;
    for(const n of b.notes){const note=new at.model.Note();note.string=2-n.string;note.fret=n.fret;note.isGhost=n.ghost===true;beat.addNote(note);}}
  score.finish(new at.Settings());const bytes=new at.exporter.Gp7Exporter().export(score,new at.Settings()),actual=at.importer.ScoreLoader.loadScoreFromBytes(bytes,new at.Settings());
  good(checkSourceGraces(actual,f.parts,at.model.GraceType));actual.tracks[0].staves[0].bars[0].voices[0].beats[0].notes[1].isGhost=false;bad(checkSourceGraces(actual,f.parts));
});

test('old GP plus fabricated grace-report fields cannot masquerade as new proof',{skip:!at},()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'source-grace-cache-negative-'));
  try{
    const folder=path.join(root,'case');fs.mkdirSync(folder);const f=fixture(),score=new at.model.Score();score.addMasterBar(new at.model.MasterBar());
    const t=new at.model.Track();score.addTrack(t);const staff=new at.model.Staff();t.addStaff(staff);staff.stringTuning.tunings=[64,59];const bar=new at.model.Bar();staff.addBar(bar);const voice=new at.model.Voice();bar.addVoice(voice);
    // Deliberately old/incorrect: source grace groups emitted as ordinary beats.
    for(const source of f.source){const beat=new at.model.Beat();voice.addBeat(beat);beat.duration=source.type;
      for(const n of source.notes){const note=new at.model.Note();note.string=2-n.string;note.fret=n.fret;beat.addNote(note);}}
    score.finish(new at.Settings());const bytes=new at.exporter.Gp7Exporter().export(score,new at.Settings());
    fs.writeFileSync(path.join(folder,'score.gp'),bytes);fs.writeFileSync(path.join(folder,'capture.json'),JSON.stringify({capture_complete:true,song_id:1}));
    fs.writeFileSync(path.join(folder,'track-0.json'),JSON.stringify(f.parts[0]));fs.writeFileSync(path.join(folder,'metadata.json'),JSON.stringify({songId:1,title:'Synthetic negative'}));
    fs.writeFileSync(path.join(folder,'gp7-validation.json'),JSON.stringify({songId:1,roundtripPass:true,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),pitchedGraceRestoration:{schema:'identity-checked-pitched-source-graces/1'},directPitchedGraces:{status:'PASS_INDEPENDENT_PITCHED_SOURCE_GRACES'}}));
    const oldGp=fs.readFileSync(path.join(folder,'score.gp')),oldReport=fs.readFileSync(path.join(folder,'gp7-validation.json'));
    const exporter=fileURLToPath(new URL('./export_csv_gp7.mjs',import.meta.url));
    const run=spawnSync(process.execPath,[exporter,path.resolve(modulePath),root,'--native-bends-only','--restore-pitched-graces'],{encoding:'utf8',windowsHide:true});
    assert.notEqual(run.status,0,'An unaudited old GP was accepted solely from fabricated status fields');
    assert.deepEqual(fs.readFileSync(path.join(folder,'score.gp')),oldGp);assert.deepEqual(fs.readFileSync(path.join(folder,'gp7-validation.json')),oldReport);
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});
