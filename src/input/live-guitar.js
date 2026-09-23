import { GuitarMicrophone } from "../audio/microphone.js";
import { midiToNoteName } from "../guitar/notes.js";
import { candidateStringsForMidi } from "../guitar/tuning.js";
import { RingingPluckBuffer } from "../audio/ringing-pluck-buffer.js";
import { extractRingingFeatures } from "../classifier/ringing-features.js";
import { classifyRingingPluck } from "../classifier/full-ringing-classifier.js";

let microphone = null;
const pluckBuffer = new RingingPluckBuffer();
let featureReferencePromise = null;

const FEATURE_STATS = ["mean", "std", "p25", "median", "p75"];
const FEATURE_NAMES = (() => {
  const names = [];
  for (const part of ["attack", "sustain"]) {
    for (let i = 1; i <= 13; i++) {
      names.push(`${part}_mfcc${i}_mean`, `${part}_mfcc${i}_std`);
    }
    for (const descriptor of ["centroid", "bandwidth", "rolloff", "flatness", "zcr"]) {
      for (const stat of FEATURE_STATS) names.push(`${part}_${descriptor}_${stat}`);
    }
  }
  names.push(
    "attack_peak_dbfs",
    "attack_rms_50_dbfs",
    "attack_rms_100_dbfs",
    "attack_energy_100",
    "total_rms_dbfs"
  );
  if (names.length !== 107) throw new Error(`Expected 107 feature names; got ${names.length}`);
  return names;
})();

function loadFeatureReference() {
  if (!featureReferencePromise) {
    featureReferencePromise = fetch("/model/ringing_scaler.json").then(async r => {
      if (!r.ok) throw new Error(`Could not load ringing scaler (${r.status})`);
      const scaler = await r.json();
      if (scaler.mean?.length !== 107 || scaler.scale?.length !== 107) {
        throw new Error("Ringing scaler must contain exactly 107 means and scales");
      }
      return { scaler, names: FEATURE_NAMES };
    });
  }
  return featureReferencePromise;
}

async function summarizeFeatureShift(features) {
  const { scaler, names } = await loadFeatureReference();
  const shifts = Array.from(features, (value, i) => ({
    name: names[i] || `f${i}`,
    z: (value - scaler.mean[i]) / scaler.scale[i]
  })).filter(x => Number.isFinite(x.z));

  shifts.sort((a, b) => Math.abs(b.z) - Math.abs(a.z));
  const extreme = shifts.filter(x => Math.abs(x.z) >= 3).length;
  const top = shifts.slice(0, 5)
    .map(x => `${x.name} ${x.z >= 0 ? "+" : ""}${x.z.toFixed(1)}σ`)
    .join(" · ");
  return `${extreme}/107 ≥3σ · ${top}`;
}

