import { GuitarMicrophone } from "../audio/microphone.js";
import { midiToNoteName } from "../guitar/notes.js";
import { candidateStringsForMidi } from "../guitar/tuning.js";
import { RingingPluckBuffer } from "../audio/ringing-pluck-buffer.js";
import { extractRingingFeatures } from "../classifier/ringing-features.js";
import { classifyRingingPluck } from "../classifier/full-ringing-classifier.js";

let microphone = null;
const pluckBuffer = new RingingPluckBuffer();
let featureReferencePromise = null;

function loadFeatureReference() {
  if (!featureReferencePromise) {
    featureReferencePromise = Promise.all([
      fetch("/model/ringing_scaler.json").then(r => {
        if (!r.ok) throw new Error("Could not load ringing scaler");
        return r.json();
      }),
      fetch("/model/feature_names.json").then(r => {
        if (!r.ok) throw new Error("Could not load feature names");
        return r.json();
      })
    ]).then(([scaler, names]) => ({ scaler, names }));
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
