// Render bounded real-score passages with the ordinary alphaTab reader.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {pathToFileURL} from 'node:url';
import {loadPlaybackScore} from './songsterr_automation/songsterr_api/playback_score.mjs';
const [modulePath,fontPath,jobsPath]=process.argv.slice(2),at=await import(pathToFileURL(path.resolve(modulePath)));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const font=new Uint8Array(fs.readFileSync(fontPath)),jobs=JSON.parse(fs.readFileSync(jobsPath,'utf8')),results=[];
for(const job of jobs){
 if(fs.existsSync(job.out))throw Error('Refusing to overwrite '+job.out);
 const {data,score,sidecarData,restored,companion_selection}=loadPlaybackScore(at,job.file,job);
 const settings=new at.Settings();settings.notation.notationMode=at.NotationMode.GuitarPro;
 const profilePath=job.file.replace(/\.gp$/i,'.playback.json');
 const playbackProfile=fs.existsSync(profilePath)?JSON.parse(fs.readFileSync(profilePath,'utf8')):{};
 for(const [key,value] of Object.entries(playbackProfile)){
  if(!['noteSlightAmplitude','noteSlightLength'].includes(key)||!Number.isFinite(value)||value<=0)throw Error('Invalid explicit vibrato playback profile');
  settings.player.vibrato[key]=value;
 }
 const midi=new at.midi.MidiFile(),generator=new at.midi.MidiFileGenerator(score,settings,new at.midi.AlphaSynthMidiFileHandler(midi,false));generator.generate();
 const bars=generator.tickLookup.masterBars,start=bars.findIndex(b=>b.masterBar.index===job.start_bar-1),end=bars.findIndex((b,i)=>i>=start&&b.masterBar.index===job.end_bar-1);
 if(start<0||end<start||end-start>16)throw Error('Unresolved passage playback range');
 const tempoPoints=bars.flatMap(b=>b.tempoChanges).sort((a,b)=>a.tick-b.tick);
 function secondsBetween(a,b){let q=a,tempo=score.tempo,total=0;for(const p of tempoPoints){if(p.tick<=a){tempo=p.tempo;continue;}if(p.tick>=b)break;total+=(p.tick-q)/960*60/tempo;q=p.tick;tempo=p.tempo;}return total+(b-q)/960*60/tempo;}
 const fraction=x=>{const parts=String(x||0).split('/').map(Number);return parts.length===2?parts[0]/parts[1]:parts[0];};
 const targetBar=bars.slice(start,end+1).find(b=>b.masterBar.index===job.target_bar-1),targetTick=targetBar?targetBar.start+fraction(job.target_offset_q)*960:bars[start].start;
 const options=new at.synth.AudioExportOptions();Object.assign(options,{soundFonts:[font],sampleRate:44100,masterVolume:.3,metronomeVolume:0,useSyncPoints:false,playbackRange:{startTick:bars[start].start,endTick:bars[end].end}});
 if(job.mode==='focused'){
  const focus=score.tracks[job.track],channels=new Set([focus.playbackInfo.primaryChannel,focus.playbackInfo.secondaryChannel]);
  options.trackVolume=new Map();
  for(const [i,t] of score.tracks.entries())for(const channel of new Set([t.playbackInfo.primaryChannel,t.playbackInfo.secondaryChannel])){
   if(i!==job.track&&channels.has(channel))throw Error('Shared MIDI channel prevents an honest isolated-track preview');
   options.trackVolume.set(channel,i===job.track?1:0);
  }
 }
 const output={sampleRate:44100,ready:{on(){}},sampleRequest:{on(){}},samplesPlayed:{on(){}},open(){},destroy(){},pause(){},play(){},resetSamples(){},activate(){},addSamples(){}};
 const synth=new at.synth.AlphaSynth(output,100),exporter=synth.exportAudio(options,midi,[],new Map()),chunks=[];
 let frames=0,peak=0,squares=0,ended=false;
 for(let i=0;i<40;i++){
  const chunk=exporter.render(1000);if(!chunk){ended=true;break;}
  const mono=new Float32Array(chunk.samples.length/2);
  for(let j=0;j<mono.length;j++){const v=(chunk.samples[j*2]+chunk.samples[j*2+1])/2;if(!Number.isFinite(v)||Math.abs(v)>=1)throw Error('Invalid/clipped audio');mono[j]=v;peak=Math.max(peak,Math.abs(v));squares+=v*v;}
  chunks.push(mono);frames+=mono.length;
 }
 if(!ended||!frames||squares/frames<1e-12)throw Error('Silent or over-limit passage');
 const wav=Buffer.alloc(44+frames*2);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(44100,24);wav.writeUInt32LE(88200,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(frames*2,40);
 let offset=44;for(const chunk of chunks)for(const value of chunk){wav.writeInt16LE(Math.round(value*32767),offset);offset+=2;}
 fs.writeFileSync(job.out,wav);
 const result={...job,playback_profile:playbackProfile,gp_sha256:hash(data),midi_event_sha256:hash(JSON.stringify(midi.events)),audio_sha256:hash(wav),seconds:frames/44100,rms:Math.sqrt(squares/frames),peak,
  target_seconds:secondsBetween(bars[start].start,targetTick),reader:restored?'alphaTab with exact-model-bend companion':'unmodified alphaTab 1.8.4',bend_companion_selection:companion_selection,exact_model_bend_restore:restored?{curves:restored.restored,sidecar_sha256:hash(sidecarData),native_gp_lossless:false}:null,renderer:'alphaTab internal MIDI / Sonivox GM SF2, fixed .3 gain',font_sha256:hash(font),tracks:score.tracks.length,bars:score.masterBars.length,playback_range:options.playbackRange,listening_judgment:null};
 results.push(result);fs.writeFileSync(jobsPath.replace(/\.json$/,'.results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify({case_id:job.case_id,method:job.method,mode:job.mode,seconds:result.seconds,peak}));
}