export function setupLiveGuitarInput() {
  const button = document.getElementById("guitarInputButton");
  const status = document.getElementById("guitarInputStatus");
  const note = document.getElementById("guitarDetectedNote");
  const string = document.getElementById("guitarDetectedString");
  const confidence = document.getElementById("guitarConfidence");
  const logBody = document.getElementById("guitarInputLogBody");
  let lastClassificationText = "Classifier: waiting for pluck";
  let currentNoteEvent = null;
  let lastAudibleMidi = null;

  const testButton = document.getElementById("classifierTestButton");
  const skipButton = document.getElementById("classifierTestSkipButton");
  const exportButton = document.getElementById("classifierTestExportButton");
  const testStatus = document.getElementById("classifierTestStatus");
  const openMidis = [27,34,39,44,49,54,58,63];
  let testActive = false;
  let testCases = [];
  let testIndex = 0;
  const testResults = [];
  const TEST_PROGRESS_KEY = "classifier-live-test-progress-v1";

  const datasetButton = document.getElementById("datasetRecordButton");
  const datasetExportButton = document.getElementById("datasetExportButton");
  const datasetStatus = document.getElementById("datasetRecordStatus");

  // Existing ringing dataset already contains soft/normal/hard at these frets.
  // Record only the 18 missing frets per string: 8 * 18 * 3 = 432 samples.
  const EXISTING_DATASET_FRETS = new Set([0, 5, 7, 12, 17, 19, 24]);
  // Measured attack_rms_100_dbfs from the 168 existing ringing WAVs.
  // Each row is frets [0, 5, 7, 12, 17, 19, 24]. Missing frets are
  // predicted by piecewise-linear interpolation on the SAME string/strength.
  const DATASET_ANCHOR_FRETS = [0, 5, 7, 12, 17, 19, 24];
  const DATASET_VOLUME_MAP = {
    soft: [
      [-37.70,-32.30,-31.42,-27.08,-25.18,-26.83,-26.33],
      [-30.00,-28.05,-27.82,-26.06,-24.68,-25.89,-22.15],
      [-31.49,-30.28,-27.26,-31.67,-26.70,-26.91,-28.55],
      [-36.06,-34.83,-36.57,-30.85,-30.32,-28.81,-29.45],
      [-34.86,-40.41,-36.93,-31.00,-30.66,-28.94,-30.90],
      [-30.77,-29.92,-31.08,-26.96,-27.46,-27.10,-25.64],
      [-34.32,-38.55,-31.85,-29.08,-30.91,-30.10,-29.48],
      [-39.49,-39.19,-37.09,-36.86,-38.85,-34.49,-30.70]
    ],
    normal: [
      [-27.57,-25.48,-25.06,-21.74,-19.07,-20.03,-18.64],
      [-25.34,-27.09,-26.55,-19.90,-18.58,-17.84,-16.83],
      [-26.79,-27.44,-23.68,-23.11,-20.11,-20.87,-19.69],
      [-29.71,-29.66,-27.35,-26.33,-25.93,-23.32,-21.48],
      [-32.64,-31.43,-28.33,-27.88,-25.06,-23.48,-21.83],
      [-29.40,-26.88,-23.33,-20.93,-19.02,-18.88,-18.22],
      [-28.52,-26.89,-27.50,-26.63,-24.98,-22.92,-20.19],
      [-30.31,-29.85,-30.20,-27.54,-25.73,-24.54,-19.83]
    ],
    hard: [
      [-23.00,-21.83,-18.72,-20.23,-17.10,-18.75,-16.46],
      [-22.60,-23.24,-23.34,-19.02,-17.01,-14.70,-14.22],
      [-25.02,-23.01,-21.31,-20.35,-19.05,-19.15,-17.65],
      [-26.91,-25.29,-23.41,-21.82,-22.45,-22.34,-18.59],
      [-29.36,-28.48,-24.65,-25.42,-22.42,-22.18,-17.79],
      [-24.30,-22.48,-22.45,-20.87,-18.27,-18.03,-15.01],
      [-29.11,-28.05,-25.44,-25.63,-25.06,-24.84,-19.22],
      [-30.69,-31.60,-30.71,-29.83,-29.95,-26.57,-19.13]
    ]
  };

  // Tolerance comes from leave-one-anchor-out interpolation error across the
  // previous samples (90th percentile absolute error), separately by strength.
  const DATASET_VOLUME_TOLERANCE_DB = {
    soft: 3.72,
    normal: 1.89,
    hard: 2.33
  };

  const expectedDatasetDb = (string, fret, strength) => {
    const values = DATASET_VOLUME_MAP[strength][string - 1];
    let hi = DATASET_ANCHOR_FRETS.findIndex(anchor => anchor > fret);
    if (hi < 0) hi = DATASET_ANCHOR_FRETS.length - 1;
    const lo = Math.max(0, hi - 1);
    const f0 = DATASET_ANCHOR_FRETS[lo], f1 = DATASET_ANCHOR_FRETS[hi];
    const d0 = values[lo], d1 = values[hi];
    if (f0 === f1) return d0;
    return d0 + (d1 - d0) * ((fret - f0) / (f1 - f0));
  };

  // S1/S2 missing frets were already recorded in the previous pass.
  // Continue with one medium take only for the remaining S3-S8 missing frets.
  const DATASET_COMPLETED_STRINGS = new Set([1, 2]);
  const DATASET_STRENGTHS = [
    { key: "normal", label: "medium" }
  ];

  let datasetActive = false;
  let datasetCases = [];
  let datasetIndex = 0;
  const datasetSamples = [];
  let datasetPitchOk = false;
  const DATASET_PITCH_TOLERANCE_SEMITONES = 1;

  const buildDatasetCases = () => {
    const cases = [];
    for (let string = 1; string <= 8; string++) {
      if (DATASET_COMPLETED_STRINGS.has(string)) continue;
      for (let fret = 0; fret <= 24; fret++) {
        if (EXISTING_DATASET_FRETS.has(fret)) continue;
        for (const strength of DATASET_STRENGTHS) {
          // One medium sweet-spot take per remaining position.
          // Preserve the current medium target used in the S1/S2 pass.
          const expectedDb = expectedDatasetDb(string, fret, strength.key) - 6.0;
          const toleranceDb = DATASET_VOLUME_TOLERANCE_DB[strength.key];
          cases.push({
            string,
            fret,
            midi: openMidis[string - 1] + fret,
            ...strength,
            expectedDb,
            minDb: expectedDb - toleranceDb,
            maxDb: expectedDb + toleranceDb
          });
        }
      }
    }
    return cases;
  };

  const updateDatasetStatus = (message = "") => {
    if (!datasetStatus) return;
    if (!datasetActive) {
      datasetStatus.textContent = datasetSamples.length
        ? `Stopped · ${datasetSamples.length}/432 accepted`
        : "108 remaining samples · medium only · S3-S8";
      return;
    }
    const target = datasetCases[datasetIndex];
    if (!target) {
      datasetStatus.textContent = `Complete · ${datasetSamples.length}/${datasetCases.length} accepted`;
      return;
    }
    datasetStatus.textContent =
      `String: ${target.string}\n` +
      `Fret:    ${target.fret}\n` +
      `Pick: ${target.label[0].toUpperCase() + target.label.slice(1)}\n` +
      `Vol: ${message || "—"}`;
  };

  const writeAscii = (view, offset, text) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
  };

  const wavBytes = (samples, sampleRate) => {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);
    writeAscii(view, 0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeAscii(view, 8, "WAVEfmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeAscii(view, 36, "data");
    view.setUint32(40, samples.length * 2, true);
    let offset = 44;
    for (const sample of samples) {
      const value = Math.max(-1, Math.min(1, sample));
      view.setInt16(offset, value < 0 ? value * 32768 : value * 32767, true);
      offset += 2;
    }
    return new Uint8Array(buffer);
  };

  const CRC_TABLE = (() => {
    const table = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = (c & 1) ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      table[n] = c >>> 0;
    }
    return table;
  })();

  const crc32 = bytes => {
    let c = 0xffffffff;
    for (const byte of bytes) c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };

  // Minimal ZIP writer using STORE (no compression), avoiding another runtime dependency.
  const zipBlob = files => {
    const encoder = new TextEncoder();
    const locals = [];
    const centrals = [];
    let offset = 0;
    for (const file of files) {
      const name = encoder.encode(file.name);
      const data = file.bytes;
      const crc = crc32(data);
      const local = new Uint8Array(30 + name.length + data.length);
      const lv = new DataView(local.buffer);
      lv.setUint32(0, 0x04034b50, true);
      lv.setUint16(4, 20, true);
      lv.setUint16(6, 0, true);
      lv.setUint16(8, 0, true);
      lv.setUint32(14, crc, true);
      lv.setUint32(18, data.length, true);
      lv.setUint32(22, data.length, true);
      lv.setUint16(26, name.length, true);
      local.set(name, 30);
      local.set(data, 30 + name.length);
      locals.push(local);

      const central = new Uint8Array(46 + name.length);
      const cv = new DataView(central.buffer);
      cv.setUint32(0, 0x02014b50, true);
      cv.setUint16(4, 20, true);
      cv.setUint16(6, 20, true);
      cv.setUint32(16, crc, true);
      cv.setUint32(20, data.length, true);
      cv.setUint32(24, data.length, true);
      cv.setUint16(28, name.length, true);
      cv.setUint32(42, offset, true);
      central.set(name, 46);
      centrals.push(central);
      offset += local.length;
    }
    const centralOffset = offset;
    const centralSize = centrals.reduce((sum, x) => sum + x.length, 0);
    const end = new Uint8Array(22);
    const ev = new DataView(end.buffer);
    ev.setUint32(0, 0x06054b50, true);
    ev.setUint16(8, files.length, true);
    ev.setUint16(10, files.length, true);
    ev.setUint32(12, centralSize, true);
    ev.setUint32(16, centralOffset, true);
    return new Blob([...locals, ...centrals, end], { type: "application/zip" });
  };

  datasetButton?.addEventListener("click", () => {
    if (datasetActive) {
      datasetActive = false;
      datasetButton.textContent = "Start Recording";
      updateDatasetStatus();
      return;
    }
    datasetCases = buildDatasetCases();
    datasetIndex = datasetSamples.length;
    if (datasetIndex >= datasetCases.length) datasetIndex = 0;
    datasetActive = true;
    datasetPitchOk = false;
    datasetButton.textContent = "Stop Recording";
    updateDatasetStatus();
  });

  datasetExportButton?.addEventListener("click", () => {
    if (!datasetSamples.length) return;
    const files = datasetSamples.map(sample => ({
      name: sample.name,
      bytes: wavBytes(sample.samples, sample.sampleRate)
    }));
    const url = URL.createObjectURL(zipBlob(files));
    const a = document.createElement("a");
    a.href = url;
    a.download = `string-classifier-missing-ringing-${new Date().toISOString().replaceAll(":","-")}.zip`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });


  const saveTestProgress = () => {
    if (!testActive) return;
    localStorage.setItem(TEST_PROGRESS_KEY, JSON.stringify({
      index: testIndex,
      results: testResults
    }));
  };

  const clearTestProgress = () => localStorage.removeItem(TEST_PROGRESS_KEY);

  const buildTestCases = () => {
    const cases = [];
    for (let string = 1; string <= 8; string++) {
      for (let fret = 0; fret <= 24; fret++) {
        const midi = openMidis[string - 1] + fret;
        if (candidateStringsForMidi(midi).length >= 2) cases.push({ string, fret, midi });
      }
    }
    return cases;
  };

  const currentTestCase = () => testActive ? testCases[testIndex] : null;

  const updateTestStatus = () => {
    if (!testStatus) return;
    const t = currentTestCase();
    testStatus.textContent = t
      ? `Test ${testIndex + 1}/${testCases.length}: play S${t.string} F${t.fret} (${midiToNoteName(t.midi)})`
      : testResults.length
        ? `Test stopped · ${testResults.filter(x => x.correct).length}/${testResults.length} correct`
        : "Test: off";
  };

  const stopTest = () => {
    testActive = false;
    if (testButton) testButton.textContent = "Start Test";
    if (skipButton) skipButton.disabled = true;
    updateTestStatus();
  };

  const advanceTest = () => {
    testIndex++;
    if (testIndex >= testCases.length) {
      clearTestProgress();
      stopTest();
    } else {
      saveTestProgress();
      updateTestStatus();
    }
  };

  testButton?.addEventListener("click", () => {
    if (testActive) {
      stopTest();
      return;
    }
    testCases = buildTestCases();
    let saved = JSON.parse(localStorage.getItem(TEST_PROGRESS_KEY) || "null");

    // One-time migration for the test run completed before progress persistence
    // existed. Continue at the exact blocked case instead of restarting S1.
    // One-time recovery for the current interrupted run. The exported data
    // is complete through S8 F19, so stale/legacy progress at or before S6 F21
    // should resume at S8 F20 instead.
    const s6f21Index = testCases.findIndex(
      testCase => testCase.string === 6 && testCase.fret === 21
    );
    const s8f20Index = testCases.findIndex(
      testCase => testCase.string === 8 && testCase.fret === 20
    );
    const staleLegacyProgress = !saved ||
      !Number.isInteger(saved.index) ||
      saved.index <= s6f21Index;

    if (staleLegacyProgress) {
      saved = {
        index: s8f20Index >= 0 ? s8f20Index : Math.max(0, testCases.length - 3),
        results: []
      };
    }

    testIndex = Number.isInteger(saved?.index)
      ? Math.min(Math.max(saved.index, 0), Math.max(0, testCases.length - 1))
      : 0;
    testResults.length = 0;
    if (Array.isArray(saved?.results)) testResults.push(...saved.results);
    testActive = true;
    testButton.textContent = "Stop Test";
    if (skipButton) skipButton.disabled = false;
    saveTestProgress();
    updateTestStatus();
  });

  skipButton?.addEventListener("click", () => {
    const expected = currentTestCase();
    if (!expected) return;
    testResults.push({
      time: new Date().toISOString(),
      expectedString: expected.string,
      expectedFret: expected.fret,
      expectedMidi: expected.midi,
      detectedMidi: "",
      pitchConfidence: "",
      probabilities: ["","","","","","","",""],
      predictedString: "",
      stringConfidence: "",
      correct: false,
      status: "skipped"
    });
    advanceTest();
  });

  exportButton?.addEventListener("click", () => {
    if (!testResults.length) return;
    const header = ["time","expected_string","expected_fret","expected_midi","detected_midi",
      "pitch_confidence","pitch_candidates","p_s1","p_s2","p_s3","p_s4","p_s5","p_s6","p_s7","p_s8",
      "predicted_string","string_confidence","correct","status"];
    const rows = testResults.map(x => [
      x.time,x.expectedString,x.expectedFret,x.expectedMidi,x.detectedMidi,x.pitchConfidence,
      (x.pitchCandidates || []).map(p => `${p.midi}:${Number(p.confidence).toFixed(4)}`).join("|"),
      ...x.probabilities,x.predictedString,x.stringConfidence,x.correct,x.status || "tested"
    ]);
    const csv = [header, ...rows].map(row => row.map(value => {
      const s = String(value ?? "");
      return /[",\n]/.test(s) ? '"' + s.replaceAll('"','""') + '"' : s;
    }).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `classifier-live-test-${new Date().toISOString().replaceAll(":","-")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  });

  const beginNoteEvent = frame => {
    if (frame.midi == null || frame.pitchConfidence < 0.55) return;
    if (lastAudibleMidi !== frame.midi || currentNoteEvent == null) {
      currentNoteEvent = {
        midi: frame.midi,
        timestamp: new Date(),
        pitchConfidence: frame.pitchConfidence,
        pitchCandidates: frame.pitchCandidates || []
      };
    } else {
      if (frame.pitchConfidence >= currentNoteEvent.pitchConfidence) {
        currentNoteEvent.pitchConfidence = frame.pitchConfidence;
        currentNoteEvent.pitchCandidates = frame.pitchCandidates || [];
      }
    }
    lastAudibleMidi = frame.midi;
  };

  const endAudibleNote = () => {
    lastAudibleMidi = null;
  };

  const appendLogRow = async (pluck, result, features) => {
    if (!logBody || pluck.midi == null) return;
    const event = currentNoteEvent?.midi === pluck.midi
      ? currentNoteEvent
      : { midi: pluck.midi, timestamp: new Date(), pitchConfidence: pluck.pitchConfidence };

    const candidateText = (event.pitchCandidates || [])
      .map(x => `${midiToNoteName(x.midi)} ${x.confidence.toFixed(2)}`)
      .join(", ");
    if (candidateText) console.debug("Pitch candidates:", candidateText);

    const row = document.createElement("tr");
    const values = [
      event.timestamp.toLocaleTimeString([], {
        hour: "2-digit", minute: "2-digit", second: "2-digit", fractionalSecondDigits: 3
      }),
      midiToNoteName(pluck.midi),
      String(pluck.midi),
      Math.max(event.pitchConfidence || 0, pluck.pitchConfidence || 0).toFixed(2),
      ...result.probabilities.map(p => p.toFixed(2)),
      `S${result.string} (${result.confidence.toFixed(2)})`
    ];

    const quizState = window.getGuitarTrainerDebugState?.() || {
      prompt: "—", played: "—", remaining: "—"
    };
    let featureShift = "—";
    try {
      featureShift = await summarizeFeatureShift(features);
    } catch (error) {
      featureShift = "diagnostic error";
      console.error("Feature shift diagnostics:", error);
    }
    values.push(
      quizState.prompt,
      `Played: ${quizState.played} | Remaining: ${quizState.remaining}`,
      featureShift
    );
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    }
    logBody.appendChild(row);
    logBody.closest(".guitarInputLogScroll")?.scrollTo({
      top: logBody.closest(".guitarInputLogScroll").scrollHeight,
      behavior: "smooth"
    });
    currentNoteEvent = null;
  };


  window.addEventListener("guitar-manual-fret-click", event => {
    if (!logBody) return;
    const detail = event.detail || {};
    const before = window.getGuitarTrainerDebugState?.() || {
      prompt: "—", played: "—", remaining: "—"
    };

    // Let the trainer's click handler finish first so the row reflects the
    // resulting played/remaining state.
    queueMicrotask(() => {
      const after = window.getGuitarTrainerDebugState?.() || before;
      const row = document.createElement("tr");
      const values = [
        new Date().toLocaleTimeString([], {
          hour: "2-digit", minute: "2-digit", second: "2-digit", fractionalSecondDigits: 3
        }),
        detail.note || (Number.isFinite(detail.midi) ? midiToNoteName(detail.midi) : "—"),
        Number.isFinite(detail.midi) ? String(detail.midi) : "—",
        "MANUAL",
        "—", "—", "—", "—", "—", "—", "—", "—",
        `S${detail.string} F${detail.fret} manual`,
        before.prompt,
        `Played: ${after.played} | Remaining: ${after.remaining}`,
        "—"
      ];
      for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      }
      logBody.appendChild(row);
      const scroll = logBody.closest(".guitarInputLogScroll");
      if (scroll) scroll.scrollTop = scroll.scrollHeight;
    });
  });

  if (!button) return;

  button.addEventListener("click", async () => {
    if (microphone) {
      microphone.stop();
      microphone = null;
      pluckBuffer.reset();
      button.textContent = "Enable";
      status.textContent = "Stopped";
      return;
    }

    button.disabled = true;
    status.textContent = "Requesting microphone…";

    microphone = new GuitarMicrophone({
      fftSize: 4096,
      async onFrame(frame) {
        const completedPluck = pluckBuffer.push(frame);
        if (completedPluck) {
          // Extract exactly 107 full-model features once per completed ringing pluck.
          // Keep extraction off the continuous pitch path so classification is
          // one event per pluck rather than one event per audio callback.
          const features = extractRingingFeatures(
            completedPluck.samples,
            completedPluck.sampleRate
          );

          // Dataset recording is intentionally driven by the prompted physical
          // position, not detected pitch: the current pitch detector is known
          // to octave/subharmonic-error on high frets.
          if (datasetActive) {
            const target = datasetCases[datasetIndex];
            if (target) {
              const attackRms100Dbfs = features[104];
              const volumeOk = attackRms100Dbfs >= target.minDb && attackRms100Dbfs <= target.maxDb;
              if (volumeOk && datasetPitchOk) {
                const name =
                  `s${target.string}_f${String(target.fret).padStart(2, "0")}_${target.key}_ringing.wav`;
                datasetSamples.push({
                  name,
                  samples: new Float32Array(completedPluck.samples),
                  sampleRate: completedPluck.sampleRate,
                  attackRms100Dbfs
                });
                datasetIndex++;
                datasetPitchOk = false;
                if (datasetExportButton) datasetExportButton.disabled = false;
                if (datasetIndex >= datasetCases.length) {
                  datasetActive = false;
                  datasetButton.textContent = "Start Recording";
                  updateDatasetStatus();
                } else {
                  // The check belongs to the sample that was just accepted.
                  // Clear it immediately when advancing to the next prompt.
                  updateDatasetStatus();
                }
              } else {
                const volumeIcon = attackRms100Dbfs < target.minDb
                  ? "🔉"
                  : attackRms100Dbfs > target.maxDb
                    ? "🚨"
                    : "—";
                updateDatasetStatus(volumeIcon);
              }
            }
          }
          window.dispatchEvent(new CustomEvent("guitar-ringing-pluck", {
            detail: { ...completedPluck, features }
          }));
          if (completedPluck.midi != null) {
            try {
              const result = await classifyRingingPluck({
                midi: completedPluck.midi,
                features
              });
              const fret = completedPluck.midi - [27,34,39,44,49,54,58,63][result.string - 1];
              string.textContent = String(result.string);
              const probabilityText = result.probabilities
                .map((p, i) => `S${i + 1} ${p.toFixed(2)}`)
                .join(" · ");
              lastClassificationText =
                "Classifier: " + probabilityText +
                " · picked S" + result.string +
                " (" + result.confidence.toFixed(2) + ")";
              confidence.textContent =
                "Pitch: " + completedPluck.pitchConfidence.toFixed(2) +
                " · " + lastClassificationText;
              window.dispatchEvent(new CustomEvent("guitar-note-detected", {
                detail: {
                  midi: completedPluck.midi,
                  string: result.string,
                  fret,
                  pitchConfidence: completedPluck.pitchConfidence,
                  stringConfidence: result.confidence
                }
              }));
              appendLogRow(completedPluck, result, features);

              const expected = currentTestCase();
              if (expected) {
                const record = {
                  time: new Date().toISOString(),
                  expectedString: expected.string,
                  expectedFret: expected.fret,
                  expectedMidi: expected.midi,
                  detectedMidi: completedPluck.midi,
                  pitchConfidence: completedPluck.pitchConfidence,
                  pitchCandidates: currentNoteEvent?.pitchCandidates || [],
                  probabilities: result.probabilities.map(p => Number(p.toFixed(6))),
                  predictedString: result.string,
                  stringConfidence: result.confidence,
                  correct: completedPluck.midi === expected.midi && result.string === expected.string,
                  status: completedPluck.midi === expected.midi ? "tested" : "pitch_mismatch"
                };
                testResults.push(record);
                saveTestProgress();

                // Advance only when the requested pitch was actually heard.
                // A pitch-detection mistake is recorded but does not silently skip the target.
                if (completedPluck.midi === expected.midi) {
                  advanceTest();
                } else {
                  updateTestStatus();
                }
              }
            } catch (error) {
              console.error("Full ringing classifier:", error);
            }
          }
        }

        if (frame.midi == null || frame.pitchConfidence < 0.55) {
          endAudibleNote();
          note.textContent = "—";
          string.textContent = "—";
          confidence.textContent =
            "Pitch: " + frame.pitchConfidence.toFixed(2) +
            " · " + lastClassificationText;
          return;
        }

        if (datasetActive) {
          const target = datasetCases[datasetIndex];
          if (target && Math.abs(frame.midi - target.midi) <= DATASET_PITCH_TOLERANCE_SEMITONES) {
            datasetPitchOk = true;
          }
        }

        beginNoteEvent(frame);
        note.textContent = midiToNoteName(frame.midi);
        confidence.textContent =
          "Pitch: " + frame.pitchConfidence.toFixed(2) +
          " · " + lastClassificationText;

        const candidates = candidateStringsForMidi(frame.midi);

        // Prefer a physical-string prediction supplied by the full classifier.
        // Until that model is connected, a note is actionable only when pitch
        // leaves exactly one physically possible string. We never guess.
        const resolvedString = Number.isInteger(frame.string)
          ? frame.string
          : candidates.length === 1
            ? candidates[0].string
            : null;

        string.textContent = resolvedString
          ? String(resolvedString)
          : candidates.length
            ? candidates.map(x => x.string).join(" / ")
            : "—";

        window.dispatchEvent(new CustomEvent("guitar-audio-frame", { detail: frame }));

        if (resolvedString) {
          window.dispatchEvent(new CustomEvent("guitar-note-detected", {
            detail: {
              midi: frame.midi,
              string: resolvedString,
              pitchConfidence: frame.pitchConfidence,
              stringConfidence: frame.stringConfidence ?? null
            }
          }));
        }
      }
    });

    try {
      const { sampleRate } = await microphone.start();
      button.textContent = "Disable";
      status.textContent = "Listening · " + sampleRate + " Hz";
    } catch (error) {
      microphone = null;
      status.textContent = "Microphone error: " + error.message;
    } finally {
      button.disabled = false;
    }
  });
}
