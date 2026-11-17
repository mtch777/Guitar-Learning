const keys = [
  { label: "C", count: 0, type: "none", color: "#34A853" },
  { label: "G", count: 1, type: "sharp", color: "#7CB342" },
  { label: "D", count: 2, type: "sharp", color: "#C0CA33" },
  { label: "A", count: 3, type: "sharp", color: "#FDD835" },
  { label: "E", count: 4, type: "sharp", color: "#FFB300" },
  { label: "B", count: 5, type: "sharp", color: "#FB8C00" },
  { label: "F#/Gb", count: 6, type: "sharp", color: "#EA4335", variant: "F#" },
  { label: "F#/Gb", count: 6, type: "flat", color: "#EA4335", variant: "Gb" },
  { label: "Db", count: 5, type: "flat", color: "#7E57C2" },
  { label: "Ab", count: 4, type: "flat", color: "#5C6BC0" },
  { label: "Eb", count: 3, type: "flat", color: "#42A5F5" },
  { label: "Bb", count: 2, type: "flat", color: "#26A69A" },
  { label: "F", count: 1, type: "flat", color: "#5BBE7A" }
];

const SHARP_ORDER = [
  { name: "F#", pitchClass: 6 },
  { name: "C#", pitchClass: 1 },
  { name: "G#", pitchClass: 8 },
  { name: "D#", pitchClass: 3 },
  { name: "A#", pitchClass: 10 },
  { name: "E#", pitchClass: 5 },
  { name: "B#", pitchClass: 0 }
];

const FLAT_ORDER = [
  { name: "Bb", pitchClass: 10 },
  { name: "Eb", pitchClass: 3 },
  { name: "Ab", pitchClass: 8 },
  { name: "Db", pitchClass: 1 },
  { name: "Gb", pitchClass: 6 },
  { name: "Cb", pitchClass: 11 },
  { name: "Fb", pitchClass: 4 }
];

const GREY = "#D6D9DF";
const WRONG = "#E53935";

const svg = document.getElementById("circleSvg");
const midiButton = document.getElementById("midiButton");
const midiConnection = document.getElementById("midiConnection");
const restartButton = document.getElementById("restartButton");
const statusElement = document.getElementById("status");
const sequenceProgress = document.getElementById("sequenceProgress");

const SIZE = 600;
const CX = SIZE / 2;
const CY = SIZE / 2;
const OUTER_R = 250;
const INNER_R = 145;
const visualKeys = [
  { label: "C", color: "#34A853" },
  { label: "G", color: "#7CB342" },
  { label: "D", color: "#C0CA33" },
  { label: "A", color: "#FDD835" },
  { label: "E", color: "#FFB300" },
  { label: "B", color: "#FB8C00" },
  { label: "F#/Gb", color: "#EA4335" },
  { label: "Db", color: "#7E57C2" },
  { label: "Ab", color: "#5C6BC0" },
  { label: "Eb", color: "#42A5F5" },
  { label: "Bb", color: "#26A69A" },
  { label: "F", color: "#5BBE7A" }
];

const ANGLE_PER = 360 / visualKeys.length;

let midiAccess = null;
let currentIndex = null;
let remaining = [];
let solved = new Set();
let locked = false;
let questionNumber = 0;
let answerPosition = 0;
let acceptedSequences = [];
let activeSequences = [];
let wedgePaths = [];
let labels = [];
let checkMarks = [];

function polarToCartesian(cx, cy, radius, angleDeg) {
  const radians = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians)
  };
}

function ringSlicePath(cx, cy, outerR, innerR, startAngle, endAngle) {
  const outerStart = polarToCartesian(cx, cy, outerR, startAngle);
  const outerEnd = polarToCartesian(cx, cy, outerR, endAngle);
  const innerEnd = polarToCartesian(cx, cy, innerR, endAngle);
  const innerStart = polarToCartesian(cx, cy, innerR, startAngle);

  return [
    "M " + outerStart.x + " " + outerStart.y,
    "A " + outerR + " " + outerR + " 0 0 1 " + outerEnd.x + " " + outerEnd.y,
    "L " + innerEnd.x + " " + innerEnd.y,
    "A " + innerR + " " + innerR + " 0 0 0 " + innerStart.x + " " + innerStart.y,
    "Z"
  ].join(" ");
}

