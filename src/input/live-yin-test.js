import { detectPitch, frequencyToMidi } from '../audio/pitch.js';
import { referenceYin } from '../audio/reference-yin.js';

const $ = id => document.getElementById(id);
const openMidi = [27, 34, 39, 44, 49, 54, 58, 63];
const frets = [0, 5, 12, 19, 24], attacks = ['soft', 'normal', 'hard'];
for (let s = 1; s <= 8; s++) $('string').add(new Option(String(s), String(s)));
const trials = [], plan = [];
for (let s = 1; s <= 8; s++) for (const fret of frets) for (const attack of attacks) for (let repeat = 1; repeat <= 2; repeat++) plan.push({ string: s, fret, attack, repeat });
let planIndex = 0, context, stream, source, processor, sink, recording = null, recent = [], sampleCount = 0;
function target(t) {
  $('string').value = t.string; $('fret').value = t.fret;
  $('attack').value = t.attack; $('repeat').value = t.repeat;
  $('progress').textContent = `Planned ${planIndex + 1}/${plan.length}: string ${t.string}, fret ${t.fret}, ${t.attack}, repeat ${t.repeat}`;
}
target(plan[0]);
$('next').onclick = () => { planIndex = Math.min(planIndex + 1, plan.length - 1); target(plan[planIndex]); };
function snapshot() {
  const string = Number($('string').value), fret = Number($('fret').value);
  if (!Number.isInteger(string) || string < 1 || string > 8 || !Number.isInteger(fret) || fret < 0 || fret > 24) throw new Error('Choose a string and fret within range');
  return { string, fret, attack: $('attack').value, repeat: Number($('repeat').value), expectedMidi: openMidi[string - 1] + fret };
}
$('microphone').onclick = async () => {
  if (stream) {
    processor.onaudioprocess = null; stream.getTracks().forEach(t => t.stop());
    source.disconnect(); processor.disconnect(); sink.disconnect(); await context.close();
    stream = null; recent = []; sampleCount = 0; recording = null;
    $('microphone').textContent = 'Enable microphone'; $('record').disabled = true; $('status').textContent = 'Microphone off'; return;
  }
  try {
    context = new AudioContext(); await context.resume();
    stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }, video: false });
    source = context.createMediaStreamSource(stream);
    processor = context.createScriptProcessor(4096, 1, 1);
    sink = context.createGain(); sink.gain.value = 0;
    source.connect(processor); processor.connect(sink); sink.connect(context.destination);
    processor.onaudioprocess = event => {
      const samples = new Float32Array(event.inputBuffer.getChannelData(0));
      recent.push(samples); sampleCount += samples.length;
      const max = Math.ceil(context.sampleRate * 0.24);
      while (recent.length > 1 && sampleCount - recent[0].length >= max) sampleCount -= recent.shift().length;
      if (!recording) return;
      const duration = recording.durationSamples += samples.length;
      const t0 = performance.now(), old = detectPitch(samples, context.sampleRate), oldMs = performance.now() - t0;
      const window = new Float32Array(Math.min(sampleCount, max));
      let offset = sampleCount;
      for (let i = recent.length - 1; i >= 0 && offset > sampleCount - window.length; i--) {
        offset -= recent[i].length;
        const from = Math.max(0, sampleCount - window.length - offset);
        window.set(recent[i].subarray(from), Math.max(0, offset - (sampleCount - window.length)));
      }
      const t1 = performance.now();
      const reference = window.length >= max ? referenceYin(window, context.sampleRate) : { frequency: NaN, confidence: 0 };
      const referenceMs = performance.now() - t1;
      const rms = old.rms;
      recording.frames.push({ elapsedMs: duration / context.sampleRate * 1000, rms,
        oldMidi: Number.isFinite(old.frequency) ? frequencyToMidi(old.frequency) : null,
        oldConfidence: old.confidence, oldMs,
        referenceMidi: Number.isFinite(reference.frequency) ? frequencyToMidi(reference.frequency) : null,
        referenceConfidence: reference.confidence, referenceMs,
        windowMs: window.length / context.sampleRate * 1000 });
      if (duration >= context.sampleRate * 1.2) finish();
    };
    $('microphone').textContent = 'Disable microphone'; $('record').disabled = false;
    $('status').textContent = `Ready · ${context.sampleRate} Hz · 1.2 seconds per pluck`;
  } catch (error) { $('status').textContent = `Microphone error: ${error.message}`; }
};
$('record').onclick = () => {
  if (!stream || recording) return;
  try { recording = { ...snapshot(), startedAt: new Date().toISOString(), sampleRate: context.sampleRate, durationSamples: 0, frames: [] }; }
  catch (error) { $('status').textContent = error.message; return; }
  recent = []; sampleCount = 0;
  $('record').disabled = true; $('status').textContent = 'Recording: pluck now…';
};
function finish() {
  const result = recording; recording = null;
  trials.push(result); $('record').disabled = false;
  $('status').textContent = `Saved ${trials.length} trial(s). Predictions remain hidden until export.`;
  const row = $('history').insertRow();
  for (const value of [result.string, result.fret, result.attack, result.repeat, result.frames.length]) row.insertCell().textContent = value;
  if (planIndex < plan.length - 1) { planIndex++; target(plan[planIndex]); }
}
$('download').onclick = () => {
  const payload = { schema: 'paired-live-yin-v1', createdAt: new Date().toISOString(), userAgent: navigator.userAgent,
    note: 'One stream, paired frame decisions; reference confidence is diagnostic and not calibrated for the trainer gate.', trials };
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload)], { type: 'application/json' }));
  const a = document.createElement('a'); a.href = url; a.download = 'live-yin-paired-' + Date.now() + '.json'; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
