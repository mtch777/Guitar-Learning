// Independent alphaTab GP import/MIDI export. Pass the installed alphaTab module
// path first, followed by local .gp artifacts. No website dependency changes.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [modulePath, ...files] = process.argv.slice(2);
if (!modulePath || !files.length) throw new Error('Usage: node verify_gp.mjs ALPHATAB_MODULE FILE.gp ...');
const at = await import(pathToFileURL(path.resolve(modulePath)));
for (const file of files) {
  const score = at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(file)));
  const expectedPath=file.replace(/\.gp$/i,'.expected.json');
  let compared=false;
  if(fs.existsSync(expectedPath)) {
    const expected=JSON.parse(fs.readFileSync(expectedPath,'utf8'));
    const fraction=x=>{const [a,b='1']=String(x).split('/');return Number(a)/Number(b);};
    if(score.tracks.length!==expected.tracks.length) throw new Error('Track count mismatch');
    for(const [ti,t] of expected.tracks.entries()) {
      if(t.program!==undefined && t.program!==null && score.tracks[ti].playbackInfo.program!==t.program) throw new Error('Instrument program mismatch');
      const actual=score.tracks[ti].staves[0];
      if(JSON.stringify(actual.tuning)!==JSON.stringify([...t.tunings[0]].reverse())) throw new Error('Tuning mismatch');
      if(actual.bars.length!==t.measures.length) throw new Error('Bar count mismatch');
      for(const [mi,m] of t.measures.entries()) for(const [vi,v] of m.voices.entries()) {
        const beats=actual.bars[mi].voices[vi].beats;
        if(beats.length!==v.length) throw new Error('Beat count mismatch');
        for(const [ei,e] of v.entries()) {
          const b=beats[ei];
          if(Math.abs(b.playbackStart-fraction(e.local_onset_q)*960)>1e-6 || Math.abs(b.playbackDuration-fraction(e.duration_q)*960)>1e-6)
            throw new Error(`Timing mismatch at ${ti}/${mi}/${vi}/${ei}`);
          if(JSON.stringify(b.notes.map(n=>n.realValue).sort((a,b)=>a-b))!==JSON.stringify(e.notes.map(n=>n.midi).sort((a,b)=>a-b)))
            throw new Error(`Pitch mismatch at ${ti}/${mi}/${vi}/${ei}`);
        }
      }
    }
    compared=true;
  }
  const midi = new at.midi.MidiFile();
  const handler = new at.midi.AlphaSynthMidiFileHandler(midi, true);
  new at.midi.MidiFileGenerator(score, null, handler).generate();
  fs.writeFileSync(file.replace(/\.gp$/i, '.mid'), midi.toBinary());
  const tracks = score.tracks.map(t => ({ name:t.name, tuning:t.staves[0].tuning, program:t.playbackInfo.program, channel:t.playbackInfo.primaryChannel,
    notes:t.staves.flatMap(s=>s.bars).flatMap(b=>b.voices).flatMap(v=>v.beats).reduce((n,b)=>n+b.notes.length,0) }));
  const report = { file, reader:'alphaTab', tracks, bars:score.masterBars.length,
    midiBytes:midi.toBinary().length, expected_pitch_timing_tuning_checked:compared, playback_listened:false };
  fs.writeFileSync(file.replace(/\.gp$/i, '.alphatab.json'), JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
}
