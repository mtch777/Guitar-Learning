// Offline instrument preview with alphaTab internal MIDI (not SMF1) and bundled SF2.
// This reproduces the engine's GM rendering, not Guitar Pro RSE or a human player.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {loadPlaybackScore} from './songsterr_automation/songsterr_api/playback_score.mjs';
const args=process.argv.slice(2),limits=args.filter(x=>x.startsWith('--max-seconds='));
if(limits.length>1)throw new Error('Only one explicit render duration limit allowed');
const maxSeconds=limits.length?Number(limits[0].split('=')[1]):120;
if(!Number.isInteger(maxSeconds)||maxSeconds<1||maxSeconds>600)throw new Error('Render duration limit must be an integer1–600seconds');
const [modulePath,fontPath,...files]=args.filter(x=>!x.startsWith('--max-seconds='));
if(!files.length)throw new Error('Usage: node render_gp_instrument.mjs ALPHATAB SF2 FILE.gp ...');
const at=await import(pathToFileURL(path.resolve(modulePath)));
const font=new Uint8Array(fs.readFileSync(fontPath));
for(const file of files){
  const target=file.replace(/\.gp$/i,'.instrument.wav');
  if(fs.existsSync(target)||fs.existsSync(target+'.json'))throw new Error('Refusing to overwrite audio or sidecar '+target);
  const {score,restored,sidecarData,companion_selection}=loadPlaybackScore(at,file);
  const profilePath=file.replace(/\.gp$/i,'.playback.json');
  const profile=fs.existsSync(profilePath)?JSON.parse(fs.readFileSync(profilePath,'utf8')):{};
  const settings=new at.Settings();
  for(const [key,value] of Object.entries(profile)){
    if(!['noteSlightAmplitude','noteSlightLength'].includes(key)||!Number.isFinite(value)||value<=0)throw new Error('Invalid explicit vibrato playback profile');
    settings.player.vibrato[key]=value;
  }
  const midi=new at.midi.MidiFile();
  new at.midi.MidiFileGenerator(score,settings,new at.midi.AlphaSynthMidiFileHandler(midi,false)).generate();
  const output={sampleRate:44100,ready:{on(){}},sampleRequest:{on(){}},samplesPlayed:{on(){}},open(){},destroy(){},pause(){},play(){},resetSamples(){},activate(){},addSamples(){}};
  const synth=new at.synth.AlphaSynth(output,100);
  const options=new at.synth.AudioExportOptions();Object.assign(options,{soundFonts:[font],sampleRate:44100,masterVolume:.5,metronomeVolume:0,useSyncPoints:false});
  const exporter=synth.exportAudio(options,midi,[],new Map());
  const chunks=[];let frames=0,peak=0,nonzero=0,ended=false;
  for(let seconds=0;seconds<maxSeconds;seconds++){
    const c=exporter.render(1000);if(!c){ended=true;break;}
    const samples=new Float32Array(c.samples.length/2);
    for(let i=0;i<samples.length;i++){
      const v=(c.samples[i*2]+c.samples[i*2+1])/2;
      if(!Number.isFinite(v)||Math.abs(v)>=1)throw new Error('Invalid/clipped instrument samples');
      samples[i]=v;peak=Math.max(peak,Math.abs(v));if(Math.abs(v)>1e-6)nonzero++;
    }
    chunks.push(samples);frames+=samples.length;
  }
  if(!ended)throw new Error(`Explicit ${maxSeconds}-second render limit reached; choose an appropriate bounded diagnostic`);
  if(!nonzero)throw new Error('Silent instrument preview');
  const bytes=Buffer.alloc(44+frames*2);bytes.write('RIFF');bytes.writeUInt32LE(bytes.length-8,4);bytes.write('WAVEfmt ',8);bytes.writeUInt32LE(16,16);bytes.writeUInt16LE(1,20);bytes.writeUInt16LE(1,22);bytes.writeUInt32LE(44100,24);bytes.writeUInt32LE(88200,28);bytes.writeUInt16LE(2,32);bytes.writeUInt16LE(16,34);bytes.write('data',36);bytes.writeUInt32LE(frames*2,40);
  let pos=44;for(const chunk of chunks)for(const v of chunk){bytes.writeInt16LE(Math.round(v*32767),pos);pos+=2;}
  fs.writeFileSync(target,bytes);
  const report={renderer:'alphaTab 1.8.4 internal MIDI / Sonivox SF2, fixed gain .5',playbackProfile:profile,renderLimitSeconds:maxSeconds,seconds:frames/44100,peak,nonzeroSamples:nonzero,
    bendCompanionSelection:companion_selection,exactModelBendRestore:restored?{curves:restored.restored,sidecarSha256:crypto.createHash('sha256').update(sidecarData).digest('hex'),nativeGpLossless:false}:null,
    finite:true,clipped:false,fontSha256:crypto.createHash('sha256').update(font).digest('hex'),audioSha256:crypto.createHash('sha256').update(bytes).digest('hex'),
    limitations:['GM sampled instrument, not physical string model or Guitar Pro RSE','HOPO engine rendering primarily changes destination dynamics; authentic legato attack not certified'],listeningJudgment:null};
  fs.writeFileSync(target+'.json',JSON.stringify(report,null,2));console.log(JSON.stringify({file,...report}));
}
