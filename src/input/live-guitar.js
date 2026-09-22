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
      "pitch_confidence","p_s1","p_s2","p_s3","p_s4","p_s5","p_s6","p_s7","p_s8",
      "predicted_string","string_confidence","correct","status"];
    const rows = testResults.map(x => [
      x.time,x.expectedString,x.expectedFret,x.expectedMidi,x.detectedMidi,x.pitchConfidence,
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
        pitchConfidence: frame.pitchConfidence
      };
    } else {
      currentNoteEvent.pitchConfidence = Math.max(
        currentNoteEvent.pitchConfidence,
        frame.pitchConfidence
      );
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
