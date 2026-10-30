// Bind every actual MIDI event to its generating native note, including resets.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {pathToFileURL,fileURLToPath} from 'node:url';
import {loadPlaybackScore} from './songsterr_automation/songsterr_api/playback_score.mjs';
const [modulePath,folder]=process.argv.slice(2),at=await import(pathToFileURL(path.resolve(modulePath))),root=path.resolve(folder);
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),snapshot=read(path.join(root,'dynamic-native-snapshot.json')),cases={};
for(const name of ['source','zero','changed']){
 const {score}=loadPlaybackScore(at,path.join(root,name,'score.gp'),{}),settings=new at.Settings();settings.notation.notationMode=at.NotationMode.GuitarPro;
 const notes=new Map(snapshot.cases[name].notes.map(n=>[n.native_ref,n.source_ref])),midi=new at.midi.MidiFile(),handler=new at.midi.AlphaSynthMidiFileHandler(midi,false),owners=new WeakMap();let current=null;
 const add=midi.addEvent.bind(midi);midi.addEvent=e=>{owners.set(e,current);return add(e);};
 const generator=new at.midi.MidiFileGenerator(score,settings,handler),generate=generator._generateNote;
 generator._generateNote=function(note,...args){const old=current,b=note.beat,v=b.voice,bar=v.bar,track=bar.staff.track;current=notes.get(`native:${track.index}:${bar.index+1}:${v.index}:${b.index}:${note.index}`)??null;try{return generate.call(this,note,...args);}finally{current=old;}};
 generator.generate();
 if(JSON.stringify(midi.events)!==snapshot.cases[name].raw_midi_json)throw Error('Independent complete MIDI regeneration differs: '+name);
 cases[name]=midi.events.map(e=>({origin_source_ref:owners.get(e)??null,kind:e.constructor.name,data:JSON.parse(JSON.stringify(e))}));
}
const out=path.join(root,'rhythm-midi-origins.json');if(fs.existsSync(out))throw Error('Fresh origin ledger required');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
fs.writeFileSync(out,JSON.stringify({schema:'actual-native-midi-origins/1',script_sha256:hash(fileURLToPath(import.meta.url)),snapshot_sha256:hash(path.join(root,'dynamic-native-snapshot.json')),cases},null,2));
