import { extractRingingFeatures, prepareRingingAudio } from './ringing-features.js';
import { harmonicFusionFeatures } from './harmonic-fusion-features.js';
import { earlyMfccFusionFeatures } from './early-mfcc-fusion-features.js';
import { maskFusionProbabilities, predictFusionModel } from './xgboost-fusion-model.js';
import { chooseIsotonicFusion, FUSION_MODELS } from './isotonic-fusion.js';

export async function loadFusion3Bundle(baseUrl) {
  const base = baseUrl.replace(/\/$/, '');
  const names = [...FUSION_MODELS, 'calibrators'];
  const entries = await Promise.all(names.map(async name => {
    const response = await fetch(`${base}/${name}.json`);
    if (!response.ok) throw new Error(`Fusion3 ${name} missing (${response.status})`);
    return [name, await response.json()];
  }));
  const loaded = Object.fromEntries(entries);
  const { calibrators, ...models } = loaded;
  return { models, calibrators };
}

// Experimental complete inference path. Caller supplies exported model bundles
// and isotonic calibrators, and handles pitch/onset gating separately.
export function classifyFusion3({ samples, sampleRate, midi, models, calibrators, preprocessed = false }) {
  if (!Number.isInteger(midi)) throw new Error('Fusion3 requires a detected MIDI');
  if (preprocessed && sampleRate !== 22050) throw new Error('Preprocessed audio must be 22,050 Hz');
  const y = preprocessed ? samples : prepareRingingAudio(samples, sampleRate);
  const baseline = extractRingingFeatures(y, 22050, { preprocessed: true });
  const features = {
    baseline,
    harmonic: [...baseline, ...harmonicFusionFeatures(y, 22050, midi)],
    mfcc: earlyMfccFusionFeatures(y)
  };
  const raw = {}, masked = {};
  for (const name of FUSION_MODELS) {
    raw[name] = predictFusionModel(models[name], features[name]);
    masked[name] = maskFusionProbabilities(raw[name], midi);
  }
  const preds = FUSION_MODELS.map(name => masked[name].indexOf(Math.max(...masked[name])) + 1);
  const confs = FUSION_MODELS.map(name => Math.max(...masked[name]));
  const selected = chooseIsotonicFusion(FUSION_MODELS.map(name => calibrators[name]), preds, confs);
  return { ...selected, raw, masked, predictions: Object.fromEntries(FUSION_MODELS.map((name, i) => [name, preds[i]])) };
}
