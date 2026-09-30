#!/usr/bin/env node
// Offline replay of the current microphone frame and pluck gates with
// held-out estimated-MIDI fusion3 fold models. No simulated lesson answer.
import fs from 'node:fs';
import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { detectPitch, frequencyToMidi } from '../src/audio/pitch.js';
import { referenceYin } from '../src/audio/reference-yin.js';
import { RingingPluckBuffer } from '../src/audio/ringing-pluck-buffer.js';
import { candidateStringsForMidi } from '../src/guitar/tuning.js';
import { classifyFusion3 } from '../src/classifier/fusion3.js';
import { fitIsotonic, FUSION_MODELS } from '../src/classifier/isotonic-fusion.js';
import { maskFusionProbabilities } from '../src/classifier/xgboost-fusion-model.js';

const [,, fixturePath, rawDir, oofPath, foldDir, outPath, ...flags] = process.argv;
if (!outPath) throw Error('usage: node run_step18_full_replay.mjs fixture.json raw_f32_dir oof.json fold_dir out.json [--smoke] [--reference-yin] [--hybrid-start]');
const useReferenceYin = flags.includes('--reference-yin');
const hybridStart = flags.includes('--hybrid-start');
if (hybridStart && !useReferenceYin) throw Error('--hybrid-start requires --reference-yin');
const leadingIndex = flags.indexOf('--leading-samples');
const leadingSamples = leadingIndex < 0 ? 0 : Number(flags[leadingIndex + 1]);
if (!Number.isInteger(leadingSamples) || leadingSamples < 0 || leadingSamples > 16384) throw Error('Invalid leading sample count');
const source = JSON.parse(fs.readFileSync(fixturePath));
const rows = Array.isArray(source) ? source : source.rows;
const probabilities = JSON.parse(fs.readFileSync(oofPath));
const detectedMidi = JSON.parse(fs.readFileSync('training/results/reference/step18_reference_yin_midi_384.json'));
if (rows.length !== 384 || probabilities.length !== 384) throw Error('Expected 384 fixture and calibration recordings');
const byMidi = new Map();
for (const r of probabilities) {
  const masked = Object.fromEntries(FUSION_MODELS.map(name => {
    const p = maskFusionProbabilities(r[`${name}_probabilities`], detectedMidi[r.file]);
    return [name, { pred: p.indexOf(Math.max(...p)) + 1, conf: Math.max(...p) }];
  }));
  byMidi.set(r.file, { ...r, masked });
}
const targets = flags.includes('--smoke') ? rows.filter(r => r.midi >= 54 && r.midi <= 60 && r.file.includes('_normal_')) : rows;
if (flags.includes('--smoke') && targets.length !== 36) throw Error(`Expected 36 smoke rows, got ${targets.length}`);
const caches = new Map(), results = [];
const sampleRate = 44100, frameSize = 4096;
function bundle(midi) {
  if (!caches.has(midi)) {
    const models = Object.fromEntries(FUSION_MODELS.map(name => [name,
      JSON.parse(fs.readFileSync(path.join(foldDir, `midi_${midi}`, `${name}.json`)))]));
    const train = probabilities.filter(r => r.midi !== midi).map(r => byMidi.get(r.file));
    const calibrators = Object.fromEntries(FUSION_MODELS.map(name => [name, fitIsotonic(
      train.map(r => r.masked[name].conf), train.map(r => Number(r.masked[name].pred === r.string))
    )]));
    caches.set(midi, { models, calibrators });
  }
  return caches.get(midi);
}
for (const [index, row] of targets.entries()) {
  const bytes = fs.readFileSync(path.join(rawDir, row.file + '.f32'));
  const raw = new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4);
  const samples = new Float32Array(leadingSamples + raw.length);
  samples.set(raw, leadingSamples);
  const buffer = new RingingPluckBuffer();
  const pitchTimes = [], bufferTimes = [], singletonEvents = [];
  let captured = null, fusion = null, captureMs = null, inferenceMs = null;
  let frames = 0, firstTriggerFrame = null, eligibleFrames = 0, maxPitchConfidence = 0;
  for (let offset = 0; offset + frameSize <= samples.length; offset += frameSize) {
    const chunk = samples.subarray(offset, offset + frameSize), pitchStart = performance.now();
    // Same rolling 240 ms input and referenceYin implementation as live-yin-test.
    const end = offset + frameSize, yinWindow = Math.ceil(sampleRate * .24);
    const pitch = useReferenceYin
      ? end >= yinWindow ? referenceYin(samples.subarray(end - yinWindow, end), sampleRate)
        : { frequency: NaN, confidence: 0 }
      : detectPitch(chunk, sampleRate);
    // A hybrid starts the same 0.82 s capture from the existing frame detector,
    // then uses YIN votes once its 240 ms window is available.
    const votingPitch = hybridStart && end < yinWindow ? detectPitch(chunk, sampleRate) : pitch;
    pitchTimes.push(performance.now() - pitchStart);
    const midi = Number.isFinite(votingPitch.frequency) ? frequencyToMidi(votingPitch.frequency) : null;
    let peak = 0, sumSquares = 0;
    for (const v of chunk) { peak = Math.max(peak, Math.abs(v)); sumSquares += v * v; }
    const rms = useReferenceYin ? Math.sqrt(sumSquares / frameSize) : pitch.rms;
    const frame = { samples: chunk, sampleRate, midi, pitchConfidence: votingPitch.confidence,
      rms, peak, dbfs: rms > 0 ? 20 * Math.log10(rms) : -Infinity };
    maxPitchConfidence = Math.max(maxPitchConfidence, votingPitch.confidence);
    if (midi != null && votingPitch.confidence >= .55 && frame.dbfs >= -48) eligibleFrames++;
    const wasActive = buffer.active, gateStart = performance.now();
    const pluck = buffer.push(frame);
    bufferTimes.push(performance.now() - gateStart);
    if (!wasActive && buffer.active) firstTriggerFrame = frames;
    // This is the normal trainer's independent early singleton event.
    if (midi != null && votingPitch.confidence >= .55) {
      const candidates = candidateStringsForMidi(midi);
      if (candidates.length === 1) singletonEvents.push({ midi, string: candidates[0].string,
        frame: frames, elapsed_ms: (offset + frameSize) / sampleRate * 1000 });
    }
    frames++;
    if (pluck) {
      captured = { midi: pluck.midi, pitch_confidence: pluck.pitchConfidence,
        samples: pluck.samples.length, first_trigger_frame: firstTriggerFrame };
      captureMs = (offset + frameSize) / sampleRate * 1000;
      if (pluck.midi != null) {
        const start = performance.now();
        const selected = classifyFusion3({ samples: pluck.samples, sampleRate, midi: pluck.midi, ...bundle(row.midi) });
        inferenceMs = performance.now() - start;
        fusion = { midi: pluck.midi, string: selected.string, model: selected.model,
          confidence: selected.confidence, candidates: candidateStringsForMidi(pluck.midi).length };
      }
      break;
    }
  }
  const early = singletonEvents.find(e => captureMs == null || e.elapsed_ms < captureMs - 1e-6) || null;
  const firstEvent = early || (fusion ? { midi: fusion.midi, string: fusion.string,
    elapsed_ms: captureMs + inferenceMs, source: 'fusion' } : null);
  const onsetMs = leadingSamples / sampleRate * 1000;
  results.push({ file: row.file, true_midi: row.midi, true_string: row.string,
    duration_ms: samples.length / sampleRate * 1000, original_duration_ms: raw.length / sampleRate * 1000,
    onset_ms: onsetMs, frames, captured, capture_ms: captureMs,
    decision_from_onset_ms: fusion ? captureMs + inferenceMs - onsetMs : null,
    eligible_frames: eligibleFrames, max_pitch_confidence: maxPitchConfidence,
    inference_ms: inferenceMs, pitch_compute_ms: pitchTimes, buffer_compute_ms: bufferTimes,
    first_singleton: singletonEvents[0] || null, early_singleton: early,
    first_event: firstEvent, singleton_count: singletonEvents.length,
    fusion, tuple_correct: !!fusion && fusion.midi === row.midi && fusion.string === row.string });
  if (index === 0 || (index + 1) % 25 === 0) console.log(`REPLAY [${index + 1}/${targets.length}]`, { captured: results.filter(r => r.captured).length }, '\n');
}
const allPitch = results.flatMap(r => r.pitch_compute_ms), completed = results.filter(r => r.fusion);
function percentile(a, p) { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor((s.length - 1) * p))] ?? null; }
const report = { phase: flags.includes('--smoke') ? 'smoke' : 'real', detector: hybridStart ? 'correlation-start-yin-votes' : useReferenceYin ? 'referenceYin-rolling240-gate0.55' : 'correlation-frame4096', leading_samples: leadingSamples, recordings: results.length,
  captured: results.filter(r => r.captured).length, classified: completed.length,
  never_eligible: results.filter(r => !r.eligible_frames).length,
  eligible_but_incomplete: results.filter(r => r.eligible_frames && !r.captured).length,
  pitch_correct: completed.filter(r => r.fusion.midi === r.true_midi).length,
  string_correct: completed.filter(r => r.fusion.string === r.true_string).length,
  tuple_correct: results.filter(r => r.tuple_correct).length,
  early_singleton_count: results.filter(r => r.early_singleton).length,
  early_singleton_correct: results.filter(r => r.early_singleton?.midi === r.true_midi && r.early_singleton?.string === r.true_string).length,
  early_singleton_wrong: results.filter(r => r.early_singleton && (r.early_singleton.midi !== r.true_midi || r.early_singleton.string !== r.true_string)).length,
  first_event_correct: results.filter(r => r.first_event?.midi === r.true_midi && r.first_event?.string === r.true_string).length,
  capture_ms_median: percentile(completed.map(r => r.capture_ms), .5),
  inference_ms_median: percentile(completed.map(r => r.inference_ms), .5),
  inference_ms_p95: percentile(completed.map(r => r.inference_ms), .95),
  pitch_compute_ms_median: percentile(allPitch, .5), pitch_compute_ms_p95: percentile(allPitch, .95),
  decision_ms_median: percentile(completed.map(r => r.capture_ms + r.inference_ms), .5),
  decision_ms_p95: percentile(completed.map(r => r.capture_ms + r.inference_ms), .95) };
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify({ report, rows: results }));
console.log(JSON.stringify(report, null, 2));
