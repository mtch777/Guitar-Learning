#!/usr/bin/env node
// Fixed rules; no threshold fitting or label-dependent policy selection.
import fs from 'node:fs';
const [,, sourcePath, outputPath, ...flags] = process.argv;
const source = JSON.parse(fs.readFileSync(sourcePath));
if (source.rows.length !== 384 || source.report.detector !== 'correlation-start-yin-votes') throw Error('Expected full hybrid replay');
if (source.rows.some(r => !Array.isArray(r.early_singletons))) throw Error('Missing frame diagnostics');
const correct = (e,r) => !!e && e.midi === r.true_midi && e.string === r.true_string;
function early(r, yinOnly) {
  let prior = null;
  for (const e of r.early_singletons) {
    // Existing replay uses YIN once its full 240 ms window is available,
    // provided capture was already active before this frame.
    const yin = e.elapsed_ms >= 240 && r.captured && e.frame > r.captured.first_trigger_frame;
    if ((yinOnly && !yin) || e.pitch_confidence < .55 || e.dbfs < -48) { prior = null; continue; }
    if (prior && e.frame === prior.frame + 1 && e.midi === prior.midi && e.string === prior.string) return e;
    prior = e;
  }
  return null;
}
const all = source.rows;
const rows = flags.includes('--smoke') ? [
  ...all.filter(r => r.early_singleton && !correct(r.early_singleton,r)).slice(0,4),
  ...all.filter(r => r.early_singleton && correct(r.early_singleton,r)).slice(0,4),
  ...all.filter(r => !r.early_singleton && r.fusion).slice(0,4),
  ...all.filter(r => !r.fusion).slice(0,1),
] : all;
const policies = ['immediate','wait','two_frames','two_yin_frames'];
const scored = rows.map(r => {
  const final = r.fusion ? { ...r.fusion, elapsed_ms:r.capture_ms+r.inference_ms } : null;
  const events = {immediate:r.first_event,wait:final};
  const earlyEvents = {two_frames:early(r,false),two_yin_frames:early(r,true)};
  for (const name of Object.keys(earlyEvents)) events[name]=earlyEvents[name]||final;
  return {file:r.file,true_midi:r.true_midi,true_string:r.true_string,events,
    correct:Object.fromEntries(policies.map(name=>[name,correct(events[name],r)])),
    early:earlyEvents,time_saved_ms:Object.fromEntries(Object.keys(earlyEvents).map(name=>
      [name,earlyEvents[name]&&final ? final.elapsed_ms-earlyEvents[name].elapsed_ms:null]))};
});
const median = a => { const s=a.filter(Number.isFinite).sort((a,b)=>a-b);return s.length?s[Math.floor((s.length-1)/2)]:null; };
const report={phase:flags.includes('--smoke')?'smoke':'real',recordings:scored.length,
  source_run:36665632798,source_artifact:11075223801,
  policies:Object.fromEntries(policies.map(name=>[name,{
    correct:scored.filter(r=>r.correct[name]).length,
    missing:scored.filter(r=>!r.events[name]).length,
    rescues_vs_wait:scored.filter(r=>!r.correct.wait&&r.correct[name]).length,
    regressions_vs_wait:scored.filter(r=>r.correct.wait&&!r.correct[name]).length,
    ...(name.startsWith('two_')?{
      early_correct:scored.filter(r=>r.early[name]&&r.correct[name]).length,
      early_wrong:scored.filter(r=>r.early[name]&&!r.correct[name]).length,
      median_saved_ms_correct:median(scored.filter(r=>r.correct[name]).map(r=>r.time_saved_ms[name])),
      zero_regression_gate:scored.every(r=>!r.correct.wait||r.correct[name]),
    }:{})}]))};
fs.writeFileSync(outputPath,JSON.stringify({report,rows:scored}));
console.log(JSON.stringify(report,null,2));
