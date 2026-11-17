const NOTE_NAMES = [
  "C", "C#", "D", "D#", "E", "F",
  "F#", "G", "G#", "A", "A#", "B"
];

const MAJOR_TRIAD_INTERVALS = [0, 4, 7];

const MIDI_MIN = 21;
const MIDI_MAX = 108;
const MAX_START_MIDI = MIDI_MAX - 7;

const rootName = document.getElementById("rootName");
const statusElement = document.getElementById("status");
const midiButton = document.getElementById("midiButton");
const newTriadButton = document.getElementById("newTriadButton");
const keyboard = document.getElementById("keyboard");
const progressText = document.getElementById("progressText");

let midiAccess = null;
let targetPitchClass = null;
let startMidi = null;
let expectedSequence = [];
let nextIndex = 0;
let correctNotes = new Set();
let keyElements = new Map();
let wrongTimer = null;
let lastRootPitchClass = null;
let finished = false;

function setStatus(text, type) {
  statusElement.textContent = text;
  statusElement.className = "status" + (type ? " " + type : "");
}

function chooseRandomRoot() {
  let next;

  do {
    next = Math.floor(Math.random() * 12);
  } while (next === lastRootPitchClass && lastRootPitchClass !== null);

  lastRootPitchClass = next;
  targetPitchClass = next;

  startMidi = null;
  expectedSequence = [];
  nextIndex = 0;
  correctNotes = new Set();
  finished = false;

  rootName.textContent = NOTE_NAMES[targetPitchClass];
  progressText.textContent = "0 / 3";

  renderPreviewKeyboard();

  if (midiAccess) {
    setStatus(
      "Play " + NOTE_NAMES[targetPitchClass] + " in any octave to start",
      ""
    );
  } else {
    setStatus("Enable MIDI to start", "");
  }
}

function noteNameWithOctave(midi) {
  const name = NOTE_NAMES[midi % 12];
  const octave = Math.floor(midi / 12) - 1;
  return name + octave;
}

function isBlack(pitchClass) {
  return [1, 3, 6, 8, 10].includes(pitchClass);
}

function buildTriad(start) {
  return MAJOR_TRIAD_INTERVALS.map((interval) => start + interval);
}

function getDisplayRangeForStart(start) {
  const octaveC = start - (start % 12);

  return {
    from: Math.max(MIDI_MIN, octaveC),
    to: Math.min(MIDI_MAX, octaveC + 11)
  };
}

function getPreviewRange() {
  return { from: 48, to: 83 };
}

function renderPreviewKeyboard() {
  const range = startMidi === null
    ? getPreviewRange()
    : getDisplayRangeForStart(startMidi);

  renderKeyboard(range.from, range.to);
}

function renderKeyboard(from, to) {
  keyboard.innerHTML = "";
  keyElements = new Map();

  const whiteMidis = [];

  for (let midi = from; midi <= to; midi++) {
    if (!isBlack(midi % 12)) {
      whiteMidis.push(midi);
    }
  }

  const whiteCount = whiteMidis.length;
  const whiteWidth = 100 / whiteCount;
  const whiteIndexByMidi = new Map();

  whiteMidis.forEach((midi, index) => {
    whiteIndexByMidi.set(midi, index);

    const key = document.createElement("div");
    key.className = "key white";
    key.dataset.midi = midi;
    key.style.left = (index * whiteWidth) + "%";
    key.style.width = whiteWidth + "%";

    const label = document.createElement("span");
    label.className = "key-label";

    if (midi % 12 === 0) {
      label.textContent = noteNameWithOctave(midi);
    }

    key.appendChild(label);
    keyboard.appendChild(key);
    keyElements.set(midi, key);
  });

  for (let midi = from; midi <= to; midi++) {
    if (!isBlack(midi % 12)) continue;

    let previousWhite = midi - 1;

    while (previousWhite >= from && isBlack(previousWhite % 12)) {
      previousWhite--;
    }

    const previousIndex = whiteIndexByMidi.get(previousWhite);

    if (previousIndex === undefined) continue;

    const key = document.createElement("div");
    key.className = "key black";
    key.dataset.midi = midi;

    const blackWidth = whiteWidth * 0.62;
    const center = (previousIndex + 1) * whiteWidth;

    key.style.left = (center - blackWidth / 2) + "%";
    key.style.width = blackWidth + "%";

    keyboard.appendChild(key);
    keyElements.set(midi, key);
  }

  correctNotes.forEach((midi) => {
    const key = keyElements.get(midi);
    if (key) key.classList.add("correct");
  });
}

