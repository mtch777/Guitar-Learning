import { maskProbabilitiesByPitch } from "./candidate-strings.js";

const MODEL_CHUNKS = [
  "/model/ringing_xgboost.b64.00",
  "/model/ringing_xgboost.b64.01",
  "/model/ringing_xgboost.b64.02",
  "/model/ringing_xgboost.b64.03a",
  "/model/ringing_xgboost.b64.03b",
  "/model/ringing_xgboost.b64.04",
  "/model/ringing_xgboost.b64.05"
];
const SCALER_URL = "/model/ringing_scaler.json";

let loaded = null;

function softmax(scores) {
  const m = Math.max(...scores);
  const e = scores.map(x => Math.exp(x - m));
  const s = e.reduce((a, b) => a + b, 0);
  return e.map(x => x / s);
}

function base64ToBuffer(base64) {
  const binary = atob(base64.replace(/\s+/g, ""));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

function readModel(buffer) {
  const v = new DataView(buffer);
  let p = 0;
  const treeCount = v.getUint16(p, true);
  p += 2;
  const trees = [];
  for (let t = 0; t < treeCount; t++) {
    const cls = v.getUint8(p++);
    const n = v.getUint8(p++);
    const nodes = [];
    for (let i = 0; i < n; i++) {
      const feature = v.getUint8(p++);
      const value = v.getFloat32(p, true);
      p += 4;
      if (feature === 255) {
        nodes.push({ leaf: value });
      } else {
        nodes.push({
          feature,
          threshold: value,
          left: v.getUint8(p++),
          right: v.getUint8(p++)
        });
      }
    }
    trees.push({ cls, nodes });
  }
  if (trees.length !== 800) {
    throw new Error(`Expected 800 XGBoost trees; loaded ${trees.length}.`);
  }
  if (p !== buffer.byteLength) {
    throw new Error(`Model byte count mismatch: parsed ${p} of ${buffer.byteLength}.`);
  }
  return trees;
}

function treeValue(tree, x) {
  let i = 0;
  for (;;) {
    const n = tree.nodes[i];
    if (n.leaf !== undefined) return n.leaf;
    const value = x[n.feature];
    i = (Number.isNaN(value) || value < n.threshold) ? n.left : n.right;
  }
}

async function fetchModelBuffer() {
  const responses = await Promise.all(MODEL_CHUNKS.map(url => fetch(url)));
  responses.forEach((response, i) => {
    if (!response.ok) {
      throw new Error(`Full classifier model chunk ${i} missing (${response.status}).`);
    }
  });
  const chunks = await Promise.all(responses.map(response => response.text()));
  return base64ToBuffer(chunks.join(""));
}

export async function loadFullRingingClassifier() {
  if (loaded) return loaded;

  const [buffer, scalerResponse] = await Promise.all([
    fetchModelBuffer(),
    fetch(SCALER_URL)
  ]);

  if (!scalerResponse.ok) {
    throw new Error(`Full classifier scaler missing (${scalerResponse.status}).`);
  }

  const scaler = await scalerResponse.json();
  const trees = readModel(buffer);

  if (scaler.mean.length !== 107 || scaler.scale.length !== 107) {
    throw new Error("Classifier scaler must contain 107 features.");
  }

  loaded = { trees, scaler };
  return loaded;
}

export async function classifyRingingPluck({ midi, features }) {
  if (features?.length !== 107) {
    throw new Error(`Expected 107 features; got ${features?.length ?? 0}`);
  }

  const { trees, scaler } = await loadFullRingingClassifier();
  const x = Array.from(
    features,
    (v, i) => (v - scaler.mean[i]) / scaler.scale[i]
  );

  const scores = Array(8).fill(0);
  for (const tree of trees) scores[tree.cls] += treeValue(tree, x);

  const raw = softmax(scores);
  const probabilities = maskProbabilitiesByPitch(raw, midi);

  let best = 0;
  for (let i = 1; i < 8; i++) {
    if (probabilities[i] > probabilities[best]) best = i;
  }

  return {
    string: best + 1,
    confidence: probabilities[best],
    probabilities
  };
}
