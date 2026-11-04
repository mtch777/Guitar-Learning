import test from 'node:test';import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import {createHash} from 'node:crypto';import {pathToFileURL} from 'node:url';
import {checkSourceHammerPullThroughTies,restoreHammerPullThroughTies} from './restore_hammer_pull_through_ties.mjs';
import {loadPlaybackScore} from './playback_score.mjs';
const modulePath=process.env.ALPHATAB_MODULE||'.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
const at=fs.existsSync(modulePath)?await import(pathToFileURL(path.resolve(modulePath))):null;
const json=score=>at.model.JsonConverter.scoreToJson(score);
function fixture({chains=1,split=true}={}) {
  const score=new at.model.Score(),track=new at.model.Track(),staff=new at.model.Staff();score.addTrack(track);track.addStaff(staff);staff.stringTuning.tunings=[64,59,55,50,45,40];
  const measures=[],items=[];
  for(let ci=0;ci<chains;ci++) {
    score.addMasterBar(new at.model.MasterBar());const bar=new at.model.Bar(),voice=new at.model.Voice();staff.addBar(bar);bar.addVoice(voice);
    const raw=split?[{type:4,duration:[1,4],notes:[{fret:5,string:0,hp:true}]},{type:4,duration:[1,4],notes:[{fret:5,string:0,tie:true}]},{type:2,duration:[1,2],notes:[{fret:0,string:0}]}]:[{type:2,duration:[1,2],notes:[{fret:5,string:0,hp:true}]},{type:2,duration:[1,2],notes:[{fret:0,string:0}]}];
    for(const r of raw) {const b=new at.model.Beat();voice.addBeat(b);b.duration=r.type;const n=new at.model.Note();n.string=6;n.fret=r.notes[0].fret;n.isHammerPullOrigin=!!r.notes[0].hp;n.isTieDestination=!!r.notes[0].tie;b.addNote(n);}
    measures.push({voices:[{beats:raw}]});items.push({origin:voice.beats[0].notes[0],tail:split?voice.beats[1].notes[0]:null,target:voice.beats.at(-1).notes[0]});
  }
  const parts=[{instrumentId:25,tuning:[...staff.tuning],measures}],settings=new at.Settings();score.finish(settings);return{score,parts,settings,items};
}
function midi(score) {const calls=[],file=new at.midi.MidiFile(),handler=new at.midi.AlphaSynthMidiFileHandler(file,false);const add=handler.addNote.bind(handler);handler.addNote=(...args)=>{calls.push(args);return add(...args);};new at.midi.MidiFileGenerator(score,new at.Settings(),handler).generate();return calls;}
function withoutHpLinks(score) {return JSON.stringify(JSON.parse(json(score)),(k,v)=>['hammerpulloriginnoteid','hammerpulldestinationnoteid'].includes(k)?undefined:v);}

test('written HP through tie keeps the complete hold and fresh target velocity', {skip:!at},()=>{
  const f=fixture(),baseline=fixture({split:false}),p=f.items[0],source=structuredClone(f.parts),before=withoutHpLinks(f.score);
  assert.equal(p.origin.hammerPullDestination,p.tail);assert.equal(p.target.hammerPullOrigin,null);
  assert.notDeepEqual(midi(f.score),midi(baseline.score));
  assert.equal(checkSourceHammerPullThroughTies(f.score,f.parts).checkedChains,1);
  assert.equal(restoreHammerPullThroughTies(f.score).restoredChains,1);
  assert.equal(p.origin.hammerPullDestination,p.target);assert.equal(p.target.hammerPullOrigin,p.origin);assert.equal(p.tail.hammerPullOrigin,null);
  assert.deepEqual(midi(f.score),midi(baseline.score));assert.equal(withoutHpLinks(f.score),before);assert.deepEqual(f.parts,source);
  const after=json(f.score);assert.equal(restoreHammerPullThroughTies(f.score).restoredChains,0);assert.equal(json(f.score),after);
});

test('save/reload applies routing only through the authenticated playback policy', {skip:!at},()=>{
  const f=fixture(),bytes=new at.exporter.Gp7Exporter().export(f.score,f.settings),dir=fs.mkdtempSync(path.join(os.tmpdir(),'hp-ties-'));
  try {
    const gp=path.join(dir,'source.gp');fs.writeFileSync(gp,bytes);
    const before=loadPlaybackScore(at,gp).score;
    assert.notDeepEqual(midi(before),midi(fixture({split:false}).score));
    fs.writeFileSync(path.join(dir,'source.execution-policy.json'),JSON.stringify({schema:'composition-lab.execution-policy/1',policy:'composition-lab.continuous-mute-terminal-release/1',gp_sha256:createHash('sha256').update(bytes).digest('hex'),exact_model_bends_sha256:null}));
    const after=loadPlaybackScore(at,gp);assert.equal(after.hammer_pull_registration.restoredChains,1);assert.deepEqual(midi(after.score),midi(fixture({split:false}).score));
    const disabled=loadPlaybackScore(at,gp,{execution_policy:false});assert.equal(disabled.hammer_pull_registration,null);assert.deepEqual(midi(disabled.score),midi(before));
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});

test('wrong, mixed, missing, forked or noncontiguous chain refuses before earlier repairs', {skip:!at},()=>{
  for(const change of [
    p=>p.tail.fret++,p=>p.tail.string--,p=>p.tail.isDead=true,p=>p.tail.isHammerPullOrigin=true,
    p=>p.tail.tieOrigin=null,p=>p.tail.beat.playbackStart++,p=>p.target.beat.displayStart++,
    p=>p.origin.tieDestination=null,
    p=>p.origin.hammerPullDestination=null,p=>p.target.hammerPullOrigin=p.tail,p=>p.tail.hammerPullOrigin=null,
    p=>p.tail.tieDestination=p.origin,p=>p.target.isTieDestination=true,p=>p.target.beat.graceType=1,
  ]) {
    const f=fixture({chains:2});change(f.items[1]);const before=json(f.score);
    assert.throws(()=>restoreHammerPullThroughTies(f.score),/HP through ties/);assert.equal(json(f.score),before);
  }
});

test('source authentication rejects mismatched declarations, identity, duration and sequence', {skip:!at},()=>{
  for(const change of [rows=>delete rows[0].notes[0].hp,rows=>delete rows[1].notes[0].tie,rows=>rows[1].notes[0].hp=true,
    rows=>rows[2].notes[0].fret++,rows=>rows[1].duration=[1,8],rows=>rows.splice(1,0,structuredClone(rows[2]))]) {
    const f=fixture();change(f.parts[0].measures[0].voices[0].beats);const before=json(f.score);
    assert.throws(()=>checkSourceHammerPullThroughTies(f.score,f.parts),/HP through ties/);assert.equal(json(f.score),before);
  }
});

test('ordinary HP and unrelated native links are untouched', {skip:!at},()=>{
  const f=fixture({split:false});const before=json(f.score);assert.equal(restoreHammerPullThroughTies(f.score).restoredChains,0);assert.equal(json(f.score),before);
});
