import { GuitarMicrophone } from "../audio/microphone.js";
import { midiToNoteName } from "../guitar/notes.js";
import { candidateStringsForMidi } from "../guitar/tuning.js";

let microphone = null;

export function setupLiveGuitarInput() {
  const button = document.getElementById("guitarInputButton");
  const status = document.getElementById("guitarInputStatus");
  const note = document.getElementById("guitarDetectedNote");
  const string = document.getElementById("guitarDetectedString");
  const confidence = document.getElementById("guitarConfidence");

  if (!button) return;

  button.addEventListener("click", async () => {
    if (microphone) {
      microphone.stop();
      microphone = null;
      button.textContent = "Enable";
      status.textContent = "Stopped";
      return;
    }

    button.disabled = true;
    status.textContent = "Requesting microphone…";

    microphone = new GuitarMicrophone({
      fftSize: 4096,
      onFrame(frame) {
        if (frame.midi == null || frame.pitchConfidence < 0.55) {
          note.textContent = "—";
          string.textContent = "—";
          confidence.textContent = "Pitch: " + frame.pitchConfidence.toFixed(2);
          return;
        }

        note.textContent = midiToNoteName(frame.midi);
        confidence.textContent = "Pitch: " + frame.pitchConfidence.toFixed(2);

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
