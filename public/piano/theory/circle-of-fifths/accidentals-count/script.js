const keys = [
  { label: "C", count: 0, type: "none", color: "#34A853" },
  { label: "G", count: 1, type: "sharp", color: "#7CB342" },
  { label: "D", count: 2, type: "sharp", color: "#C0CA33" },
  { label: "A", count: 3, type: "sharp", color: "#FDD835" },
  { label: "E", count: 4, type: "sharp", color: "#FFB300" },
  { label: "B", count: 5, type: "sharp", color: "#FB8C00" },
  { label: "F#/Gb", count: 6, type: "either", color: "#EA4335" },
  { label: "Db", count: 5, type: "flat", color: "#7E57C2" },
  { label: "Ab", count: 4, type: "flat", color: "#5C6BC0" },
  { label: "Eb", count: 3, type: "flat", color: "#42A5F5" },
  { label: "Bb", count: 2, type: "flat", color: "#26A69A" },
  { label: "F", count: 1, type: "flat", color: "#5BBE7A" }
];

const ANSWER_PITCH_CLASS = {
  0: 0,  // C
  1: 2,  // D
  2: 4,  // E
  3: 5,  // F
  4: 7,  // G
  5: 9,  // A
  6: 11  // B
};

const GREY = "#D6D9DF";
const WRONG = "#E53935";

const svg = document.getElementById("circleSvg");
const midiButton = document.getElementById("midiButton");
const restartButton = document.getElementById("restartButton");
const statusElement = document.getElementById("status");

const SIZE = 600;
const CX = SIZE / 2;
const CY = SIZE / 2;
const OUTER_R = 250;
const INNER_R = 145;
const ANGLE_PER = 360 / keys.length;

let midiAccess = null;
let currentIndex = null;
let remaining = [];
let solved = new Set();
let locked = false;
let questionNumber = 0;
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
  const node = document.createElementNS(
    "http://www.w3.org/2000/svg",
    tag
  );

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

  keys.forEach((key, index) => {
    const centerAngle = index * ANGLE_PER;
    const startAngle = centerAngle - ANGLE_PER / 2;
    const endAngle = centerAngle + ANGLE_PER / 2;

    const path = makeSvg("path", {
      d: ringSlicePath(
        CX,
        CY,
        OUTER_R,
        INNER_R,
        startAngle,
        endAngle
      ),
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
  statusElement.className =
    "status" + (type ? " " + type : "");
}

function setMidiConnection(connected) {
  midiButton.textContent = connected
    ? "🟢 MIDI connected"
    : "🔴 Enable MIDI";
  midiButton.classList.toggle("connected", connected);
  midiButton.disabled = connected;
}

function resetLesson() {
  remaining = keys.map((_, index) => index);

  solved = new Set();
  locked = false;
  currentIndex = null;
  questionNumber = 0;
  restartButton.hidden = true;

  wedgePaths.forEach((path) => {
    path.setAttribute("fill", GREY);
  });

  labels.forEach((label) => {
    label.style.display = "none";
  });

  checkMarks.forEach((check) => {
    check.style.display = "none";
  });

  if (midiAccess) {
    nextQuestion();
  } else {
    setStatus("Waiting for keyboard input…", "");
  }
}

function randomRemainingIndex() {
  const position =
    Math.floor(Math.random() * remaining.length);

  return remaining[position];
}

function currentPrompt() {
  const key = keys[currentIndex];

  if (key.type === "sharp") {
    return "How many sharps?";
  }

  if (key.type === "flat") {
    return "How many flats?";
  }

  return "How many sharps / flats?";
}

function nextQuestion() {
  if (remaining.length === 0) {
    currentIndex = null;
    locked = true;
    setStatus("Complete ✓", "success");
    restartButton.hidden = false;
    return;
  }

  currentIndex = randomRemainingIndex();
  questionNumber += 1;
  locked = false;

  wedgePaths.forEach((path, index) => {
    if (!solved.has(index)) {
      path.setAttribute("fill", GREY);
    }
  });

  labels.forEach((label, index) => {
    if (!solved.has(index)) {
      label.style.display = "none";
    }
  });

  wedgePaths[currentIndex].setAttribute(
    "fill",
    keys[currentIndex].color
  );

  labels[currentIndex].style.display = "block";

  setStatus(
    currentPrompt() +
      " · Question " +
      questionNumber +
      " of 12",
    ""
  );
}

function attachMidiInputs() {
  const inputs =
    Array.from(midiAccess.inputs.values());

  inputs.forEach((input) => {
    input.onmidimessage = handleMidiMessage;
  });

  if (inputs.length === 0) {
    setStatus(
      "No MIDI keyboard connected",
      "error"
    );
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

  const playedPitchClass =
    noteNumber % 12;

  const targetCount =
    keys[currentIndex].count;

  const expectedPitchClass =
    ANSWER_PITCH_CLASS[targetCount];

  if (playedPitchClass === expectedPitchClass) {
    handleCorrect();
  } else {
    handleWrong();
  }
}

function handleWrong() {
  locked = true;

  const path =
    wedgePaths[currentIndex];

  const originalColor =
    keys[currentIndex].color;

  path.setAttribute("fill", WRONG);
  setStatus("Wrong", "error");

  window.setTimeout(() => {
    path.setAttribute(
      "fill",
      originalColor
    );

    setStatus(
      currentPrompt(),
      ""
    );

    locked = false;
  }, 300);
}

function handleCorrect() {
  locked = true;

  const solvedIndex =
    currentIndex;

  wedgePaths[solvedIndex].setAttribute(
    "fill",
    GREY
  );

  labels[solvedIndex].style.display =
    "none";

  checkMarks[solvedIndex].style.display =
    "block";

  solved.add(solvedIndex);

  remaining =
    remaining.filter(
      (index) => index !== solvedIndex
    );

  setStatus(
    "Correct ✓",
    "success"
  );

  window.setTimeout(() => {
    nextQuestion();
  }, 450);
}

async function connectMidi() {
    if (!navigator.requestMIDIAccess) {
      setStatus(
        "Web MIDI is not supported in this browser",
        "error"
      );
      return;
    }

    try {
      setStatus(
        "Connecting MIDI…",
        ""
      );

      midiAccess =
        await navigator.requestMIDIAccess({
          sysex: false
        });

      midiAccess.onstatechange = () => {
        attachMidiInputs();
      };

      if (!attachMidiInputs()) {
        return;
      }
    setMidiConnection(true);
    if (window.PracticeMIDI) {
      window.PracticeMIDI.setEnabled(true);
    }

      resetLesson();
    } catch (error) {
    midiAccess = null;
    setMidiConnection(false);
    setStatus("MIDI access failed", "error");
  }
}

midiButton.addEventListener("click", connectMidi);

restartButton.addEventListener(
  "click",
  resetLesson
);


setMidiConnection(false);
drawCircle();
resetLesson();



if (window.PracticeMIDI && window.PracticeMIDI.isEnabled()) {
  connectMidi();
}
