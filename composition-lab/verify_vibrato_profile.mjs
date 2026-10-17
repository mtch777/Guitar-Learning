// Verify emitted pitch offsets, rather than infer depth from the waveform/timbre.
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';
const [modulePath,oldFile,newFile]=process.argv.slice(2);const at=await import(pathToFileURL(path.resolve(modulePath)));
function bends(file,profile){const score=at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(file)));const settings=new at.Settings();Object.assign(settings.player.vibrato,profile);const midi=new at.midi.MidiFile();new at.midi.MidiFileGenerator(score,settings,new at.midi.AlphaSynthMidiFileHandler(midi,false)).generate();return midi.events.filter(e=>e.constructor.name==='NoteBendEvent');}
const original=bends(oldFile,{}),profile=JSON.parse(fs.readFileSync(newFile.replace(/\.gp$/i,'.playback.json'),'utf8')),corrected=bends(newFile,profile);
if(original.length!==corrected.length||original.some((e,i)=>e.tick!==corrected[i].tick))throw new Error('Vibrato event timing changed');
const center=2147483648;let maxError=0,oldPeak=0,newPeak=0;
for(let i=0;i<original.length;i++){const a=original[i].value-center,b=corrected[i].value-center;maxError=Math.max(maxError,Math.abs(b-a/2));oldPeak=Math.max(oldPeak,Math.abs(a));newPeak=Math.max(newPeak,Math.abs(b));}
if(!oldPeak||maxError>1)throw new Error(JSON.stringify({maxError,oldPeak,newPeak}));
console.log(JSON.stringify({sameEventTicks:true,pitchOffsetScale:.5,eventCount:original.length,maxRoundingError:maxError,oldPeak,newPeak,scope:'Preview-engine pitch events; GP qualitative marker does not encode this precise depth'}));