function attachMidiInputs() {
  if (!midiAccess) return false;

  const inputs = Array.from(midiAccess.inputs.values());

  inputs.forEach((input) => {
    input.onmidimessage = handleMidiMessage;
  });

  if (inputs.length === 0) {
    setStatus("No MIDI keyboard connected", "error");
    return false;
  }

  return true;
}

function handleMidiMessage(event) {
  const statusByte = event.data[0];
  const noteNumber = event.data[1];
  const velocity = event.data[2];
  const command = statusByte & 0xf0;

  if (command !== 0x90 || velocity === 0 || finished) {
    return;
  }

  if (startMidi === null) {
    handleStartingNote(noteNumber);
    return;
  }

  handleTriadNote(noteNumber);
}

function handleStartingNote(noteNumber) {
  if (
    noteNumber < MIDI_MIN ||
    noteNumber > MAX_START_MIDI ||
    noteNumber % 12 !== targetPitchClass
  ) {
    flashWrong(noteNumber);
    setStatus(
      "Start on " + NOTE_NAMES[targetPitchClass] + " in any usable octave",
      "error"
    );
    return;
  }

  startMidi = noteNumber;
  expectedSequence = buildTriad(startMidi);
  nextIndex = 1;
  correctNotes = new Set([startMidi]);

  renderPreviewKeyboard();
  markCorrect(startMidi);

  progressText.textContent = "1 / 3";
  setStatus("Continue upward from " + noteNameWithOctave(startMidi), "");
}

function handleTriadNote(noteNumber) {
  const expected = expectedSequence[nextIndex];

  if (noteNumber !== expected) {
    flashWrong(noteNumber);
    setStatus("Wrong — keep the same triad position", "error");
    return;
  }

  markCorrect(noteNumber);
  correctNotes.add(noteNumber);
  nextIndex += 1;

  progressText.textContent = nextIndex + " / 3";

  if (nextIndex >= expectedSequence.length) {
    finished = true;
    setStatus(
      NOTE_NAMES[targetPitchClass] + " major triad complete ✓",
      "success"
    );

    window.setTimeout(() => {
      if (window.PracticeMIDI) {
  window.PracticeMIDI.watchButton(midiButton);
}

chooseRandomRoot();
    }, 700);

    return;
  }

  setStatus("Correct", "success");
}

function markCorrect(midi) {
  const key = keyElements.get(midi);

  if (key) {
    key.classList.remove("wrong");
    key.classList.add("correct");
  }
}

function flashWrong(midi) {
  const key = keyElements.get(midi);

  if (!key && startMidi === null) {
    const c = midi - (midi % 12);

    renderKeyboard(
      Math.max(MIDI_MIN, c),
      Math.min(MIDI_MAX, c + 11)
    );
  }

  const visibleKey = keyElements.get(midi);
  if (!visibleKey) return;

  const wasCorrect = correctNotes.has(midi);

  visibleKey.classList.remove("correct");
  visibleKey.classList.add("wrong");

  if (wrongTimer) {
    window.clearTimeout(wrongTimer);
  }

  wrongTimer = window.setTimeout(() => {
    visibleKey.classList.remove("wrong");

    if (wasCorrect) {
      visibleKey.classList.add("correct");
    }
  }, 320);
}

midiButton.addEventListener("click", async () => {
  if (!navigator.requestMIDIAccess) {
    setStatus("Web MIDI is not supported in this browser", "error");
    return;
  }

  try {
    setStatus("Connecting MIDI…", "");

    midiAccess = await navigator.requestMIDIAccess({
      sysex: false
    });

    midiAccess.onstatechange = attachMidiInputs;

    if (!attachMidiInputs()) {
      return;
    }

    if (window.PracticeMIDI) {
      window.PracticeMIDI.setEnabled(true);
      window.PracticeMIDI.syncButton(midiButton);
    } else {
      midiButton.textContent = "MIDI enabled";
      midiButton.disabled = true;
    }

    setStatus(
      "Play " + NOTE_NAMES[targetPitchClass] + " in any octave to start",
      ""
    );
  } catch (error) {
    setStatus("MIDI access failed", "error");
  }
});

newTriadButton.addEventListener("click", chooseRandomRoot);

chooseRandomRoot();

if (window.PracticeMIDI && window.PracticeMIDI.isEnabled()) {
  window.setTimeout(() => {
    midiButton.disabled = false;
    midiButton.click();
  }, 0);
}
