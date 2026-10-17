// Verify what alphaTab actually sends to the instrument synth, without listening claims.
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';
const [modulePath,reference,...variants]=process.argv.slice(2);
if(!variants.length)throw new Error('Usage: node verify_technique_playback.mjs ALPHATAB REFERENCE.gp VARIANT.gp ...');
const at=await import(pathToFileURL(path.resolve(modulePath)));
function events(file){
 const score=at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(file)));
 const midi=new at.midi.MidiFile();new at.midi.MidiFileGenerator(score,null,new at.midi.AlphaSynthMidiFileHandler(midi,false)).generate();return midi.events;
}
const base=events(reference),ons=x=>x.filter(e=>e.constructor.name==='NoteOnEvent');
const identity=x=>x.filter(e=>['NoteOnEvent','NoteOffEvent'].includes(e.constructor.name)).map(e=>[e.constructor.name,e.tick,e.channel,e.noteKey]);
for(const file of variants){
 const actual=events(file);
 if(JSON.stringify(identity(base))!==JSON.stringify(identity(actual)))throw new Error('Pitch/timing playback lock changed');
 const a=ons(base),b=ons(actual);const dynamicsChanged=a.filter((e,i)=>e.noteVelocity!==b[i].noteVelocity).length;
 const bends=actual.filter(e=>e.constructor.name==='NoteBendEvent'&&e.value!==2147483648).length;
 if(file.includes('vibrato')&&bends===0)throw new Error('Vibrato does not reach synth');
 if(!file.includes('vibrato')&&dynamicsChanged===0)throw new Error('HOPO does not change engine playback');
 console.log(JSON.stringify({file,pitchAndTimingPreserved:true,destinationDynamicsChanged:dynamicsChanged,noncenterPitchEvents:bends,
    scope:'Engine event verification, not authentic physical legato or human musical judgment'}));
}
