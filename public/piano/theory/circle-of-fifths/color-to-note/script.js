const keys = [
  { label: "C", pitchClass: 0, color: "#34A853" },
  { label: "G", pitchClass: 7, color: "#7CB342" },
  { label: "D", pitchClass: 2, color: "#C0CA33" },
  { label: "A", pitchClass: 9, color: "#FDD835" },
  { label: "E", pitchClass: 4, color: "#FFB300" },
  { label: "B", pitchClass: 11, color: "#FB8C00" },
  { label: "F#/Gb", pitchClass: 6, color: "#EA4335" },
  { label: "Db", pitchClass: 1, color: "#7E57C2" },
  { label: "Ab", pitchClass: 8, color: "#5C6BC0" },
  { label: "Eb", pitchClass: 3, color: "#42A5F5" },
  { label: "Bb", pitchClass: 10, color: "#26A69A" },
  { label: "F", pitchClass: 5, color: "#5BBE7A" }
];

const GREY = "#D6D9DF";
const WRONG = "#E53935";

const svg = document.getElementById("circleSvg");
const midiButton = document.getElementById("midiButton");
const midiConnection = document.getElementById("midiConnection");
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

    const labelPoint = polarToCartesian(
      CX,
      CY,
      (OUTER_R + INNER_R) / 2,
      centerAngle
    );

    const check = makeSvg("text", {
      x: labelPoint.x,
      y: labelPoint.y,
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

  checkMarks.forEach((check) => {
    check.style.display = "none";
  });

  if (midiAccess) {
    nextQuestion();
  } else {
    setStatus("Enable MIDI to start", "");
  }
}

function randomRemainingIndex() {
  const position = Math.floor(Math.random() * remaining.length);
  return remaining[position];
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

  wedgePaths[currentIndex].setAttribute(
    "fill",
    keys[currentIndex].color
  );

  setStatus(
    "Question " + questionNumber + " of " + keys.length,
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
  const target = keys[currentIndex];

  if (playedPitchClass === target.pitchClass) {
    handleCorrect();
  } else {
    handleWrong();
  }
}

function handleWrong() {
  locked = true;

  const path = wedgePaths[currentIndex];
  const originalColor = keys[currentIndex].color;

  path.setAttribute("fill", WRONG);
  setStatus("Wrong", "error");

  window.setTimeout(() => {
    path.setAttribute("fill", originalColor);
    setStatus(
      "Question " + questionNumber + " of " + keys.length,
      ""
    );
    locked = false;
  }, 300);
}

function handleCorrect() {
  locked = true;

  const solvedIndex = currentIndex;
  const path = wedgePaths[solvedIndex];
  const check = checkMarks[solvedIndex];

  path.setAttribute("fill", GREY);
  check.style.display = "block";

  solved.add(solvedIndex);

  remaining = remaining.filter(
    (index) => index !== solvedIndex
  );

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
    setStatus("Connecting MIDI…", "");

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
    setStatus(
      "MIDI access failed",
      "error"
    );
  }
});

restartButton.addEventListener("click", resetLesson);

midiConnection.addEventListener("click", () => {
  if (typeof connectMidi === "function") {
    connectMidi(true);
  } else {
    midiButton.click();
  }
});

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