function makeSvg(tag, attrs) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);

  Object.entries(attrs || {}).forEach(([key, value]) => {
    node.setAttribute(key, value);
  });

  return node;
}

function drawCircle() {
  svg.innerHTML = "";
  wedgePaths = [];
  labels = [];
  checkMarks = [];

  visualKeys.forEach((key, index) => {
    const centerAngle = index * ANGLE_PER;
    const startAngle = centerAngle - ANGLE_PER / 2;
    const endAngle = centerAngle + ANGLE_PER / 2;

    const path = makeSvg("path", {
      d: ringSlicePath(CX, CY, OUTER_R, INNER_R, startAngle, endAngle),
      fill: GREY,
      class: "wedge"
    });

    svg.appendChild(path);
    wedgePaths.push(path);

    const point = polarToCartesian(
      CX,
      CY,
      (OUTER_R + INNER_R) / 2,
      centerAngle
    );

    const label = makeSvg("text", {
      x: point.x,
      y: point.y,
      class: "key-label",
      "font-size": key.label === "F#/Gb" ? 17 : 23
    });

    label.textContent = key.label;
    label.style.display = "none";
    svg.appendChild(label);
    labels.push(label);

    const check = makeSvg("text", {
      x: point.x,
      y: point.y,
      class: "check"
    });

    check.textContent = "✓";
    check.style.display = "none";
    svg.appendChild(check);
    checkMarks.push(check);
  });

  const center = makeSvg("circle", {
    cx: CX,
    cy: CY,
    r: INNER_R - 8,
    class: "center-disc"
  });

  svg.appendChild(center);
}

function setStatus(text, type) {
  statusElement.textContent = text;
  statusElement.className = "status" + (type ? " " + type : "");
}

function setMidiConnection(connected) {
  if (!midiConnection) return;

  midiConnection.textContent = connected
    ? "🟢 Keyboard connected"
    : "🔴 Waiting for keyboard input";

  midiConnection.classList.toggle("connected", connected);
}

function getSequencesForKey(key) {
  if (key.type === "sharp") {
    return [SHARP_ORDER.slice(0, key.count)];
  }

  if (key.type === "flat") {
    return [FLAT_ORDER.slice(0, key.count)];
  }

  return [];
}

function resetAnswerProgress() {
  answerPosition = 0;
  acceptedSequences = getSequencesForKey(keys[currentIndex]);
  activeSequences = acceptedSequences.slice();
  renderSequenceProgress();
}

function renderSequenceProgress() {
  if (currentIndex === null) {
    sequenceProgress.textContent = "";
    return;
  }

  const targetCount = keys[currentIndex].count;
  const completed = answerPosition;

  sequenceProgress.textContent =
    completed + " / " + targetCount + " accidentals";
}

function getVisualIndexForQuestion(index) {
  const key = keys[index];

  if (key.variant === "F#" || key.variant === "Gb") {
    return 6;
  }

  if (index <= 5) {
    return index;
  }

  return index - 1;
}

function resetLesson() {
  remaining = keys
    .map((_, index) => index)
    .filter((index) => keys[index].count > 0);

  solved = new Set();
  locked = false;
  currentIndex = null;
  questionNumber = 0;
  answerPosition = 0;
  restartButton.hidden = true;

  wedgePaths.forEach((path) => path.setAttribute("fill", GREY));
  labels.forEach((label) => (label.style.display = "none"));
  checkMarks.forEach((check) => (check.style.display = "none"));

  if (midiAccess) {
    nextQuestion();
  } else {
    setStatus("Waiting for keyboard input…", "");
    sequenceProgress.textContent = "";
  }
}

function randomRemainingIndex() {
  const position = Math.floor(Math.random() * remaining.length);
  return remaining[position];
}

function currentPrompt() {
  const key = keys[currentIndex];

  if (key.type === "sharp") {
    return key.variant === "F#"
      ? "F# · Play the sharps in order"
      : "Play the sharps in order";
  }

  if (key.type === "flat") {
    return key.variant === "Gb"
      ? "Gb · Play the flats in order"
      : "Play the flats in order";
  }

  return "";
}

