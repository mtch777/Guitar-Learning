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
      button.textContent = "Start Guitar Input";
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

        // Classifier attaches here next. Until it is loaded, show only
        // physically possible strings; never invent a string prediction.
        const candidates = candidateStringsForMidi(frame.midi);
        string.textContent = candidates.length
          ? candidates.map(x => x.string).join(" / ")
          : "—";

        window.dispatchEvent(new CustomEvent("guitar-audio-frame", { detail: frame }));
      }
    });

    try {
      const { sampleRate } = await microphone.start();
      button.textContent = "Stop Guitar Input";
      status.textContent = "Listening · " + sampleRate + " Hz";
    } catch (error) {
      microphone = null;
      status.textContent = "Microphone error: " + error.message;
    } finally {
      button.disabled = false;
    }
  });
}
