import { maskProbabilitiesByPitch } from "./candidate-strings.js";

/**
 * Browser inference boundary.
 *
 * The full ringing-only model and the exact matching feature extractor
 * will be connected here. Do not substitute the old reduced-feature
 * CodePen model.
 */
export async function classifyPhysicalString({ midi, features, model }) {
  if (!model) throw new Error("Full ringing-only classifier is not loaded.");
  const rawProbabilities = await model.predict(features);
  const probabilities = maskProbabilitiesByPitch(rawProbabilities, midi);

  let bestIndex = 0;
  for (let i = 1; i < probabilities.length; i++) {
    if (probabilities[i] > probabilities[bestIndex]) bestIndex = i;
  }

  return {
    string: bestIndex + 1,
    confidence: probabilities[bestIndex],
    probabilities
  };
}