function nextQuestion() {
  if (remaining.length === 0) {
    currentIndex = null;
    locked = true;
    sequenceProgress.textContent = "";
    setStatus("Complete ✓", "success");
    restartButton.hidden = false;
    return;
  }

  currentIndex = randomRemainingIndex();
  questionNumber += 1;
  locked = false;

  wedgePaths.forEach((path, visualIndex) => {
    if (checkMarks[visualIndex].style.display === "none") {
      path.setAttribute("fill", GREY);
    }
  });

  labels.forEach((label, visualIndex) => {
    if (checkMarks[visualIndex].style.display === "none") {
      label.style.display = "none";
    }
  });

  const visualIndex = getVisualIndexForQuestion(currentIndex);

  wedgePaths[visualIndex].setAttribute("fill", keys[currentIndex].color);
  labels[visualIndex].style.display = "block";

  resetAnswerProgress();

  setStatus(
    currentPrompt() + " · Question " + questionNumber + " of 12",
    ""
  );
}

function attachMidiInputs() {
  const inputs = Array.from(midiAccess.inputs.values());

  inputs.forEach((input) => {
    input.onmidimessage = handleMidiMessage;
  });

  if (inputs.length === 0) {
    setStatus("No MIDI keyboard connected", "error");
    setMidiConnection(false);
    return false;
  }

  setMidiConnection(true);
  return true;
}

function handleMidiMessage(event) {
  const statusByte = event.data[0];
  const noteNumber = event.data[1];
  const velocity = event.data[2];
  const command = statusByte & 0xf0;

  if (
    command !== 0x90 ||
    velocity === 0 ||
    locked ||
    currentIndex === null
  ) {
    return;
  }

  const playedPitchClass = noteNumber % 12;

  activeSequences = activeSequences.filter(
    (sequence) =>
      sequence[answerPosition] &&
      sequence[answerPosition].pitchClass === playedPitchClass
  );

  if (activeSequences.length === 0) {
    handleWrong();
    return;
  }

  answerPosition += 1;
  renderSequenceProgress();

  const targetCount = keys[currentIndex].count;

  if (answerPosition === targetCount) {
    handleCorrect();
  }
}

function handleWrong() {
  locked = true;

  const visualIndex = getVisualIndexForQuestion(currentIndex);
  const path = wedgePaths[visualIndex];
  const originalColor = keys[currentIndex].color;

  path.setAttribute("fill", WRONG);
  setStatus("Wrong · start the sequence again", "error");

  window.setTimeout(() => {
    path.setAttribute("fill", originalColor);
    resetAnswerProgress();
    setStatus(currentPrompt(), "");
    locked = false;
  }, 350);
}

function handleCorrect() {
  locked = true;

  const solvedIndex = currentIndex;
  const visualIndex = getVisualIndexForQuestion(solvedIndex);

  wedgePaths[visualIndex].setAttribute("fill", GREY);
  labels[visualIndex].style.display = "none";

  solved.add(solvedIndex);

  remaining = remaining.filter(
    (index) => index !== solvedIndex
  );

  const isSharedCenter = visualIndex === 6;
  const otherSharedQuestionRemaining =
    isSharedCenter &&
    remaining.some((index) => getVisualIndexForQuestion(index) === 6);

  if (!otherSharedQuestionRemaining) {
    checkMarks[visualIndex].style.display = "block";
  }

  setStatus("Correct ✓", "success");

  window.setTimeout(() => {
    nextQuestion();
  }, 450);
}

midiButton.addEventListener("click", async () => {
  if (!navigator.requestMIDIAccess) {
    setStatus("Web MIDI is not supported in this browser", "error");
    return;
  }

  try {
    setStatus("Waiting for keyboard input…", "");

    midiAccess = await navigator.requestMIDIAccess({
      sysex: false
    });

    midiAccess.onstatechange = () => {
      attachMidiInputs();
    };

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

    resetLesson();
  } catch (error) {
    setStatus("Waiting for keyboard input…", "");
  }
});

restartButton.addEventListener("click", resetLesson);

if (midiConnection) {
  midiConnection.addEventListener("click", () => {
    if (typeof connectMidi === "function") {
      connectMidi(true);
    } else if (midiButton) {
      midiButton.click();
    }
  });
}

if (window.PracticeMIDI) {
  window.PracticeMIDI.watchButton(midiButton);
}

drawCircle();

if (typeof connectMidi === "function") {
  connectMidi(false);
} else {
  window.setTimeout(() => midiButton.click(), 0);
}
resetLesson();
