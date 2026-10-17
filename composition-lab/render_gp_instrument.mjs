// Offline instrument preview with alphaTab internal MIDI (not SMF1) and bundled SF2.
// This reproduces the engine's GM rendering, not Guitar Pro RSE or a human player.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const [modulePath,fontPath,...files]=process.argv.slice(2);
if(!files.length)throw new Error('Usage: node render_gp_instrument.mjs ALPHATAB SF2 FILE.gp ...');
const at=await import(pathToFileURL(path.resolve(modulePath)));
const font=new Uint8Array(fs.readFileSync(fontPath));
for(const file of files){
  const target=file.replace(/\.gp$/i,'.instrument.wav');
  if(fs.existsSync(target))throw new Error('Refusing to overwrite '+target);
  const score=at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(file)));
  const midi=new at.midi.MidiFile();
  new at.midi.MidiFileGenerator(score,null,new at.midi.AlphaSynthMidiFileHandler(midi,false)).generate();
  const output={sampleRate:44100,ready:{on(){}},sampleRequest:{on(){}},samplesPlayed:{on(){}},open(){},destroy(){},pause(){},play(){},resetSamples(){},activate(){},addSamples(){}};
  const synth=new at.synth.AlphaSynth(output,100);
  const options=new at.synth.AudioExportOptions();Object.assign(options,{soundFonts:[font],sampleRate:44100,masterVolume:.5,metronomeVolume:0,useSyncPoints:false});
  const exporter=synth.exportAudio(options,midi,[],new Map());
  const chunks=[];let frames=0,peak=0,nonzero=0,ended=false;
  for(let seconds=0;seconds<120;seconds++){
    const c=exporter.render(1000);if(!c){ended=true;break;}
    const samples=new Float32Array(c.samples.length/2);
    for(let i=0;i<samples.length;i++){
      const v=(c.samples[i*2]+c.samples[i*2+1])/2;
      if(!Number.isFinite(v)||Math.abs(v)>=1)throw new Error('Invalid/clipped instrument samples');
      samples[i]=v;peak=Math.max(peak,Math.abs(v));if(Math.abs(v)>1e-6)nonzero++;
    }
    chunks.push(samples);frames+=samples.length;
  }
  if(!ended)throw new Error('Explicit 120-second preview limit reached; export a shorter diagnostic score');
  if(!nonzero)throw new Error('Silent instrument preview');
  const bytes=Buffer.alloc(44+frames*2);bytes.write('RIFF');bytes.writeUInt32LE(bytes.length-8,4);bytes.write('WAVEfmt ',8);bytes.writeUInt32LE(16,16);bytes.writeUInt16LE(1,20);bytes.writeUInt16LE(1,22);bytes.writeUInt32LE(44100,24);bytes.writeUInt32LE(88200,28);bytes.writeUInt16LE(2,32);bytes.writeUInt16LE(16,34);bytes.write('data',36);bytes.writeUInt32LE(frames*2,40);
  let pos=44;for(const chunk of chunks)for(const v of chunk){bytes.writeInt16LE(Math.round(v*32767),pos);pos+=2;}
  fs.writeFileSync(target,bytes);
  const report={renderer:'alphaTab 1.8.4 internal MIDI / Sonivox SF2, fixed gain .5',seconds:frames/44100,peak,nonzeroSamples:nonzero,
    finite:true,clipped:false,fontSha256:crypto.createHash('sha256').update(font).digest('hex'),audioSha256:crypto.createHash('sha256').update(bytes).digest('hex'),
    limitations:['GM sampled instrument, not physical string model or Guitar Pro RSE','HOPO engine rendering primarily changes destination dynamics; authentic legato attack not certified'],listeningJudgment:null};
  fs.writeFileSync(target+'.json',JSON.stringify(report,null,2));console.log(JSON.stringify({file,...report}));
}
