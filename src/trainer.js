import { setupLiveGuitarInput } from "./input/live-guitar.js";

// GitHub/Vite theme initialization added during migration.
const themeButton = document.getElementById('themeToggle');
const savedTheme = localStorage.getItem('guitar-learning-theme');
const initialTheme = savedTheme || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeButton.setAttribute(
    'aria-label',
    theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
  );
}
applyTheme(initialTheme);
themeButton.addEventListener('click', () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('guitar-learning-theme', next);
  applyTheme(next);
});



function buildUnifiedSingleSelect(detailsId, sourceSelectId, optionsContainerId = null) {
  const details = document.getElementById(detailsId);
  const source = document.getElementById(sourceSelectId);
  if (!details || !source) return;

  const summary = details.querySelector('summary');
  const menu = optionsContainerId
    ? document.getElementById(optionsContainerId)
    : details.querySelector('.singleSelectMenu');

  if (optionsContainerId) {
    menu.innerHTML = '';
    for (const option of source.options) {
      const label = document.createElement('label');
      label.className = 'singleOption';
      const input = document.createElement('input');
      input.type = 'radio';
      input.name = detailsId;
      input.value = option.value;
      input.checked = option.value === source.value;
      const span = document.createElement('span');
      span.textContent = option.textContent;
      label.append(input, span);
      menu.appendChild(label);
    }
  }

  const radios = [...menu.querySelectorAll('input[type="radio"]')];
  for (const radio of radios) {
    radio.checked = radio.value === source.value;
    radio.onchange = () => {
      if (!radio.checked) return;
      source.value = radio.value;
      summary.textContent = radio.closest('label').querySelector('span').textContent;
      details.open = false;
      source.dispatchEvent(new Event('change', { bubbles: true }));
    };
  }

  const selected = source.options[source.selectedIndex];
  if (selected) summary.textContent = selected.textContent;
}

// Default key: D#, with the mode randomly chosen on page load
// from Locrian, Dorian, or Ionian.
const defaultScaleChoices = [
  'locrian',
  'dorian',
  'ionian'
];

document
  .getElementById(
    'rootSelect'
  )
  .value =
    '3';

document
  .getElementById(
    'scaleSelect'
  )
  .value =
    defaultScaleChoices[
      Math.floor(
        Math.random() *
        defaultScaleChoices.length
      )
    ];

/*
  Browser form-state restoration can override HTML "selected"
  and "checked" defaults on reload/back-forward navigation.
  Set the app defaults explicitly before the visible controls
  are synchronized from their hidden state elements.
*/
document
  .getElementById(
    'lessonTypeSelect'
  )
  .value =
    'rrPent';

document
  .getElementById(
    'rrColorToggle'
  )
  .checked =
    false;

// Visible single-selects share one component; hidden native selects remain state only.
buildUnifiedSingleSelect('lessonTypeDropdown', 'lessonTypeSelect');
buildUnifiedSingleSelect('rootDropdown', 'rootSelect', 'rootOptions');
buildUnifiedSingleSelect('scaleDropdown', 'scaleSelect', 'scaleOptions');

function buildOrderControls() {
  const source =
    document.getElementById(
      'orderSelect'
    );

  const radios = [
    ...document.querySelectorAll(
      '#orderOptions input[type="radio"]'
    )
  ];

  radios.forEach(
    radio => {
      radio.checked =
        radio.value ===
        source.value;

      radio.onchange =
        () => {
          if (!radio.checked) {
            return;
          }

          source.value =
            radio.value;

          source.dispatchEvent(
            new Event(
              'change',
              {
                bubbles:
                  true
              }
            )
          );
        };
    }
  );
}

buildOrderControls();

const noteNames = [
  'C', 'C#', 'D', 'D#', 'E', 'F',
  'F#', 'G', 'G#', 'A', 'A#', 'B'
];

const intervals = {
  0: 'R',
  1: 'b2',
  2: '2',
  3: 'm3',
  4: 'M3',
  5: '4',
  6: 'b5',
  7: '5',
  8: 'b6',
  9: '6',
  10: 'b7',
  11: '7'
};

const intervalStyles = {
  'R':  { background: '#34A853', color: '#000000' },
  'b2': { background: '#FEFFB3', color: '#F9CA9C' },
  '2':  { background: '#FFFF00', color: '#FF9900' },
  'm3': { background: '#F9CA9C', color: '#B4A7D5' },
  'M3': { background: '#FF9900', color: '#9900FF' },
  '4':  { background: '#B4A7D5', color: '#444444' },
  '#4': { background: '#9900FF', color: '#000000' },
  'b5': { background: '#9900FF', color: '#000000' },
  '5':  { background: '#FF0000', color: '#000000' },
  'b6': { background: '#F9CA9C', color: '#444444' },
  '6':  { background: '#FF9900', color: '#000000' },
  'b7': { background: '#FEFFB3', color: '#444444' },
  '7':  { background: '#FFFF00', color: '#000000' }
};


/* =========================================================
   MODES
   ========================================================= */

const scales = {
  ionian: [
    [0, 'R'], [2, '2'], [4, 'M3'], [5, '4'],
    [7, '5'], [9, '6'], [11, '7']
  ],

  dorian: [
    [0, 'R'], [2, '2'], [3, 'm3'], [5, '4'],
    [7, '5'], [9, '6'], [10, 'b7']
  ],

  phrygian: [
    [0, 'R'], [1, 'b2'], [3, 'm3'], [5, '4'],
    [7, '5'], [8, 'b6'], [10, 'b7']
  ],

  lydian: [
    [0, 'R'], [2, '2'], [4, 'M3'], [6, '#4'],
    [7, '5'], [9, '6'], [11, '7']
  ],

  mixolydian: [
    [0, 'R'], [2, '2'], [4, 'M3'], [5, '4'],
    [7, '5'], [9, '6'], [10, 'b7']
  ],

  aeolian: [
    [0, 'R'], [2, '2'], [3, 'm3'], [5, '4'],
    [7, '5'], [8, 'b6'], [10, 'b7']
  ],

  locrian: [
    [0, 'R'], [1, 'b2'], [3, 'm3'], [5, '4'],
    [6, 'b5'], [8, 'b6'], [10, 'b7']
  ]
};

const modeNames = {
  ionian: 'Ionian',
  dorian: 'Dorian',
  phrygian: 'Phrygian',
  lydian: 'Lydian',
  mixolydian: 'Mixolydian',
  aeolian: 'Aeolian',
  locrian: 'Locrian'
};

const modalDegreeIndex = {
  ionian: 0,
  dorian: 1,
  phrygian: 2,
  lydian: 3,
  mixolydian: 4,
  aeolian: 5,
  locrian: 6
};


/* =========================================================
   2/3 NPS PENTATONICS
   ========================================================= */

const npsPentatonicSemitones = {
  lydian:     [0, 4, 6, 7, 11],
  ionian:     [0, 4, 5, 7, 11],
  mixolydian: [0, 4, 5, 7, 10],
  dorian:     [0, 3, 5, 7, 10],
  aeolian:    [0, 3, 5, 7, 10],
  phrygian:   [0, 3, 5, 7, 10],
  locrian:    [0, 3, 5, 6, 10]
};


/*
  EXACT STRING DISTRIBUTION FROM THE REFERENCE SHAPES

  Physical string numbering:
    stringIndex 0 = lowest string
    stringIndex 7 = highest string

  Lydian / Ionian / Mixolydian /
  Dorian / Aeolian / Phrygian:

      3 | 3 | 3 | 2 | 3 | 2 | 3 | 2

  Locrian:

      4 | 2 | 3 | 2 | 3 | 2 | 3 | 2

  Therefore:
    - strings 1 and 2 initialize the pattern
    - string 3 onward is always 3,2,3,2,3,2
*/

const npsShapeRules = {
  lydian: {
    firstTwo: [
      ['R', 'M3', '#4'],
      ['5', '7', 'R'],
      ['M3', '#4', '5']
    ],
    remaining: [
      ['7', 'R'],
      ['M3', '#4', '5']
    ]
  },

  ionian: {
    firstTwo: [
      ['R', 'M3', '4'],
      ['5', '7', 'R'],
      ['M3', '4', '5']
    ],
    remaining: [
      ['7', 'R'],
      ['M3', '4', '5']
    ]
  },

  mixolydian: {
    firstTwo: [
      ['R', 'M3', '4'],
      ['5', 'b7', 'R'],
      ['M3', '4', '5']
    ],
    remaining: [
      ['b7', 'R'],
      ['M3', '4', '5']
    ]
  },

  dorian: {
    firstTwo: [
      ['R', 'm3', '4'],
      ['5', 'b7', 'R'],
      ['m3', '4', '5']
    ],
    remaining: [
      ['b7', 'R'],
      ['m3', '4', '5']
    ]
  },

  aeolian: {
    firstTwo: [
      ['R', 'm3', '4'],
      ['5', 'b7', 'R'],
      ['m3', '4', '5']
    ],
    remaining: [
      ['b7', 'R'],
      ['m3', '4', '5']
    ]
  },

  phrygian: {
    firstTwo: [
      ['R', 'm3', '4'],
      ['5', 'b7', 'R'],
      ['m3', '4', '5']
    ],
    remaining: [
      ['b7', 'R'],
      ['m3', '4', '5']
    ]
  },

  locrian: {
    firstTwo: [
      ['R', 'm3', '4', 'b5'],
      ['b7', 'R'],
      ['m3', '4', 'b5']
    ],
    remaining: [
      ['b7', 'R'],
      ['m3', '4', 'b5']
    ]
  }
};


const genericDegreeBySemitone = {
  0: 'R',
  1: '2',
  2: '2',
  3: '3',
  4: '3',
  5: '4',
  6: '5',
  7: '5',
  8: '6',
  9: '6',
  10: '7',
  11: '7'
};

const npsModeOrder = [
  'lydian',
  'ionian',
  'mixolydian',
  'dorian',
  'aeolian',
  'phrygian',
  'locrian'
];

const startingDegreeOrder = [
  'R', '2', '3', '4', '5', '6', '7'
];

const directionOptions = [
  ['up', '⬆️'],
  ['down', '⬇️'],
  ['upDown', '↕️']
];

const cagedShapeOrder = [
  'C',
  'A',
  'G',
  'E',
  'D'
];

/*
  CAGED is permanently mapped to physical strings 3-8
  (the six-string standard-tuning block of the 8-string).

  Each mode/shape combination below supplies its own exact,
  immutable six-string pentatonic template. Templates may
  transpose horizontally only; they never move vertically.
*/
const cagedBlockStartStringIndex =
  2; // physical String 3

const cagedBlockEndStringIndex =
  7; // physical String 8


/* =========================================================
   FRETBOARD
   ========================================================= */

const dotFrets = [
  3, 5, 7, 9, 12,
  15, 17, 19, 21, 24
];

const defaultTuning = [
  27, // D#1
  34, // A#1
  39, // D#2
  44, // G#2
  49, // C#3
  54, // F#3
  58, // A#3
  63  // D#4
];

let currentTuning = [...defaultTuning];

let questions = [];
let currentAnswer = null;
let showAll = false;
let currentNpsExercise = null;
let currentRrPentExercise = null;
let currentShapeExercise = null;
let currentCagedExercise = null;

const lessonDefinitions = {
  intervals: {
    label: 'Intervals Relative to Low String',
    maxFret: 12,
    hasStartCue: false
  },
  shape: {
    label: 'Closest interval',
    maxFret: 15,
    hasStartCue: true
  },
  nps: {
    label: '2/3 NPS',
    maxFret: 24,
    hasStartCue: true
  },
  rrPent: {
    label: 'R-R',
    maxFret: 24,
    hasStartCue: true
  },
  caged: {
    label: 'CAGED',
    maxFret: 24,
    hasStartCue: true
  },
  daily: {
    label: 'Daily Practice',
    orchestrator: true
  }
};

const dailyPracticeLessonTypes = [
  'shape',
  'nps',
  'rrPent',
  'caged'
];

let dailyPracticeState = null;

let fretboardNoteResizeObserver = null;

const quizCompletePauseMs = 1000;

let quizTransitionTimer = null;
let isQuizTransitioning = false;

function cancelQuizTransition() {
  if (
    quizTransitionTimer !== null
  ) {
    clearTimeout(
      quizTransitionTimer
    );
  }

  quizTransitionTimer = null;
  isQuizTransitioning = false;
}

function scheduleQuizTransition(
  callback
) {
  cancelQuizTransition();

  isQuizTransitioning = true;

  quizTransitionTimer =
    setTimeout(
      () => {
        quizTransitionTimer = null;
        isQuizTransitioning = false;

        callback();
      },
      quizCompletePauseMs
    );
}


/* =========================================================
   BASIC HELPERS
   ========================================================= */

function mod12(value) {
  return ((value % 12) + 12) % 12;
}

function midiToPitchClass(midi) {
  return mod12(midi);
}

function midiToOctave(midi) {
  return Math.floor(midi / 12) - 1;
}

function midiToNoteName(midi) {
  return noteNames[
    midiToPitchClass(midi)
  ];
}

function midiToScientificPitch(midi) {
  return (
    midiToNoteName(midi) +
    midiToOctave(midi)
  );
}

function getSelectedLessonType() {
  return document
    .getElementById(
      'lessonTypeSelect'
    )
    .value;
}

function isDailyPracticeSelected() {
  return (
    getSelectedLessonType() ===
    'daily'
  );
}

/*
  "Selected lesson" is what the user chose in the Lesson menu.
  "Active lesson" is the exercise engine currently doing the work.

  Ordinary lessons:
    selected === active

  Daily Practice:
    selected === "daily"
    active   === intervals / shape / nps / rrPent / caged

  This keeps every existing lesson engine independent from the
  Daily Practice orchestrator.
*/
function getLessonType() {
  if (
    isDailyPracticeSelected() &&
    dailyPracticeState
  ) {
    return dailyPracticeState
      .activeLessonType;
  }

  return getSelectedLessonType();
}

function getLessonDefinition(
  lessonType =
    getLessonType()
) {
  return (
    lessonDefinitions[
      lessonType
    ] ||
    lessonDefinitions.intervals
  );
}

function syncSingleSelectDisplay(
  detailsId,
  selectId
) {
  const details =
    document.getElementById(
      detailsId
    );

  const select =
    document.getElementById(
      selectId
    );

  if (!details || !select) {
    return;
  }

  const summary =
    details.querySelector(
      'summary'
    );

  const selectedOption =
    select.options[
      select.selectedIndex
    ];

  if (
    summary &&
    selectedOption
  ) {
    summary.textContent =
      selectedOption.textContent;
  }

  details
    .querySelectorAll(
      'input[type="radio"]'
    )
    .forEach(
      radio => {
        radio.checked =
          radio.value ===
          select.value;
      }
    );
}

function setDailyBaseScale(
  mode
) {
  const rootSelect =
    document.getElementById(
      'rootSelect'
    );

  const scaleSelect =
    document.getElementById(
      'scaleSelect'
    );

  rootSelect.value = '3';
  scaleSelect.value = mode;

  syncSingleSelectDisplay(
    'rootDropdown',
    'rootSelect'
  );

  syncSingleSelectDisplay(
    'scaleDropdown',
    'scaleSelect'
  );
}

function setDailyStartDegreeRoot() {
  document
    .querySelectorAll(
      '.startDegreeCheckbox'
    )
    .forEach(
      checkbox => {
        checkbox.checked =
          checkbox.value ===
          'R';
      }
    );

  updateStartDegreeSummary();
}

function setDailyIntervalSelection(
  selectAll
) {
  document
    .querySelectorAll(
      '.intervalCheckbox'
    )
    .forEach(
      checkbox => {
        checkbox.checked =
          selectAll ||
          checkbox.value ===
            'R';
      }
    );

  updateIntervalSummary();
}

function getDailyPairs() {
  return shuffleList(
    npsModeOrder.flatMap(
      mode =>
        dailyPracticeLessonTypes.map(
          lessonType => ({
            mode,
            lessonType
          })
        )
    )
  );
}

function getDailyPairLabel(
  pair
) {
  if (!pair) {
    return '';
  }

  return (
    modeNames[
      pair.mode
    ] +
    ' · ' +
    getLessonDefinition(
      pair.lessonType
    ).label
  );
}

function updateDailyPracticeStatus() {
  const status =
    document.getElementById(
      'dailyPracticeStatus'
    );

  if (!status) {
    return;
  }

  if (
    !isDailyPracticeSelected() ||
    !dailyPracticeState
  ) {
    status.hidden = true;
    status.textContent = '';
    return;
  }

  status.hidden = false;

  if (
    dailyPracticeState.phase ===
    'intervals'
  ) {
    status.textContent =
      'Phase 1 · D# ' +
      modeNames[
        dailyPracticeState
          .baseMode
      ] +
      ' · ' +
      dailyPracticeState
        .remainingPairs.length +
      ' pairs left';

    return;
  }

  if (
    dailyPracticeState.phase ===
    'complete'
  ) {
    status.textContent =
      'Daily practice complete · 0 left';

    return;
  }

  const current =
    dailyPracticeState.currentPair;

  const remaining =
    dailyPracticeState
      .remainingPairs.length +
    (
      current
        ? 1
        : 0
    );

  status.textContent =
    getDailyPairLabel(
      current
    ) +
    ' · ' +
    remaining +
    ' left';
}

function initializeDailyPractice() {
  const baseMode =
    randomItem(
      npsModeOrder
    );

  dailyPracticeState = {
    phase:
      'intervals',

    baseMode,

    activeLessonType:
      'intervals',

    currentPair:
      null,

    remainingPairs:
      getDailyPairs()
  };

  /*
    The base key is chosen ONCE for the whole Daily Practice
    session and never changes between exercise pairs.
  */
  setDailyBaseScale(
    baseMode
  );

  const orderSelect =
    document.getElementById(
      'orderSelect'
    );

  orderSelect.value =
    'random';

  buildOrderControls();
  buildIntervalControls();
  setDailyIntervalSelection(
    true
  );
  setDailyStartDegreeRoot();
  updateDailyPracticeStatus();
}

function getDailyExerciseKeyContext(
  baseRoot,
  baseMode
) {
  if (
    !isDailyPracticeSelected() ||
    !dailyPracticeState ||
    dailyPracticeState.phase !==
      'pairs' ||
    !dailyPracticeState.currentPair ||
    dailyPracticeState.currentPair
      .lessonType !==
      'shape'
  ) {
    return {
      root:
        baseRoot,
      scaleName:
        baseMode
    };
  }

  /*
    Closest Interval does not have its own modal selector, so
    Daily Practice supplies the selected relative mode directly
    as the exercise key context while leaving the base key fixed.
  */
  const mode =
    dailyPracticeState
      .currentPair.mode;

  return {
    root:
      getRelativeModeRoot(
        baseRoot,
        baseMode,
        mode
      ),

    scaleName:
      mode
  };
}

function startNextDailyPair() {
  if (
    !dailyPracticeState
  ) {
    return;
  }

  const nextPair =
    dailyPracticeState
      .remainingPairs
      .shift();

  if (!nextPair) {
    dailyPracticeState.phase =
      'complete';

    dailyPracticeState
      .currentPair =
        null;

    document
      .getElementById(
        'chartDiv'
      )
      .innerHTML = '';

    document
      .querySelector(
        '.trainerShell'
      )
      ?.classList.remove(
        'hasStartCue'
      );

    document
      .getElementById(
        'answerNote'
      )
      .textContent =
        'Daily practice complete!';

    updateDailyPracticeStatus();
    return;
  }

  dailyPracticeState.phase =
    'pairs';

  dailyPracticeState
    .currentPair =
      nextPair;

  dailyPracticeState
    .activeLessonType =
      nextPair.lessonType;

  /*
    Do NOT alter rootSelect / scaleSelect here.
    D# + the randomly chosen base mode remain fixed throughout
    the entire Daily Practice session.
  */
  setDailyStartDegreeRoot();
  updateDailyPracticeStatus();
  buildTrainer();
}

function completeDailyPair() {
  if (
    !isDailyPracticeSelected() ||
    !dailyPracticeState ||
    dailyPracticeState.phase !==
      'pairs'
  ) {
    buildTrainer();
    return;
  }

  dailyPracticeState.currentPair =
    null;

  startNextDailyPair();
}

function completeCurrentExercise() {
  if (
    isDailyPracticeSelected() &&
    dailyPracticeState?.phase ===
      'pairs'
  ) {
    completeDailyPair();
    return;
  }

  buildTrainer();
}

function finishDailyIntervals() {
  if (
    !isDailyPracticeSelected() ||
    !dailyPracticeState ||
    dailyPracticeState.phase !==
      'intervals'
  ) {
    return false;
  }

  startNextDailyPair();
  return true;
}

function skipDailyCurrentExercise() {
  if (
    !isDailyPracticeSelected() ||
    !dailyPracticeState
  ) {
    return false;
  }

  if (
    dailyPracticeState.phase ===
    'intervals'
  ) {
    if (
      currentAnswer
    ) {
      const questionIndex =
        questions.indexOf(
          currentAnswer
        );

      if (
        questionIndex !== -1
      ) {
        questions.splice(
          questionIndex,
          1
        );
      }
    }

    document
      .querySelectorAll(
        '.noteCell.correct'
      )
      .forEach(
        cell => {
          cell.classList.remove(
            'correct'
          );

          restoreCellDisplay(
            cell
          );
        }
      );

    if (
      questions.length === 0
    ) {
      startNextDailyPair();
    } else {
      generateIntervalAnswer();
    }

    return true;
  }

  if (
    dailyPracticeState.phase ===
    'pairs'
  ) {
    completeDailyPair();
    return true;
  }

  return true;
}

function getTuning() {
  return [...currentTuning];
}

window.getGuitarTrainerTuning =
  () => getTuning();

function sizeFretboardNotes(
  stage,
  fretboard,
  stringCount,
  fretCount,
  stringTopStart,
  stringTopEnd
) {
  const rect =
    fretboard
      .getBoundingClientRect();

  if (
    rect.width <= 0 ||
    rect.height <= 0
  ) {
    return;
  }

  const stageStyle =
    getComputedStyle(
      stage
    );

  const maxSize =
    Number.parseFloat(
      stageStyle.getPropertyValue(
        '--note-max-size'
      )
    ) || 38;

  const fretGap =
    Number.parseFloat(
      stageStyle.getPropertyValue(
        '--note-fret-gap'
      )
    ) || 4;

  /*
    Preserve the existing horizontal fret constraint:
      fret width - reserved horizontal breathing room.
  */
  const fretSizeLimit =
    rect.width /
      fretCount -
    fretGap;

  /*
    String centers are distributed between stringTopStart and
    stringTopEnd. Keep a 5% edge-to-edge gap between adjacent
    circles by allowing the diameter to occupy 95% of the
    center-to-center string spacing.
  */
  const stringCenterDistance =
    stringCount <= 1
      ? rect.height
      : (
          rect.height *
          (
            stringTopEnd -
            stringTopStart
          ) /
          100 /
          (
            stringCount - 1
          )
        );

  const stringGapSizeLimit =
    stringCenterDistance *
    0.95;

  const noteSize =
    Math.max(
      1,
      Math.min(
        maxSize,
        fretSizeLimit,
        stringGapSizeLimit
      )
    );

  stage.style.setProperty(
    '--fretboard-note-size',
    noteSize + 'px'
  );
}

function observeFretboardNoteSizing(
  stage,
  fretboard,
  stringCount,
  fretCount,
  stringTopStart,
  stringTopEnd
) {
  if (
    fretboardNoteResizeObserver
  ) {
    fretboardNoteResizeObserver
      .disconnect();
  }

  const update =
    () =>
      sizeFretboardNotes(
        stage,
        fretboard,
        stringCount,
        fretCount,
        stringTopStart,
        stringTopEnd
      );

  fretboardNoteResizeObserver =
    new ResizeObserver(
      update
    );

  fretboardNoteResizeObserver
    .observe(
      fretboard
    );

  requestAnimationFrame(
    update
  );
}

function randomItem(list) {
  return list[
    Math.floor(
      Math.random() *
      list.length
    )
  ];
}

function makeCellKey(
  stringIndex,
  fret
) {
  return `${stringIndex}|${fret}`;
}


/* =========================================================
   TARGET HELPERS
   ========================================================= */

function makeTarget(
  interval,
  octave
) {
  return `${interval}|${octave}`;
}

function parseTarget(target) {
  const separatorIndex =
    target.lastIndexOf('|');

  return {
    interval:
      target.slice(
        0,
        separatorIndex
      ),

    octave:
      Number(
        target.slice(
          separatorIndex + 1
        )
      )
  };
}

function setIntervalOctaveDisplay(
  element,
  interval,
  octave
) {
  element.innerHTML = '';

  const wrapper =
    document.createElement('span');

  wrapper.className =
    'intervalDisplay';

  wrapper.appendChild(
    document.createTextNode(
      interval
    )
  );

  const sub =
    document.createElement('sub');

  sub.textContent = octave;

  wrapper.appendChild(sub);

  element.appendChild(wrapper);
}


/* =========================================================
   INTERVAL LOOKUP
   ========================================================= */

function getIntervalForPitch(
  pitchClass,
  root,
  scaleName
) {
  const distance =
    mod12(
      pitchClass - root
    );

  if (distance === 6) {
    return (
      scaleName === 'lydian'
        ? '#4'
        : 'b5'
    );
  }

  return intervals[distance];
}

function getScaleInterval(
  scaleName,
  semitone
) {
  const item =
    scales[scaleName].find(
      ([distance]) =>
        distance === semitone
    );

  return item
    ? item[1]
    : null;
}


/* =========================================================
   INTERVAL MULTISELECT
   ========================================================= */

function buildIntervalControls() {
  const scaleName =
    document
      .getElementById('scaleSelect')
      .value;

  const scale =
    scales[scaleName];

  const container =
    document
      .getElementById('intervalOptions');

  container.innerHTML = '';

  scale.forEach(
    ([semitones, intervalName]) => {

      const label =
        document.createElement('label');

      label.className =
        'intervalOption';

      const checkbox =
        document.createElement('input');

      checkbox.type =
        'checkbox';

      checkbox.className =
        'intervalCheckbox';

      checkbox.value =
        intervalName;

      checkbox.checked =
        getLessonType() ===
          'shape' &&
        !isDailyPracticeSelected()
          ? intervalName === 'R'
          : true;

      checkbox.addEventListener(
        'change',
        handleIntervalChange
      );

      const text =
        document.createElement('span');

      text.innerText =
        intervalName;

      label.appendChild(checkbox);
      label.appendChild(text);

      container.appendChild(label);
    }
  );

  updateIntervalSummary();
}

function handleIntervalChange(event) {
  const selected =
    getSelectedIntervals();

  if (selected.length === 0) {
    event.target.checked = true;
    return;
  }

  updateIntervalSummary();

  if (
    ['intervals', 'shape'].includes(
      getLessonType()
    )
  ) {
    buildTrainer();
  }
}

function getSelectedIntervals() {
  const scaleName =
    document
      .getElementById('scaleSelect')
      .value;

  const scale =
    scales[scaleName];

  const checked =
    new Set(
      [
        ...document.querySelectorAll(
          '.intervalCheckbox:checked'
        )
      ].map(
        checkbox =>
          checkbox.value
      )
    );

  return scale
    .map(
      ([semitones, intervalName]) =>
        intervalName
    )
    .filter(
      intervalName =>
        checked.has(intervalName)
    );
}

function updateIntervalSummary() {
  const selected =
    getSelectedIntervals();

  const summary =
    document
      .getElementById('intervalSummary');

  if (selected.length === 7) {
    summary.innerText = 'All 7';
  } else {
    summary.innerText =
      selected.join(', ');
  }
}


/* =========================================================
   GENERIC MULTISELECT
   ========================================================= */

function createMultiOption(
  container,
  className,
  value,
  text,
  checked,
  changeHandler
) {
  const label =
    document.createElement('label');

  label.className =
    'multiOption';

  const checkbox =
    document.createElement('input');

  checkbox.type =
    'checkbox';

  checkbox.className =
    className;

  checkbox.value =
    value;

  checkbox.checked =
    checked;

  checkbox.addEventListener(
    'change',
    changeHandler
  );

  const span =
    document.createElement('span');

  span.textContent = text;

  label.appendChild(checkbox);
  label.appendChild(span);

  container.appendChild(label);
}

function preventEmptySelection(
  event,
  selector
) {
  const selected =
    document.querySelectorAll(
      selector + ':checked'
    );

  if (selected.length === 0) {
    event.target.checked = true;
    return false;
  }

  return true;
}


/* =========================================================
   NPS MODE MULTISELECT
   ========================================================= */

function buildNpsModeControls() {
  const container =
    document.getElementById(
      'npsModeOptions'
    );

  container.innerHTML = '';

  npsModeOrder.forEach(
    mode => {
      createMultiOption(
        container,
        'npsModeCheckbox',
        mode,
        modeNames[mode],
        true,
        handleNpsModeChange
      );
    }
  );

  updateNpsModeSummary();
}

function handleNpsModeChange(event) {
  if (
    !preventEmptySelection(
      event,
      '.npsModeCheckbox'
    )
  ) {
    return;
  }

  updateNpsModeSummary();

  if (
    ['nps', 'rrPent', 'caged'].includes(
      getLessonType()
    )
  ) {
    buildTrainer();
  }
}

function getSelectedNpsModes() {
  if (
    isDailyPracticeSelected() &&
    dailyPracticeState?.phase ===
      'pairs' &&
    dailyPracticeState.currentPair
  ) {
    return [
      dailyPracticeState
        .currentPair.mode
    ];
  }

  return [
    ...document.querySelectorAll(
      '.npsModeCheckbox:checked'
    )
  ].map(
    checkbox =>
      checkbox.value
  );
}

function updateNpsModeSummary() {
  const selected =
    getSelectedNpsModes();

  const summary =
    document.getElementById(
      'npsModeSummary'
    );

  if (
    selected.length ===
    npsModeOrder.length
  ) {
    summary.textContent =
      'All 7';
  } else {
    summary.textContent =
      selected
        .map(
          mode =>
            modeNames[mode]
        )
        .join(', ');
  }
}


/* =========================================================
   STARTING DEGREE MULTISELECT
   ========================================================= */

function buildStartDegreeControls() {
  const container =
    document.getElementById(
      'startDegreeOptions'
    );

  container.innerHTML = '';

  startingDegreeOrder.forEach(
    degree => {
      createMultiOption(
        container,
        'startDegreeCheckbox',
        degree,
        degree,
        degree === 'R',
        handleStartDegreeChange
      );
    }
  );

  updateStartDegreeSummary();
}

function handleStartDegreeChange(event) {
  if (
    !preventEmptySelection(
      event,
      '.startDegreeCheckbox'
    )
  ) {
    return;
  }

  updateStartDegreeSummary();

  if (
    ['nps', 'rrPent', 'caged'].includes(
      getLessonType()
    )
  ) {
    buildTrainer();
  }
}

function getSelectedStartDegrees() {
  if (
    isDailyPracticeSelected() &&
    dailyPracticeState?.phase ===
      'pairs' &&
    ['nps', 'rrPent', 'caged'].includes(
      getLessonType()
    )
  ) {
    return ['R'];
  }

  return [
    ...document.querySelectorAll(
      '.startDegreeCheckbox:checked'
    )
  ].map(
    checkbox =>
      checkbox.value
  );
}

function updateStartDegreeSummary() {
  const selected =
    getSelectedStartDegrees();

  document
    .getElementById(
      'startDegreeSummary'
    )
    .textContent =
      selected.join(', ');
}


/* =========================================================
   CAGED SHAPES MULTISELECT
   ========================================================= */

function buildCagedShapeControls() {
  const container =
    document.getElementById(
      'cagedShapeOptions'
    );

  container.innerHTML = '';

  cagedShapeOrder.forEach(
    shape => {
      createMultiOption(
        container,
        'cagedShapeCheckbox',
        shape,
        shape,
        true,
        handleCagedShapeChange
      );
    }
  );

  updateCagedShapeSummary();
}

function handleCagedShapeChange(event) {
  if (
    !preventEmptySelection(
      event,
      '.cagedShapeCheckbox'
    )
  ) {
    return;
  }

  updateCagedShapeSummary();

  if (
    getLessonType() === 'caged'
  ) {
    buildTrainer();
  }
}

function getSelectedCagedShapes() {
  return [
    ...document.querySelectorAll(
      '.cagedShapeCheckbox:checked'
    )
  ].map(
    checkbox =>
      checkbox.value
  );
}

function updateCagedShapeSummary() {
  const selected =
    getSelectedCagedShapes();

  const summary =
    document.getElementById(
      'cagedShapeSummary'
    );

  if (
    selected.length ===
    cagedShapeOrder.length
  ) {
    summary.textContent =
      'All 5';
  } else {
    summary.textContent =
      selected.join(', ');
  }
}


/* =========================================================
   DIRECTION MULTISELECT
   ========================================================= */

function buildDirectionControls() {
  const container = document.getElementById('directionOptions');
  container.innerHTML = '';

  directionOptions.forEach(([value, text]) => {
    const label = document.createElement('label');
    label.className = 'directionOption';

    const input = document.createElement('input');
    input.type = 'radio';
    input.name = 'direction';
    input.className = 'directionCheckbox';
    input.value = value;
    input.checked = value === 'up';
    input.addEventListener('change', handleDirectionChange);

    const visual = document.createElement('span');
    visual.textContent = text;

    label.appendChild(input);
    label.appendChild(visual);
    container.appendChild(label);
  });

  updateDirectionSummary();
}

function handleDirectionChange() {
  updateDirectionSummary();

  if (
    ['nps', 'rrPent'].includes(
      getLessonType()
    )
  ) {
    buildTrainer();
  }
}

function getSelectedDirections() {
  return [...document.querySelectorAll('.directionCheckbox:checked')]
    .map(input => input.value);
}

function getRrColorNotesEnabled() {
  return Boolean(
    document
      .getElementById(
        'rrColorToggle'
      )
      ?.checked
  );
}

function getDirectionLabel(value) {
  const found = directionOptions.find(([optionValue]) => optionValue === value);
  return found ? found[1] : value;
}

function updateDirectionSummary() {
  const summary = document.getElementById('directionSummary');
  if (summary) {
    summary.textContent = getSelectedDirections().map(getDirectionLabel).join(' ');
  }
}


/* =========================================================
   LESSON UI
   ========================================================= */

function updateLessonControls() {
  const selectedLessonType =
    getSelectedLessonType();

  const daily =
    selectedLessonType ===
      'daily';

  const lessonType =
    getLessonType();

  const nps =
    lessonType === 'nps';

  const rrPent =
    lessonType === 'rrPent';

  const caged =
    lessonType === 'caged';

  const pentatonicLesson =
    nps || rrPent || caged;

  document
    .getElementById(
      'intervalLessonControls'
    )
    .hidden =
      daily ||
      pentatonicLesson;

  document
    .getElementById(
      'npsControls'
    )
    .hidden =
      daily ||
      !pentatonicLesson;

  const startDegreeControl =
    document
      .getElementById(
        'startDegreeOptions'
      )
      ?.closest(
        '.controlField'
      );

  if (startDegreeControl) {
    /*
      R-R always starts from a root.
      The generic NPS Start selector does not apply here.
    */
    startDegreeControl.hidden =
      daily ||
      rrPent;
  }

  document
    .getElementById(
      'directionControl'
    )
    .hidden =
      daily ||
      !(nps || rrPent);

  document
    .getElementById(
      'cagedShapeControl'
    )
    .hidden =
      daily ||
      !caged;

  document
    .getElementById(
      'rrColorControl'
    )
    .hidden =
      daily ||
      !rrPent;

  document
    .getElementById(
      'orderControl'
    )
    .hidden =
      daily ||
      pentatonicLesson;

  const intervalFieldLabel =
    document.querySelector(
      '#intervalControlGroup .fieldLabel'
    );

  if (intervalFieldLabel) {
    intervalFieldLabel.textContent =
      lessonType === 'shape'
        ? 'Starting Intervals'
        : 'Intervals';
  }

  const rootDropdown =
    document.getElementById(
      'rootDropdown'
    );

  const scaleDropdown =
    document.getElementById(
      'scaleDropdown'
    );

  if (rootDropdown) {
    rootDropdown.inert =
      daily;
  }

  if (scaleDropdown) {
    scaleDropdown.inert =
      daily;
  }

  updateDailyPracticeStatus();
}


/* =========================================================
   CELL DISPLAY
   ========================================================= */

function applyIntervalStyle(
  cell,
  interval
) {
  const style =
    intervalStyles[interval];

  if (!style) {
    return;
  }

  cell.style.backgroundColor =
    style.background;

  cell.style.color =
    style.color;
}

function clearCellStyle(cell) {
  cell.style.backgroundColor = '';
  cell.style.color = '';
}

function revealCell(
  cell,
  intervalOverride = null
) {
  const interval =
    intervalOverride ||
    cell.dataset.displayInterval ||
    cell.dataset.interval;

  if (!interval) {
    return;
  }

  if (
    ['nps', 'rrPent', 'shape', 'caged'].includes(
      getLessonType()
    )
  ) {
    cell.textContent =
      interval;
  } else {
    setIntervalOctaveDisplay(
      cell,
      interval,
      Number(
        cell.dataset.octave
      )
    );
  }

  cell.classList.remove(
    'unknownInterval'
  );

  cell.classList.add(
    'revealed'
  );

  applyIntervalStyle(
    cell,
    interval
  );
}

function hideCell(cell) {
  cell.classList.remove(
    'revealed'
  );

  clearCellStyle(cell);

  if (
    cell.dataset.openString ===
    'true'
  ) {
    cell.classList.remove(
      'unknownInterval'
    );

    cell.innerText =
      cell.dataset.noteName;
  } else {
    cell.classList.add(
      'unknownInterval'
    );

    cell.innerText = '';
  }
}

/*
  SHOW ALL

  INTERVAL LESSON:
    only selected intervals

  NPS LESSON:
    only the exact directional shape
    being quizzed
*/

function restoreCellDisplay(cell) {
  if (
    cell.classList.contains(
      'correct'
    )
  ) {
    revealCell(cell);
    return;
  }

  if (!showAll) {
    hideCell(cell);
    return;
  }

  if (
    getLessonType() ===
    'intervals'
  ) {
    const selected =
      getSelectedIntervals();

    if (
      selected.includes(
        cell.dataset.interval
      )
    ) {
      revealCell(cell);
    } else {
      hideCell(cell);
    }

    return;
  }

  if (
    getLessonType() === 'shape' &&
    currentShapeExercise
  ) {
    const key =
      makeCellKey(
        Number(
          cell.dataset.stringIndex
        ),
        Number(
          cell.dataset.fret
        )
      );

    if (
      currentShapeExercise
        .requiredCellKeys
        .has(key)
    ) {
      revealCell(cell);
    } else {
      hideCell(cell);
    }

    return;
  }

  if (
    getLessonType() === 'caged' &&
    currentCagedExercise
  ) {
    const key =
      makeCellKey(
        Number(
          cell.dataset.stringIndex
        ),
        Number(
          cell.dataset.fret
        )
      );

    if (
      currentCagedExercise
        .requiredCellKeys
        .has(key)
    ) {
      revealCell(cell);
    } else {
      hideCell(cell);
    }

    return;
  }

  if (
    getLessonType() === 'nps' &&
    currentNpsExercise
  ) {
    const key =
      makeCellKey(
        Number(
          cell.dataset.stringIndex
        ),
        Number(
          cell.dataset.fret
        )
      );

    if (
      currentNpsExercise
        .requiredCellKeys
        .has(key)
    ) {
      revealCell(cell);
    } else {
      hideCell(cell);
    }

    return;
  }

  if (
    getLessonType() === 'rrPent' &&
    currentRrPentExercise
  ) {
    const key =
      makeCellKey(
        Number(
          cell.dataset.stringIndex
        ),
        Number(
          cell.dataset.fret
        )
      );

    if (
      currentRrPentExercise
        .requiredCellKeys
        .has(key)
    ) {
      revealCell(cell);
    } else {
      hideCell(cell);
    }
  }
}


/* =========================================================
   TUNING SETTINGS
   ========================================================= */

function createTuningSettings() {
  const wrapper = document.createElement('div');
  wrapper.className = 'fretboardTuningControl';

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'settingsButton';
  button.innerHTML = `
    <svg class="tuningForkIcon" viewBox="0 0 32 32" aria-hidden="true">
      <path class="forkStroke" d="M12 5v8a4 4 0 0 0 8 0V5M10 5v8a6 6 0 0 0 5 5.92V27h2v-8.08A6 6 0 0 0 22 13V5"/>
      <path class="forkStroke" d="M7.5 9.5c-2 2-2 5 0 7M24.5 9.5c2 2 2 5 0 7M4.5 7c-3.5 3.5-3.5 8.5 0 12M27.5 7c3.5 3.5 3.5 8.5 0 12"/>
    </svg>`;
  button.title = 'Tuning settings';
  button.setAttribute('aria-label', 'Tuning settings');

  const popover = document.createElement('div');
  popover.className = 'tuningPopover';

  currentTuning.forEach((midiPitch, stringIndex) => {
    const item = document.createElement('div');
    item.className = 'tuningItem';

    const text = document.createElement('span');
    text.className = 'tuningLabel';
    text.textContent = `String ${stringIndex + 1}`;

    const details = document.createElement('details');
    details.className = 'singleSelect tuningSelect';

    const summary = document.createElement('summary');
    summary.textContent = midiToScientificPitch(midiPitch);

    const menu = document.createElement('div');
    menu.className = 'singleSelectMenu tuningSelectMenu';

    for (let midi = 12; midi <= 95; midi++) {
      const option = document.createElement('label');
      option.className = 'singleOption';

      const input = document.createElement('input');
      input.type = 'radio';
      input.name = `tuning-string-${stringIndex}`;
      input.value = midi;
      input.checked = midi === midiPitch;

      const optionText = document.createElement('span');
      optionText.textContent = midiToScientificPitch(midi);

      input.addEventListener('change', () => {
        if (!input.checked) return;
        currentTuning[stringIndex] = midi;
        summary.textContent = optionText.textContent;
        details.open = false;
        buildTrainer();
      });

      option.append(input, optionText);
      menu.appendChild(option);
    }

    details.append(summary, menu);
    item.append(text, details);
    popover.appendChild(item);
  });

  button.addEventListener('click', event => {
    event.stopPropagation();
    popover.classList.toggle('open');
  });

  popover.addEventListener('click', event => {
    event.stopPropagation();
  });

  wrapper.append(button, popover);
  return wrapper;
}

/* =========================================================
   FRETBOARD LAYOUT
   The physical fretboard is responsive, so no table-column
   width locking is required.
   ========================================================= */

function lockColumnWidths() {
  // Compatibility no-op for older call sites.
}

/* =========================================================
   RELATIVE MODES
   ========================================================= */

function getRelativeModeRoot(
  baseRoot,
  baseMode,
  targetMode
) {
  const baseModeIndex =
    modalDegreeIndex[
      baseMode
    ];

  const targetModeIndex =
    modalDegreeIndex[
      targetMode
    ];

  const majorScaleOffsets =
    [0, 2, 4, 5, 7, 9, 11];

  const ionianRoot =
    mod12(
      baseRoot -
      majorScaleOffsets[
        baseModeIndex
      ]
    );

  return mod12(
    ionianRoot +
    majorScaleOffsets[
      targetModeIndex
    ]
  );
}


/* =========================================================
   NPS HELPERS
   ========================================================= */

function getNpsIntervalForPitch(
  pitchClass,
  modeRoot,
  modeName
) {
  const distance =
    mod12(
      pitchClass -
      modeRoot
    );

  return getScaleInterval(
    modeName,
    distance
  );
}

function getGenericDegreeForNpsInterval(
  modeName,
  intervalName
) {
  const scaleItem =
    scales[modeName].find(
      ([semitones, name]) =>
        name === intervalName
    );

  if (!scaleItem) {
    return null;
  }

  return genericDegreeBySemitone[
    scaleItem[0]
  ];
}


/* =========================================================
   NOTES PER STRING

   Reference shapes:

   Normal:
       3 3 | 3 2 3 2 3 2

   Locrian:
       4 2 | 3 2 3 2 3 2
   ========================================================= */

function getNpsShapesForString(
  modeName,
  stringIndex
) {
  const rules =
    npsShapeRules[modeName];

  return stringIndex < 2
    ? rules.firstTwo
    : rules.remaining;
}


/* =========================================================
   GET PENTATONIC NOTES ON STRING
   ========================================================= */

function getPentatonicCellsForString(
  cells,
  stringIndex,
  modeRoot,
  modeName
) {
  const allowedSemitones =
    new Set(
      npsPentatonicSemitones[
        modeName
      ]
    );

  return cells
    .filter(
      item =>
        item.stringIndex ===
        stringIndex
    )
    .filter(
      item => {
        const relative =
          mod12(
            midiToPitchClass(
              item.absolutePitch
            ) -
            modeRoot
          );

        return allowedSemitones
          .has(relative);
      }
    )
    .sort(
      (a, b) =>
        a.absolutePitch -
        b.absolutePitch
    );
}


/* =========================================================
   MATCH AN EXPLICIT NPS SHAPE ON ONE STRING
   ========================================================= */

function getNpsShapeMatchesOnString(
  candidates,
  shapes,
  modeRoot,
  modeName,
  previousPitch
) {
  const matches = [];

  shapes.forEach(
    shape => {
      for (
        let startIndex = 0;
        startIndex <=
          candidates.length -
            shape.length;
        startIndex++
      ) {
        const chosen =
          candidates.slice(
            startIndex,
            startIndex +
              shape.length
          );

        if (
          chosen[0].absolutePitch <=
          previousPitch
        ) {
          continue;
        }

        const actualShape =
          chosen.map(
            item =>
              getNpsIntervalForPitch(
                midiToPitchClass(
                  item.absolutePitch
                ),
                modeRoot,
                modeName
              )
          );

        const exactMatch =
          shape.every(
            (interval, index) =>
              actualShape[index] ===
              interval
          );

        if (exactMatch) {
          matches.push({
            shape,
            chosen
          });
        }
      }
    }
  );

  return matches.sort(
    (a, b) => {
      const firstDifference =
        a.chosen[0].absolutePitch -
        b.chosen[0].absolutePitch;

      if (firstDifference !== 0) {
        return firstDifference;
      }

      return (
        a.chosen[
          a.chosen.length - 1
        ].absolutePitch -
        b.chosen[
          b.chosen.length - 1
        ].absolutePitch
      );
    }
  );
}


/* =========================================================
   CONNECTED 2/3 NPS PATHS

   IMPORTANT:
   Do not choose one shape for a string before we know
   whether it connects to the next string.

   For every string we keep ALL valid reference-shape
   matches, then recursively keep only combinations where
   the next string begins on the immediately following
   pentatonic note.

   This prevents gaps such as:
       4 -> b7
   when the pentatonic sequence requires:
       4 -> 5 -> b7
   ========================================================= */

function isNpsPitch(
  absolutePitch,
  modeRoot,
  modeName
) {
  const relative =
    mod12(
      midiToPitchClass(
        absolutePitch
      ) - modeRoot
    );

  return npsPentatonicSemitones[
    modeName
  ].includes(relative);
}


function npsShapesConnect(
  previousChosen,
  nextChosen,
  modeRoot,
  modeName
) {
  if (
    !previousChosen ||
    previousChosen.length === 0 ||
    !nextChosen ||
    nextChosen.length === 0
  ) {
    return false;
  }

  const previousPitch =
    previousChosen[
      previousChosen.length - 1
    ].absolutePitch;

  const nextPitch =
    nextChosen[0].absolutePitch;

  if (nextPitch <= previousPitch) {
    return false;
  }

  /*
    The first note on the next string must be the
    IMMEDIATELY NEXT pentatonic pitch after the last
    note on the previous string.

    If another pentatonic pitch exists between them,
    the two shapes do not connect.
  */

  for (
    let pitch = previousPitch + 1;
    pitch < nextPitch;
    pitch++
  ) {
    if (
      isNpsPitch(
        pitch,
        modeRoot,
        modeName
      )
    ) {
      return false;
    }
  }

  return true;
}


function getAllNpsShapeMatchesOnString(
  cells,
  stringIndex,
  modeRoot,
  modeName
) {
  const candidates =
    getPentatonicCellsForString(
      cells,
      stringIndex,
      modeRoot,
      modeName
    );

  const shapes =
    getNpsShapesForString(
      modeName,
      stringIndex
    );

  return getNpsShapeMatchesOnString(
    candidates,
    shapes,
    modeRoot,
    modeName,
    -Infinity
  );
}


function buildNpsDiagonalPaths(
  modeRoot,
  modeName,
  cells
) {
  const matchesByString = [];

  for (
    let stringIndex = 0;
    stringIndex < currentTuning.length;
    stringIndex++
  ) {
    const matches =
      getAllNpsShapeMatchesOnString(
        cells,
        stringIndex,
        modeRoot,
        modeName
      );

    if (matches.length === 0) {
      return [];
    }

    matchesByString.push(matches);
  }

  const completedPaths = [];

  function extendPath(
    stringIndex,
    chosenByString
  ) {
    if (
      stringIndex ===
      currentTuning.length
    ) {
      completedPaths.push(
        chosenByString.flat()
      );

      return;
    }

    const previousChosen =
      stringIndex === 0
        ? null
        : chosenByString[
            chosenByString.length - 1
          ];

    matchesByString[
      stringIndex
    ].forEach(
      match => {
        if (
          previousChosen &&
          !npsShapesConnect(
            previousChosen,
            match.chosen,
            modeRoot,
            modeName
          )
        ) {
          return;
        }

        extendPath(
          stringIndex + 1,
          [
            ...chosenByString,
            match.chosen
          ]
        );
      }
    );
  }

  extendPath(0, []);

  return completedPaths;
}


/* =========================================================
   NPS EXERCISE CANDIDATES

   Selection order:

   1. Keep ALL connected full patterns.
   2. Find every requested target interval/string position
      contained by those patterns.
   3. Each surviving pattern + target position is a valid
      exercise candidate.
   4. If a target/root/string combination has no connected
      pattern, it simply produces no candidate; another valid
      combination is selected.
   ========================================================= */

function getNpsExerciseCandidates(
  cells,
  baseRoot,
  baseMode
) {
  const allowedModes =
    getSelectedNpsModes();

  const allowedDegrees =
    new Set(
      getSelectedStartDegrees()
    );

  const allowedDirections =
    getSelectedDirections();

  const exercises = [];
  const seenExercises =
    new Set();


  allowedModes.forEach(
    modeName => {

      const modeRoot =
        getRelativeModeRoot(
          baseRoot,
          baseMode,
          modeName
        );

      const paths =
        buildNpsDiagonalPaths(
          modeRoot,
          modeName,
          cells
        );

      paths.forEach(
        path => {

          path.forEach(
            (
              start,
              startIndex
            ) => {

              const startInterval =
                getNpsIntervalForPitch(
                  midiToPitchClass(
                    start.absolutePitch
                  ),
                  modeRoot,
                  modeName
                );

              if (!startInterval) {
                return;
              }

              const genericDegree =
                getGenericDegreeForNpsInterval(
                  modeName,
                  startInterval
                );

              if (
                !allowedDegrees.has(
                  genericDegree
                )
              ) {
                return;
              }


              allowedDirections.forEach(
                direction => {

                  let selectedPath;


                  if (
                    direction === 'up'
                  ) {
                    selectedPath =
                      path.slice(
                        startIndex
                      );
                  }

                  else if (
                    direction === 'down'
                  ) {
                    selectedPath =
                      path
                        .slice(
                          0,
                          startIndex + 1
                        )
                        .reverse();
                  }

                  else {
                    selectedPath =
                      [...path];
                  }


                  /*
                    UP/DOWN must extend across
                    at least two strings.
                  */

                  if (
                    direction !== 'upDown'
                  ) {
                    const strings =
                      new Set(
                        selectedPath.map(
                          item =>
                            item.stringIndex
                        )
                      );

                    if (
                      strings.size < 2
                    ) {
                      return;
                    }
                  }


                  const requiredCellKeys =
                    new Set(
                      selectedPath.map(
                        item =>
                          makeCellKey(
                            item.stringIndex,
                            item.fret
                          )
                      )
                    );

                  const startCellKey =
                    makeCellKey(
                      start.stringIndex,
                      start.fret
                    );

                  /*
                    Multiple recursive routes can occasionally
                    describe the same visible exercise. Keep
                    only one copy of each exact result.
                  */

                  const exerciseKey =
                    [
                      modeName,
                      modeRoot,
                      direction,
                      startCellKey,
                      [...requiredCellKeys]
                        .join(',')
                    ].join('|');

                  if (
                    seenExercises.has(
                      exerciseKey
                    )
                  ) {
                    return;
                  }

                  seenExercises.add(
                    exerciseKey
                  );


                  exercises.push({
                    mode:
                      modeName,

                    modeRoot,

                    direction,

                    startInterval,

                    startIndex,

                    startCellKey,

                    startStringIndex:
                      start.stringIndex,

                    startStringName:
                      midiToScientificPitch(
                        currentTuning[
                          start.stringIndex
                        ]
                      ),

                    fullPath:
                      [...path],

                    path:
                      selectedPath,

                    requiredCellKeys,

                    remainingCellKeys:
                      new Set(
                        requiredCellKeys
                      )
                  });
                }
              );
            }
          );
        }
      );
    }
  );


  return exercises;
}


/* =========================================================
   R-R PENTATONIC + COLOR NOTES

   Repeating string pattern:

     String 1: R - 3
     String 2: 5
     String 3: 7 - R - 3
     String 4: 5
     String 5: 7 - R - 3
     ...

   The R on each third-pattern string begins the next cycle.

   Color-note additions:
     Phrygian -> b2 beside R - b3
     Dorian   -> 6 beside 5
     Aeolian  -> b6 beside 5
   ========================================================= */

function getRrPentGroups(modeName) {
  const scale =
    scales[modeName];

  const groupA = [
    {
      semitone:
        scale[0][0],

      interval:
        scale[0][1]
    },
    {
      semitone:
        scale[2][0],

      interval:
        scale[2][1]
    }
  ];

  const groupB = [
    {
      semitone:
        scale[4][0],

      interval:
        scale[4][1]
    }
  ];

  /*
    C finishes the current cycle with 7, then immediately
    begins the next cycle on the SAME string with R - 3.
  */
  const groupC = [
    {
      semitone:
        scale[6][0],

      interval:
        scale[6][1]
    },
    {
      semitone: 12,
      interval: 'R'
    },
    {
      semitone:
        12 +
        scale[2][0],

      interval:
        scale[2][1]
    }
  ];

  if (
    getRrColorNotesEnabled() &&
    modeName ===
      'phrygian'
  ) {
    const colorNote = {
      semitone:
        scale[1][0],

      interval:
        scale[1][1]
    };

    groupA.splice(
      1,
      0,
      colorNote
    );

    groupC.splice(
      2,
      0,
      {
        semitone:
          12 +
          colorNote.semitone,

        interval:
          colorNote.interval
      }
    );
  }

  if (
    getRrColorNotesEnabled() &&
    (
      modeName ===
        'dorian' ||
      modeName ===
        'aeolian'
    )
  ) {
    groupB.push({
      semitone:
        scale[5][0],

      interval:
        scale[5][1]
    });
  }

  return {
    A: groupA,
    B: groupB,
    C: groupC
  };
}

function buildRrPentPlacementsForString(
  cells,
  stringIndex,
  modeRoot,
  modeName,
  groupName
) {
  const group =
    getRrPentGroups(
      modeName
    )[groupName];

  const cellByFret =
    new Map(
      cells
        .filter(
          item =>
            item.stringIndex ===
            stringIndex
        )
        .map(
          item => [
            item.fret,
            item
          ]
        )
    );

  const placements = [];

  for (
    let rootMidi = modeRoot;
    rootMidi <= 127;
    rootMidi += 12
  ) {
    const chosen = [];
    let valid = true;

    for (
      const note of group
    ) {
      const fret =
        rootMidi +
        note.semitone -
        currentTuning[
          stringIndex
        ];

      const item =
        cellByFret.get(
          fret
        );

      if (
        !item ||
        fret < 0 ||
        fret > 24
      ) {
        valid = false;
        break;
      }

      chosen.push({
        ...item,

        rrInterval:
          note.interval,

        rrGroupName:
          groupName,

        rrGroupNoteIndex:
          chosen.length,

        rrGroupSize:
          group.length
      });
    }

    if (valid) {
      placements.push({
        stringIndex,
        groupName,
        rootMidi,
        chosen
      });
    }
  }

  return placements;
}

function getRrPentTransition(
  groupName
) {
  if (
    groupName === 'A'
  ) {
    return {
      nextGroupName: 'B',
      cycleShift: 0
    };
  }

  if (
    groupName === 'B'
  ) {
    return {
      nextGroupName: 'C',
      cycleShift: 0
    };
  }

  return {
    nextGroupName: 'B',
    cycleShift: 12
  };
}

function rrPentPlacementsConnect(
  lowerPlacement,
  upperPlacement,
  modeName
) {
  const transition =
    getRrPentTransition(
      lowerPlacement.groupName
    );

  if (
    upperPlacement.groupName !==
      transition.nextGroupName
  ) {
    return false;
  }

  const groups =
    getRrPentGroups(
      modeName
    );

  const lowerGroup =
    groups[
      lowerPlacement.groupName
    ];

  const upperGroup =
    groups[
      upperPlacement.groupName
    ];

  const lowerLastSemitone =
    lowerGroup[
      lowerGroup.length - 1
    ].semitone;

  const upperFirstSemitone =
    transition.cycleShift +
    upperGroup[0].semitone;

  const expectedGap =
    upperFirstSemitone -
    lowerLastSemitone;

  const lowerLast =
    lowerPlacement.chosen[
      lowerPlacement.chosen.length - 1
    ];

  const upperFirst =
    upperPlacement.chosen[0];

  return (
    upperFirst.absolutePitch -
    lowerLast.absolutePitch ===
    expectedGap
  );
}

function buildRrPentPaths(
  modeRoot,
  modeName,
  cells
) {
  const placementsByString = [];

  for (
    let stringIndex = 0;
    stringIndex <
      currentTuning.length;
    stringIndex++
  ) {
    placementsByString.push({
      A:
        buildRrPentPlacementsForString(
          cells,
          stringIndex,
          modeRoot,
          modeName,
          'A'
        ),

      B:
        buildRrPentPlacementsForString(
          cells,
          stringIndex,
          modeRoot,
          modeName,
          'B'
        ),

      C:
        buildRrPentPlacementsForString(
          cells,
          stringIndex,
          modeRoot,
          modeName,
          'C'
        )
    });
  }

  const nodes = [];

  placementsByString.forEach(
    groups => {
      nodes.push(
        ...groups.A,
        ...groups.B,
        ...groups.C
      );
    }
  );

  const successors =
    new Map();

  const predecessors =
    new Map();

  nodes.forEach(
    node => {
      successors.set(
        node,
        []
      );

      predecessors.set(
        node,
        []
      );
    }
  );

  nodes.forEach(
    lower => {
      const upperString =
        lower.stringIndex + 1;

      if (
        upperString >=
        currentTuning.length
      ) {
        return;
      }

      const transition =
        getRrPentTransition(
          lower.groupName
        );

      placementsByString[
        upperString
      ][
        transition
          .nextGroupName
      ].forEach(
        upper => {
          if (
            !rrPentPlacementsConnect(
              lower,
              upper,
              modeName
            )
          ) {
            return;
          }

          successors
            .get(lower)
            .push(upper);

          predecessors
            .get(upper)
            .push(lower);
        }
      );
    }
  );

  const maximalChains = [];

  function extend(
    node,
    chain
  ) {
    const next =
      successors.get(node);

    if (
      !next ||
      next.length === 0
    ) {
      maximalChains.push(
        chain
      );
      return;
    }

    next.forEach(
      successor =>
        extend(
          successor,
          [
            ...chain,
            successor
          ]
        )
    );
  }

  nodes
    .filter(
      node =>
        predecessors
          .get(node)
          .length === 0
    )
    .forEach(
      start =>
        extend(
          start,
          [start]
        )
    );

  const paths = [];
  const seen = new Set();

  maximalChains.forEach(
    chain => {
      if (
        chain.length < 2
      ) {
        return;
      }

      const path =
        chain.flatMap(
          placement =>
            placement.chosen
        );

      const key =
        path
          .map(
            item =>
              makeCellKey(
                item.stringIndex,
                item.fret
              )
          )
          .join(',');

      if (
        seen.has(key)
      ) {
        return;
      }

      seen.add(key);
      paths.push(path);
    }
  );

  return paths;
}

function getRrPentExerciseCandidates(
  cells,
  baseRoot,
  baseMode
) {
  const allowedModes =
    getSelectedNpsModes();

  const allowedDirections =
    getSelectedDirections();

  const exercises = [];
  const seenExercises =
    new Set();

  allowedModes.forEach(
    modeName => {
      const modeRoot =
        getRelativeModeRoot(
          baseRoot,
          baseMode,
          modeName
        );

      const paths =
        buildRrPentPaths(
          modeRoot,
          modeName,
          cells
        );

      paths.forEach(
        path => {
          path.forEach(
            (
              start,
              startIndex
            ) => {
              /*
                Every R in the generated path is a valid
                cycle boundary.

                The first cycle begins:
                  R - 3
                  5
                  7 - R - 3

                After that, the R inside each C group begins
                the next cycle on that same string.
              */
              const ascendingRoot =
                start.rrInterval ===
                  'R';

              const descendingRoot =
                ascendingRoot;

              allowedDirections.forEach(
                direction => {
                  const validStart =
                    direction === 'down'
                      ? descendingRoot
                      : ascendingRoot;

                  if (!validStart) {
                    return;
                  }

                  let selectedPath;

                  if (
                    direction === 'up'
                  ) {
                    selectedPath =
                      path.slice(
                        startIndex
                      );
                  } else if (
                    direction === 'down'
                  ) {
                    selectedPath =
                      path
                        .slice(
                          0,
                          startIndex + 1
                        )
                        .reverse();
                  } else {
                    selectedPath =
                      [...path];
                  }

                  /*
                    UP/DOWN must actually continue onto
                    at least one adjacent string.
                  */
                  if (
                    direction !== 'upDown'
                  ) {
                    const strings =
                      new Set(
                        selectedPath.map(
                          item =>
                            item.stringIndex
                        )
                      );

                    if (
                      strings.size < 2
                    ) {
                      return;
                    }
                  }

                  const requiredCellKeys =
                    new Set(
                      selectedPath.map(
                        item =>
                          makeCellKey(
                            item.stringIndex,
                            item.fret
                          )
                      )
                    );

                  const startCellKey =
                    makeCellKey(
                      start.stringIndex,
                      start.fret
                    );

                  const exerciseKey =
                    [
                      modeName,
                      modeRoot,
                      direction,
                      startCellKey,
                      [
                        ...requiredCellKeys
                      ]
                        .sort()
                        .join(',')
                    ].join('|');

                  if (
                    seenExercises.has(
                      exerciseKey
                    )
                  ) {
                    return;
                  }

                  seenExercises.add(
                    exerciseKey
                  );

                  exercises.push({
                    mode:
                      modeName,

                    modeRoot,

                    direction,

                    startInterval:
                      'R',

                    startIndex,

                    startCellKey,

                    startStringIndex:
                      start.stringIndex,

                    startStringName:
                      midiToScientificPitch(
                        currentTuning[
                          start.stringIndex
                        ]
                      ),

                    fullPath:
                      [...path],

                    path:
                      selectedPath,

                    requiredCellKeys,

                    remainingCellKeys:
                      new Set(
                        requiredCellKeys
                      )
                  });
                }
              );
            }
          );
        }
      );
    }
  );

  return exercises;
}

/* =========================================================
   CAGED PENTATONIC — 35 EXPLICIT MODE/SHAPE TEMPLATES

   Storage convention:
     - outer six entries = physical strings 3 -> 8
       (low -> high within the CAGED six-string block)
     - each string has exactly two notes
     - fret is relative to the shape's anchor-root fret column
     - fret 0 = anchor-root fret column
     - intervals are stored explicitly at every coordinate

   IMPORTANT:
     - these are canonical data, not generated "closest notes"
     - C/A/G/E/D never shift vertically
     - only horizontal/octave transposition is allowed
   ========================================================= */

const cagedPentatonicShapes = {
  ionian: {
    C: [
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: '7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: '3' }, { fret: 2, interval: '4' }],
      [{ fret: -1, interval: '5' }, { fret: 3, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }]
    ],
    A: [
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: '7' }, { fret: 2, interval: 'R' }],
      [{ fret: 2, interval: '3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }]
    ],
    G: [
      [{ fret: 2, interval: '7' }, { fret: 3, interval: 'R' }],
      [{ fret: 2, interval: '3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 1, interval: '4' }, { fret: 3, interval: '5' }],
      [{ fret: 2, interval: '7' }, { fret: 3, interval: 'R' }]
    ],
    E: [
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: '7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: '3' }, { fret: 2, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }]
    ],
    D: [
      [{ fret: 2, interval: '3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 2, interval: '7' }, { fret: 3, interval: 'R' }],
      [{ fret: 2, interval: '3' }, { fret: 3, interval: '4' }]
    ]
  },

  dorian: {
    C: [
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 0, interval: 'b3' }, { fret: 2, interval: '4' }],
      [{ fret: -1, interval: '5' }, { fret: 2, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }]
    ],
    A: [
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }]
    ],
    G: [
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 1, interval: '4' }, { fret: 3, interval: '5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }]
    ],
    E: [
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 0, interval: 'b3' }, { fret: 2, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }]
    ],
    D: [
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }]
    ]
  },

  phrygian: {
    C: [
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 0, interval: 'b3' }, { fret: 2, interval: '4' }],
      [{ fret: -1, interval: '5' }, { fret: 2, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }]
    ],
    A: [
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }]
    ],
    G: [
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 1, interval: '4' }, { fret: 3, interval: '5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }]
    ],
    E: [
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 0, interval: 'b3' }, { fret: 2, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }]
    ],
    D: [
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }]
    ]
  },

  lydian: {
    C: [
      [{ fret: 1, interval: '#4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: '7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: '3' }, { fret: 3, interval: '#4' }],
      [{ fret: -1, interval: '5' }, { fret: 3, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 1, interval: '#4' }, { fret: 2, interval: '5' }]
    ],
    A: [
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 1, interval: '#4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: '7' }, { fret: 2, interval: 'R' }],
      [{ fret: 2, interval: '3' }, { fret: 4, interval: '#4' }],
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }]
    ],
    G: [
      [{ fret: 2, interval: '7' }, { fret: 3, interval: 'R' }],
      [{ fret: 2, interval: '3' }, { fret: 4, interval: '#4' }],
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 2, interval: '#4' }, { fret: 3, interval: '5' }],
      [{ fret: 2, interval: '7' }, { fret: 3, interval: 'R' }]
    ],
    E: [
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 1, interval: '#4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: '7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: '3' }, { fret: 3, interval: '#4' }],
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }]
    ],
    D: [
      [{ fret: 2, interval: '3' }, { fret: 4, interval: '#4' }],
      [{ fret: 0, interval: '5' }, { fret: 4, interval: '7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 1, interval: '#4' }, { fret: 2, interval: '5' }],
      [{ fret: 2, interval: '7' }, { fret: 3, interval: 'R' }],
      [{ fret: 2, interval: '3' }, { fret: 4, interval: '#4' }]
    ]
  },

  mixolydian: {
    C: [
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: '3' }, { fret: 2, interval: '4' }],
      [{ fret: -1, interval: '5' }, { fret: 2, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }]
    ],
    A: [
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 2, interval: '3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }]
    ],
    G: [
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 2, interval: '3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 1, interval: '4' }, { fret: 3, interval: '5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }]
    ],
    E: [
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: '3' }, { fret: 2, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }]
    ],
    D: [
      [{ fret: 2, interval: '3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 4, interval: '3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 2, interval: '3' }, { fret: 3, interval: '4' }]
    ]
  },

  aeolian: {
    C: [
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 0, interval: 'b3' }, { fret: 2, interval: '4' }],
      [{ fret: -1, interval: '5' }, { fret: 2, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }]
    ],
    A: [
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }]
    ],
    G: [
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 1, interval: '4' }, { fret: 3, interval: '5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }]
    ],
    E: [
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 0, interval: 'b3' }, { fret: 2, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }]
    ],
    D: [
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: 0, interval: '5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 2, interval: '5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }]
    ]
  },

  locrian: {
    C: [
      [{ fret: 0, interval: '4' }, { fret: 1, interval: 'b5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 0, interval: 'b3' }, { fret: 2, interval: '4' }],
      [{ fret: -2, interval: 'b5' }, { fret: 2, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 1, interval: 'b5' }]
    ],
    A: [
      [{ fret: -1, interval: 'b5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 1, interval: 'b5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: -1, interval: 'b5' }, { fret: 3, interval: 'b7' }]
    ],
    G: [
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: -1, interval: 'b5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 1, interval: '4' }, { fret: 2, interval: 'b5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }]
    ],
    E: [
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 1, interval: 'b5' }],
      [{ fret: 0, interval: 'b7' }, { fret: 2, interval: 'R' }],
      [{ fret: 0, interval: 'b3' }, { fret: 2, interval: '4' }],
      [{ fret: -1, interval: 'b5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }]
    ],
    D: [
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }],
      [{ fret: -1, interval: 'b5' }, { fret: 3, interval: 'b7' }],
      [{ fret: 0, interval: 'R' }, { fret: 3, interval: 'b3' }],
      [{ fret: 0, interval: '4' }, { fret: 1, interval: 'b5' }],
      [{ fret: 1, interval: 'b7' }, { fret: 3, interval: 'R' }],
      [{ fret: 1, interval: 'b3' }, { fret: 3, interval: '4' }]
    ]
  }
};

const cagedIntervalSemitones = {
  R: 0,
  b3: 3,
  '3': 4,
  '4': 5,
  '#4': 6,
  b5: 6,
  '5': 7,
  b7: 10,
  '7': 11
};

function validateCagedTemplate(
  modeName,
  template
) {
  if (
    !template ||
    template.length !== 6 ||
    template.some(
      stringNotes =>
        !Array.isArray(stringNotes) ||
        stringNotes.length !== 2
    )
  ) {
    return false;
  }

  const allowedSemitones =
    new Set(
      npsPentatonicSemitones[
        modeName
      ]
    );

  let anchorModulo = null;
  let rootCount = 0;

  for (
    let stringOffset = 0;
    stringOffset < 6;
    stringOffset++
  ) {
    for (
      const note of
      template[stringOffset]
    ) {
      if (
        !note ||
        !Number.isInteger(note.fret) ||
        !Object.prototype.hasOwnProperty.call(
          cagedIntervalSemitones,
          note.interval
        )
      ) {
        return false;
      }

      const intervalSemitone =
        cagedIntervalSemitones[
          note.interval
        ];

      if (
        !allowedSemitones.has(
          intervalSemitone
        )
      ) {
        return false;
      }

      if (
        note.interval === 'R'
      ) {
        rootCount++;

        const tuningPitchClass =
          midiToPitchClass(
            currentTuning[
              cagedBlockStartStringIndex +
              stringOffset
            ]
          );

        const impliedAnchor =
          mod12(
            -tuningPitchClass -
            note.fret
          );

        if (
          anchorModulo === null
        ) {
          anchorModulo =
            impliedAnchor;
        } else if (
          anchorModulo !==
          impliedAnchor
        ) {
          return false;
        }
      }
    }
  }

  return (
    rootCount > 0 &&
    anchorModulo !== null
  );
}


/*
  Build every octave copy of one exact mode/shape template
  that fits fully inside frets 0-24.

  anchorFret is the absolute fret corresponding to relative
  fret 0 in the stored template.
*/
function buildCagedTemplateCopies(
  cells,
  modeRoot,
  modeName,
  shapeName
) {
  const template =
    cagedPentatonicShapes[
      modeName
    ]?.[
      shapeName
    ];

  if (
    !validateCagedTemplate(
      modeName,
      template
    )
  ) {
    return [];
  }

  const cellByKey =
    new Map(
      cells.map(
        item => [
          makeCellKey(
            item.stringIndex,
            item.fret
          ),
          item
        ]
      )
    );

  let rootReference = null;

  for (
    let stringOffset = 0;
    stringOffset < 6 &&
    !rootReference;
    stringOffset++
  ) {
    rootReference =
      template[
        stringOffset
      ].find(
        note =>
          note.interval === 'R'
      );

    if (
      rootReference
    ) {
      rootReference = {
        stringOffset,
        fret:
          rootReference.fret
      };
    }
  }

  if (!rootReference) {
    return [];
  }

  const rootStringIndex =
    cagedBlockStartStringIndex +
    rootReference.stringOffset;

  const rootStringPitchClass =
    midiToPitchClass(
      currentTuning[
        rootStringIndex
      ]
    );

  const anchorModulo =
    mod12(
      modeRoot -
      rootStringPitchClass -
      rootReference.fret
    );

  const results = [];
  const seen = new Set();

  for (
    let octaveShift = -36;
    octaveShift <= 36;
    octaveShift += 12
  ) {
    const anchorFret =
      anchorModulo +
      octaveShift;

    const shapeCells = [];
    let valid = true;

    for (
      let stringOffset = 0;
      stringOffset < 6;
      stringOffset++
    ) {
      const stringIndex =
        cagedBlockStartStringIndex +
        stringOffset;

      for (
        const templateNote of
        template[
          stringOffset
        ]
      ) {
        const fret =
          anchorFret +
          templateNote.fret;

        if (
          fret < 0 ||
          fret > 24
        ) {
          valid = false;
          break;
        }

        const item =
          cellByKey.get(
            makeCellKey(
              stringIndex,
              fret
            )
          );

        if (!item) {
          valid = false;
          break;
        }

        const actualRelative =
          mod12(
            midiToPitchClass(
              item.absolutePitch
            ) -
            modeRoot
          );

        const expectedRelative =
          cagedIntervalSemitones[
            templateNote.interval
          ];

        if (
          actualRelative !==
          expectedRelative
        ) {
          valid = false;
          break;
        }

        shapeCells.push(
          item
        );
      }

      if (!valid) {
        break;
      }
    }

    if (!valid) {
      continue;
    }

    const requiredCellKeys =
      new Set(
        shapeCells.map(
          item =>
            makeCellKey(
              item.stringIndex,
              item.fret
            )
        )
      );

    const key =
      [
        modeName,
        shapeName,
        ...[
          ...requiredCellKeys
        ].sort()
      ].join('|');

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);

    results.push({
      shapeName,
      blockStartString:
        cagedBlockStartStringIndex,
      blockEndString:
        cagedBlockEndStringIndex,
      shapeCells,
      requiredCellKeys,
      templateAnchorFret:
        anchorFret
    });
  }

  return results;
}


function getCagedStartCandidates(
  shapeCells,
  modeRoot,
  modeName,
  allowedDegrees
) {
  return shapeCells.filter(
    item => {
      const interval =
        getNpsIntervalForPitch(
          midiToPitchClass(
            item.absolutePitch
          ),
          modeRoot,
          modeName
        );

      const degree =
        getGenericDegreeForNpsInterval(
          modeName,
          interval
        );

      return (
        degree &&
        allowedDegrees.has(
          degree
        )
      );
    }
  );
}


/*
  Every enabled, real CAGED template that fits on the
  24-fret board for the selected mode.
*/
function getFittingCagedShapesForMode(
  cells,
  modeRoot,
  modeName,
  allowedShapes
) {
  const results = [];


  allowedShapes.forEach(
    shapeName => {
      results.push(
        ...buildCagedTemplateCopies(
          cells,
          modeRoot,
          modeName,
          shapeName
        )
      );
    }
  );


  return results;
}


/*
  Return every cell at the requested pitch extreme of a
  fitting CAGED template.

  bottom = lowest absolute pitch
  top    = highest absolute pitch
*/
function getCagedShapeExtremeKeys(
  shape,
  extreme
) {
  if (
    !shape ||
    !shape.shapeCells ||
    shape.shapeCells.length === 0
  ) {
    return [];
  }

  const extremePitch =
    extreme === 'bottom'
      ? Math.min(
          ...shape.shapeCells.map(
            item =>
              item.absolutePitch
          )
        )
      : Math.max(
          ...shape.shapeCells.map(
            item =>
              item.absolutePitch
          )
        );

  return shape.shapeCells
    .filter(
      item =>
        item.absolutePitch ===
          extremePitch
    )
    .map(
      item =>
        makeCellKey(
          item.stringIndex,
          item.fret
        )
    );
}


/*
  Build an NPS bridge from the selected coordinate into ONE
  real CAGED template.

  If the bridge goes up:
    ↗️ into the BOTTOM of the CAGED template.

  If the bridge goes down:
    ↙️ into the TOP of the CAGED template.
*/
function getCagedNpsFallbacks(
  cells,
  modeRoot,
  modeName,
  rootAnchor,
  allowedShapes,
  allowedDegrees,
  sides
) {
  const rootKey =
    makeCellKey(
      rootAnchor.stringIndex,
      rootAnchor.fret
    );

  const npsPaths =
    buildNpsDiagonalPaths(
      modeRoot,
      modeName,
      cells
    );

  const fittingCagedShapes =
    getFittingCagedShapesForMode(
      cells,
      modeRoot,
      modeName,
      allowedShapes
    );


  if (
    npsPaths.length === 0 ||
    fittingCagedShapes.length === 0
  ) {
    return [];
  }


  const bottomShapesByCell =
    new Map();

  const topShapesByCell =
    new Map();


  function addShapeToMap(
    map,
    key,
    shape
  ) {
    if (
      !map.has(
        key
      )
    ) {
      map.set(
        key,
        []
      );
    }

    map.get(
      key
    ).push(
      shape
    );
  }


  fittingCagedShapes.forEach(
    shape => {
      getCagedShapeExtremeKeys(
        shape,
        'bottom'
      ).forEach(
        key =>
          addShapeToMap(
            bottomShapesByCell,
            key,
            shape
          )
      );

      getCagedShapeExtremeKeys(
        shape,
        'top'
      ).forEach(
        key =>
          addShapeToMap(
            topShapesByCell,
            key,
            shape
          )
      );
    }
  );


  const candidates = [];


  npsPaths.forEach(
    path => {
      const rootIndexes = [];

      path.forEach(
        (
          item,
          index
        ) => {
          if (
            makeCellKey(
              item.stringIndex,
              item.fret
            ) ===
              rootKey
          ) {
            rootIndexes.push(
              index
            );
          }
        }
      );


      rootIndexes.forEach(
        rootIndex => {
          sides.forEach(
            side => {
              const bridgeDirection =
                side === 'low'
                  ? 'up'
                  : 'down';

              const landingMap =
                bridgeDirection === 'up'
                  ? bottomShapesByCell
                  : topShapesByCell;

              /*
                UP:
                  start at the selected root and search forward
                  through the ascending NPS path. The connection
                  note is the HIGHEST note of the bridge and the
                  BOTTOM note of the CAGED shape.

                DOWN:
                  start at the selected root and search backward
                  through the NPS path. The connection note is the
                  LOWEST note of the bridge and the TOP note of the
                  CAGED shape.
              */
              const endpointIndexes =
                bridgeDirection === 'up'
                  ? Array.from(
                      {
                        length:
                          path.length -
                          rootIndex -
                          1
                      },
                      (
                        _,
                        offset
                      ) =>
                        rootIndex +
                        1 +
                        offset
                    )
                  : Array.from(
                      {
                        length:
                          rootIndex
                      },
                      (
                        _,
                        offset
                      ) =>
                        rootIndex -
                        1 -
                        offset
                    );


              endpointIndexes.forEach(
                endpointIndex => {
                  const endpoint =
                    path[
                      endpointIndex
                    ];

                  const endpointKey =
                    makeCellKey(
                      endpoint.stringIndex,
                      endpoint.fret
                    );

                  const landingShapes =
                    landingMap.get(
                      endpointKey
                    );

                  if (
                    !landingShapes ||
                    landingShapes.length === 0
                  ) {
                    return;
                  }


                  const segmentStart =
                    Math.min(
                      rootIndex,
                      endpointIndex
                    );

                  const segmentEnd =
                    Math.max(
                      rootIndex,
                      endpointIndex
                    );

                  const bridgeCells =
                    path.slice(
                      segmentStart,
                      segmentEnd + 1
                    );

                  const bridgeStrings =
                    new Set(
                      bridgeCells.map(
                        item =>
                          item.stringIndex
                      )
                    );


                  /*
                    Keep the same eligibility rule as the
                    directional 2/3-NPS lesson.
                  */
                  if (
                    bridgeStrings.size < 2
                  ) {
                    return;
                  }


                  const connectionCell =
                    bridgeDirection === 'up'
                      ? bridgeCells[
                          bridgeCells.length - 1
                        ]
                      : bridgeCells[0];

                  if (
                    makeCellKey(
                      connectionCell.stringIndex,
                      connectionCell.fret
                    ) !==
                      endpointKey
                  ) {
                    return;
                  }


                  landingShapes.forEach(
                    landingShape => {
                      const cellByKey =
                        new Map();


                      bridgeCells.forEach(
                        item => {
                          cellByKey.set(
                            makeCellKey(
                              item.stringIndex,
                              item.fret
                            ),
                            item
                          );
                        }
                      );


                      landingShape
                        .shapeCells
                        .forEach(
                          item => {
                            cellByKey.set(
                              makeCellKey(
                                item.stringIndex,
                                item.fret
                              ),
                              item
                            );
                          }
                        );


                      const combinedCells =
                        [
                          ...cellByKey
                            .values()
                        ];

                      const startCandidates =
                        getCagedStartCandidates(
                          combinedCells,
                          modeRoot,
                          modeName,
                          allowedDegrees
                        );

                      if (
                        startCandidates.length === 0
                      ) {
                        return;
                      }


                      const requiredCellKeys =
                        new Set(
                          cellByKey.keys()
                        );


                      const bridgeStartItem =
                        bridgeDirection === 'up'
                          ? bridgeCells[0]
                          : bridgeCells[
                              bridgeCells.length - 1
                            ];

                      const bridgeStartInterval =
                        getNpsIntervalForPitch(
                          midiToPitchClass(
                            bridgeStartItem.absolutePitch
                          ),
                          modeRoot,
                          modeName
                        );


                      candidates.push({
                        shapeName:
                          landingShape.shapeName,

                        usesNpsBridge:
                          true,

                        fallbackSide:
                          side,

                        bridgeDirection,

                        connectionCellKey:
                          endpointKey,

                        bridgeCells,

                        bridgeCellKeys:
                          new Set(
                            bridgeCells.map(
                              item =>
                                makeCellKey(
                                  item.stringIndex,
                                  item.fret
                                )
                            )
                          ),

                        bridgeStartInterval,

                        bridgeStartCellKey:
                          makeCellKey(
                            bridgeStartItem.stringIndex,
                            bridgeStartItem.fret
                          ),

                        bridgeStartStringIndex:
                          bridgeStartItem.stringIndex,

                        bridgeStartStringName:
                          midiToScientificPitch(
                            currentTuning[
                              bridgeStartItem.stringIndex
                            ]
                          ),

                        cagedShape:
                          landingShape,

                        startCandidates,

                        requiredCellKeys,

                        /*
                          Prefer the nearest valid connection.
                          Ties prefer the shorter full NPS bridge.
                        */
                        bridgeDistance:
                          Math.abs(
                            endpointIndex -
                            rootIndex
                          ),

                        bridgeLength:
                          bridgeCells.length
                      });
                    }
                  );
                }
              );
            }
          );
        }
      );
    }
  );


  if (
    candidates.length === 0
  ) {
    return [];
  }


  const bestDistance =
    Math.min(
      ...candidates.map(
        candidate =>
          candidate.bridgeDistance
      )
    );

  const closest =
    candidates.filter(
      candidate =>
        candidate.bridgeDistance ===
          bestDistance
    );

  const bestLength =
    Math.min(
      ...closest.map(
        candidate =>
          candidate.bridgeLength
      )
    );


  return closest.filter(
    candidate =>
      candidate.bridgeLength ===
        bestLength
  );
}


function createCagedExercise(
  cells,
  baseRoot,
  baseMode
) {
  const allowedModes =
    getSelectedNpsModes();

  const allowedShapes =
    getSelectedCagedShapes();

  const allowedDegrees =
    new Set(
      getSelectedStartDegrees()
    );


  if (
    allowedModes.length === 0 ||
    allowedShapes.length === 0
  ) {
    return null;
  }


  /*
    CAGED LESSON SELECTION ORDER

    1. Pick a random enabled relative mode of the base key.

    2. Pick ANY eligible diatonic fret/string coordinate
       on frets 0-12, strings 1-8.
       The Start filter limits the modal scale degrees that
       can be selected. Default Start = R.

    3. Ask whether ANY enabled, physically valid CAGED
       pentatonic shape already CONTAINS that exact coordinate.
       The selected coordinate does NOT have to be a CAGED
       root.

    4. If yes:
         use one of those direct CAGED shapes.

    5. If no:
         use the selected coordinate as the start of an
         eligible 2/3-NPS bridge and connect it into ONE
         enabled CAGED shape that fits elsewhere.

       We search both valid connection directions:
         ↗️ into the bottom of a CAGED shape
         ↙️ into the top of a CAGED shape
  */

  const shuffledModes =
    shuffleList(
      allowedModes
    );


  for (
    const modeName of
    shuffledModes
  ) {
    const modeRoot =
      getRelativeModeRoot(
        baseRoot,
        baseMode,
        modeName
      );


    /*
      All normal CAGED landing shapes for this mode.
      Their root/string positions remain locked by the CAGED
      definitions; this does NOT move those shapes vertically.
    */
    const fittingCagedShapes =
      getFittingCagedShapesForMode(
        cells,
        modeRoot,
        modeName,
        allowedShapes
      );


    if (
      fittingCagedShapes.length === 0
    ) {
      continue;
    }


    const startCoordinates =
      shuffleList(
        cells.filter(
          item => {
            if (
              item.fret < 0 ||
              item.fret > 12
            ) {
              return false;
            }


            const pitchClass =
              midiToPitchClass(
                item.absolutePitch
              );


            /*
              Must be diatonic to the selected BASE key.
              Relative modes share this same seven-note set.
            */
            const baseDistance =
              mod12(
                pitchClass -
                baseRoot
              );

            const baseScaleInterval =
              getScaleInterval(
                baseMode,
                baseDistance
              );

            if (
              !baseScaleInterval
            ) {
              return false;
            }


            /*
              Apply the Start filter relative to the randomly
              selected mode.
            */
            const modeInterval =
              getNpsIntervalForPitch(
                pitchClass,
                modeRoot,
                modeName
              );

            if (
              !modeInterval
            ) {
              return false;
            }

            const genericDegree =
              getGenericDegreeForNpsInterval(
                modeName,
                modeInterval
              );

            return (
              genericDegree &&
              allowedDegrees.has(
                genericDegree
              )
            );
          }
        )
      );


    for (
      const startItem of
      startCoordinates
    ) {
      const startCellKey =
        makeCellKey(
          startItem.stringIndex,
          startItem.fret
        );


      /*
        DIRECT CAGED:
        does a normal fitting CAGED shape contain the exact
        randomly selected coordinate?
      */
      const directCandidates =
        fittingCagedShapes
          .filter(
            shape =>
              shape.requiredCellKeys
                .has(
                  startCellKey
                )
          )
          .map(
            shape => ({
              ...shape,

              usesNpsBridge:
                false,

              startCandidates:
                [startItem]
            })
          );


      let candidates =
        directCandidates;


      /*
        NO DIRECT CAGED SHAPE AT THIS COORDINATE:
        start a 2/3-NPS bridge here and connect it into ONE
        fitting enabled CAGED shape.

        Do not try to connect "into the failed coordinate."
        The selected coordinate is the NPS START.
      */
      if (
        candidates.length === 0
      ) {
        candidates =
          getCagedNpsFallbacks(
            cells,
            modeRoot,
            modeName,
            startItem,
            allowedShapes,
            allowedDegrees,
            [
              'low',
              'high'
            ]
          );
      }


      if (
        candidates.length === 0
      ) {
        /*
          This particular coordinate cannot produce a valid
          direct shape or NPS-to-CAGED connection. Continue
          through the randomized coordinate list.
        */
        continue;
      }


      const selectedCandidate =
        randomItem(
          candidates
        );

      const startInterval =
        getNpsIntervalForPitch(
          midiToPitchClass(
            startItem.absolutePitch
          ),
          modeRoot,
          modeName
        );


      return {
        mode:
          modeName,

        modeRoot,

        shapeName:
          selectedCandidate.shapeName,

        usesNpsBridge:
          Boolean(
            selectedCandidate
              .usesNpsBridge
          ),

        fallbackSide:
          selectedCandidate
            .fallbackSide ||
          null,

        bridgeDirection:
          selectedCandidate
            .bridgeDirection ||
          null,

        connectionCellKey:
          selectedCandidate
            .connectionCellKey ||
          null,

        bridgeCellKeys:
          new Set(
            selectedCandidate
              .bridgeCellKeys ||
            []
          ),

        bridgeStartInterval:
          selectedCandidate
            .bridgeStartInterval ||
          null,

        bridgeStartCellKey:
          selectedCandidate
            .bridgeStartCellKey ||
          null,

        bridgeStartStringIndex:
          Number.isInteger(
            selectedCandidate
              .bridgeStartStringIndex
          )
            ? selectedCandidate
                .bridgeStartStringIndex
            : null,

        bridgeStartStringName:
          selectedCandidate
            .bridgeStartStringName ||
          null,

        /*
          The randomly selected coordinate is THE lesson
          start coordinate, whether the result is direct
          CAGED or NPS -> CAGED.
        */
        rootCellKey:
          startCellKey,

        selectedRootStringIndex:
          startItem.stringIndex,

        selectedRootFret:
          startItem.fret,

        startInterval,

        startCellKey,

        startStringIndex:
          startItem.stringIndex,

        startStringName:
          midiToScientificPitch(
            currentTuning[
              startItem.stringIndex
            ]
          ),

        requiredCellKeys:
          new Set(
            selectedCandidate
              .requiredCellKeys
          ),

        remainingCellKeys:
          new Set(
            selectedCandidate
              .requiredCellKeys
          )
      };
    }
  }


  return null;
}


function displayCagedQuestion() {
  const answerDisplay =
    document.getElementById(
      'answerNote'
    );

  const exercise =
    currentCagedExercise;

  if (!exercise) {
    answerDisplay.textContent =
      'Done!';

    return;
  }

  answerDisplay.innerHTML = '';
  answerDisplay.className =
    'npsExerciseCard';

  const primaryLine =
    document.createElement(
      'div'
    );

  primaryLine.className =
    'npsExercisePrimary';

  const mode =
    document.createElement(
      'span'
    );

  mode.className =
    'npsExerciseMode';

  mode.textContent =
    modeNames[
      exercise.mode
    ];

  const shape =
    document.createElement(
      'span'
    );

  shape.className =
    'npsExerciseDirection';

  shape.textContent =
    exercise.usesNpsBridge
      ? (
          '2/3 NPS ' +
          (
            exercise.bridgeDirection ===
              'up'
              ? '↗️'
              : '↙️'
          ) +
          ' + ' +
          exercise.shapeName +
          ' shape'
        )
      : (
          exercise.shapeName +
          ' shape'
        );

  primaryLine.appendChild(
    mode
  );

  primaryLine.appendChild(
    shape
  );

  answerDisplay.appendChild(
    primaryLine
  );
}


/* =========================================================
   SHAPE AROUND INTERVAL
   ========================================================= */

function shuffleList(list) {
  const copy =
    [...list];

  for (
    let index =
      copy.length - 1;
    index > 0;
    index--
  ) {
    const swapIndex =
      Math.floor(
        Math.random() *
        (index + 1)
      );

    [
      copy[index],
      copy[swapIndex]
    ] = [
      copy[swapIndex],
      copy[index]
    ];
  }

  return copy;
}


function getShapeCellDistanceSquared(
  startItem,
  candidateItem
) {
  /*
    Logical fretboard distance, independent of rendering.

    Each fret = 1 unit.
    Each string = 1 unit.

    Squared Euclidean distance is enough for comparison:
      sqrt(a) < sqrt(b) exactly when a < b.

    Examples:
      4 frets + 0 strings => 16
      3 frets + 1 string  => 10
      3 frets + 2 strings => 13
      0 frets + 5 strings => 25
  */

  const fretDelta =
    candidateItem.fret -
    startItem.fret;

  const stringDelta =
    candidateItem.stringIndex -
    startItem.stringIndex;

  return (
    fretDelta * fretDelta +
    stringDelta * stringDelta
  );
}


function getClosestShapeCell(
  allCells,
  startItem,
  interval
) {
  const candidates =
    allCells.filter(
      item =>
        item.element.dataset.interval ===
        interval
    );

  if (
    candidates.length === 0
  ) {
    return null;
  }

  let bestDistance =
    Infinity;

  let closest = [];

  candidates.forEach(
    candidate => {

      const distance =
        getShapeCellDistanceSquared(
          startItem,
          candidate
        );

      if (
        distance <
        bestDistance - 0.01
      ) {
        bestDistance =
          distance;

        closest =
          [candidate];

        return;
      }

      if (
        Math.abs(
          distance -
          bestDistance
        ) <= 0.01
      ) {
        closest.push(
          candidate
        );
      }
    }
  );

  return closest;
}


function createShapeExercise(
  allCells,
  selectedIntervals,
  scaleName
) {
  if (
    selectedIntervals.length === 0
  ) {
    return null;
  }

  const startInterval =
    randomItem(
      selectedIntervals
    );

  const startCandidates =
    allCells.filter(
      item =>
        item.element.dataset.interval ===
          startInterval &&
        item.fret >= 0 &&
        item.fret <= 12
    );

  if (
    startCandidates.length === 0
  ) {
    return null;
  }

  const startItem =
    randomItem(
      startCandidates
    );

  const startCellKey =
    makeCellKey(
      startItem.stringIndex,
      startItem.fret
    );

  const allScaleIntervals =
    scales[
      scaleName
    ].map(
      ([
        semitones,
        intervalName
      ]) =>
        intervalName
    );

  const remainingIntervals =
    allScaleIntervals.filter(
      interval =>
        interval !==
        startInterval
    );

  const targetCellKeysByInterval =
    new Map();

  const requiredCellKeys =
    new Set([
      startCellKey
    ]);

  for (
    const interval of
    remainingIntervals
  ) {
    const closestCells =
      getClosestShapeCell(
        allCells,
        startItem,
        interval
      );

    if (
      !closestCells ||
      closestCells.length === 0
    ) {
      continue;
    }

    const keys =
      new Set(
        closestCells.map(
          closest =>
            makeCellKey(
              closest.stringIndex,
              closest.fret
            )
        )
      );

    targetCellKeysByInterval.set(
      interval,
      keys
    );

    keys.forEach(
      key =>
        requiredCellKeys.add(
          key
        )
    );
  }

  const order =
    document
      .getElementById(
        'orderSelect'
      )
      .value;

  const promptQueue =
    order === 'random'
      ? shuffleList(
          remainingIntervals.filter(
            interval =>
              targetCellKeysByInterval
                .has(interval)
          )
        )
      : remainingIntervals.filter(
          interval =>
            targetCellKeysByInterval
              .has(interval)
        );

  return {
    startInterval,

    startCellKey,

    startStringIndex:
      startItem.stringIndex,

    startStringName:
      midiToScientificPitch(
        currentTuning[
          startItem.stringIndex
        ]
      ),

    requiredCellKeys,

    targetCellKeysByInterval,

    promptQueue,

    currentPromptInterval:
      null,

    currentPromptCellKeys:
      new Set(),

    currentPromptInitialCount:
      0,

    phase:
      'start'
  };
}


function displayShapeQuestion() {
  const answerDisplay =
    document.getElementById(
      'answerNote'
    );

  const exercise =
    currentShapeExercise;

  if (!exercise) {
    answerDisplay.textContent =
      'Done!';

    return;
  }

  answerDisplay.innerHTML = '';

  if (
    exercise.phase ===
    'start'
  ) {
    answerDisplay.className =
      'npsExerciseCard';

    const startLabel =
      document.createElement(
        'div'
      );

    startLabel.className =
      'npsExercisePrimary';

    startLabel.textContent =
      'Start';

    answerDisplay.appendChild(
      startLabel
    );

    return;
  }

  answerDisplay.className =
    'intervalQuizPrompt';

  answerDisplay.appendChild(
    document.createTextNode(
      'Select '
    )
  );

  const interval =
    document.createElement(
      'span'
    );

  const count =
    exercise
      .currentPromptCellKeys
      .size;

  interval.textContent =
    exercise.currentPromptInterval +
    (
      exercise
        .currentPromptInitialCount >
        1
        ? (
            ' (' +
            count +
            ' left)'
          )
        : ''
    );

  answerDisplay.appendChild(
    interval
  );
}


function advanceShapeExercise() {
  const exercise =
    currentShapeExercise;

  if (!exercise) {
    return;
  }

  const nextInterval =
    exercise.promptQueue.shift();

  if (!nextInterval) {
    scheduleQuizTransition(
      completeExerciseAndContinue
    );

    return;
  }

  exercise.phase =
    'remaining';

  exercise.currentPromptInterval =
    nextInterval;

  exercise.currentPromptCellKeys =
    new Set(
      exercise
        .targetCellKeysByInterval
        .get(
          nextInterval
        ) || []
    );

  exercise.currentPromptInitialCount =
    exercise
      .currentPromptCellKeys
      .size;

  displayShapeQuestion();
}


function completeExerciseAndContinue() {
  if (
    isDailyPracticeSelected() &&
    dailyPracticeState?.phase ===
      'pairs'
  ) {
    completeDailyPair();
    return;
  }

  buildTrainer();
}


/* =========================================================
   BUILD TRAINER
   ========================================================= */

function buildTrainer() {
  cancelQuizTransition();

  if (
    isDailyPracticeSelected() &&
    dailyPracticeState?.phase ===
      'complete'
  ) {
    document
      .getElementById(
        'chartDiv'
      )
      .innerHTML = '';

    document
      .getElementById(
        'answerNote'
      )
      .textContent =
        'Daily practice complete!';

    updateDailyPracticeStatus();
    return;
  }

  const lessonType =
    getLessonType();

  const lessonDefinition =
    getLessonDefinition(
      lessonType
    );

  const baseRoot =
    Number(
      document
        .getElementById(
          'rootSelect'
        )
        .value
    );

  const baseScaleName =
    document
      .getElementById(
        'scaleSelect'
      )
      .value;

  const exerciseKeyContext =
    getDailyExerciseKeyContext(
      baseRoot,
      baseScaleName
    );

  const root =
    exerciseKeyContext.root;

  const scaleName =
    exerciseKeyContext.scaleName;

  const tuning =
    getTuning();

  const selectedIntervals =
    (
      isDailyPracticeSelected() &&
      dailyPracticeState?.phase ===
        'pairs' &&
      lessonType ===
        'shape'
    )
      ? scales[
          scaleName
        ].map(
          ([
            semitones,
            intervalName
          ]) =>
            intervalName
        )
      : getSelectedIntervals();

  currentAnswer = null;
  currentNpsExercise = null;
  currentRrPentExercise = null;
  currentShapeExercise = null;
  currentCagedExercise = null;
  showAll = false;

  document
    .getElementById(
      'showAllButton'
    )
    .innerText =
      'Show Answer';

  const chartDiv =
    document.getElementById(
      'chartDiv'
    );

  chartDiv.innerHTML = '';

  const availableTargets =
    new Map();

  const allCells = [];

  const maxFret =
    lessonDefinition.maxFret ??
    12;

  const stringTopStart = 7;
  const stringTopEnd = 93;

  function getStringTopPercent(
    displayIndex
  ) {
    if (
      tuning.length <= 1
    ) {
      return 50;
    }

    return (
      stringTopStart +
      displayIndex *
        (
          stringTopEnd -
          stringTopStart
        ) /
        (
          tuning.length -
          1
        )
    );
  }

  const quizTuningControl =
    document.getElementById(
      'quizTuningControl'
    );

  if (quizTuningControl) {
    quizTuningControl.innerHTML = '';
    quizTuningControl.appendChild(
      createTuningSettings()
    );
  }

  const stage =
    document.createElement('div');

  stage.className =
    'fretboardStage';

  const hasStartCue =
    Boolean(
      lessonDefinition.hasStartCue
    );

  stage.classList.toggle(
    'hasStartCue',
    hasStartCue
  );

  document
    .querySelector(
      '.trainerShell'
    )
    ?.classList.toggle(
      'hasStartCue',
      hasStartCue
    );

  /*
    The fretboard is structurally split into independent
    columns instead of positioning UI with negative offsets:

      start cue | open strings | playable neck
  */
  const startCueLayer =
    document.createElement('div');

  startCueLayer.className =
    'fretboardStartCueLayer';

  const openStringLayer =
    document.createElement('div');

  openStringLayer.className =
    'fretboardOpenStrings';

  const fretboard =
    document.createElement('div');

  fretboard.className =
    'physicalFretboard';

  if (
    maxFret >= 20
  ) {
    fretboard.classList.add(
      'compact'
    );

    stage.classList.add(
      'compact'
    );
  }

  fretboard.style.setProperty(
    '--fret-count',
    maxFret
  );

  stage.append(
    startCueLayer,
    openStringLayer,
    fretboard
  );

  chartDiv.appendChild(
    stage
  );

  observeFretboardNoteSizing(
    stage,
    fretboard,
    tuning.length,
    maxFret,
    stringTopStart,
    stringTopEnd
  );


  function configureNoteCell(
    cell,
    absolutePitch,
    stringIndex,
    fret,
    isOpenString
  ) {
    const pitchClass =
      midiToPitchClass(
        absolutePitch
      );

    const octave =
      midiToOctave(
        absolutePitch
      );

    const noteName =
      midiToNoteName(
        absolutePitch
      );

    const interval =
      getIntervalForPitch(
        pitchClass,
        root,
        scaleName
      );

    const target =
      makeTarget(
        interval,
        octave
      );

    cell.classList.add(
      'noteCell'
    );

    cell.dataset.string =
      stringIndex + 1;

    cell.dataset.stringIndex =
      stringIndex;

    cell.dataset.fret =
      fret;

    cell.dataset.interval =
      interval || '';

    cell.dataset.displayInterval =
      interval || '';

    cell.dataset.octave =
      octave;

    cell.dataset.target =
      target;

    cell.dataset.openString =
      isOpenString
        ? 'true'
        : 'false';

    cell.dataset.noteName =
      noteName;

    cell.dataset.absolutePitch =
      absolutePitch;

    cell.dataset.scientificPitch =
      midiToScientificPitch(
        absolutePitch
      );

    cell.setAttribute(
      'role',
      'button'
    );

    cell.setAttribute(
      'tabindex',
      '0'
    );

    cell.setAttribute(
      'aria-label',
      'String ' +
        (stringIndex + 1) +
        ', fret ' +
        fret +
        ', ' +
        midiToScientificPitch(
          absolutePitch
        )
    );

    allCells.push({
      element: cell,
      absolutePitch,
      stringIndex,
      fret,
      isOpenString
    });


    if (
      lessonType === 'intervals' &&
      selectedIntervals.includes(
        interval
      )
    ) {
      if (
        !availableTargets.has(
          target
        )
      ) {
        availableTargets.set(
          target,
          {
            target,
            interval,
            octave
          }
        );
      }
    }
  }


  /* =======================================================
     FRETBOARD STRUCTURE
     ======================================================= */

  const nut =
    document.createElement('div');

  nut.className =
    'fretboardNut';

  fretboard.appendChild(
    nut
  );


  for (
    let fret = 1;
    fret <= maxFret;
    fret++
  ) {
    const fretLine =
      document.createElement('div');

    fretLine.className =
      'fretboardFret';

    fretLine.style.left =
      (
        fret /
        maxFret *
        100
      ) + '%';

    fretboard.appendChild(
      fretLine
    );
  }


  function addPositionDot(
    fret,
    topPercent,
    doubleDot = false
  ) {
    if (
      fret > maxFret
    ) {
      return;
    }

    const dot =
      document.createElement('div');

    dot.className =
      doubleDot
        ? 'fretboardPositionDot doubleDot'
        : 'fretboardPositionDot';

    dot.style.left =
      (
        (
          fret - 0.5
        ) /
        maxFret *
        100
      ) + '%';

    dot.style.top =
      topPercent + '%';

    fretboard.appendChild(
      dot
    );
  }


  [
    3,
    5,
    7,
    9,
    15,
    17,
    19,
    21
  ].forEach(
    fret =>
      addPositionDot(
        fret,
        50
      )
  );


  [
    12,
    24
  ].forEach(
    fret => {
      addPositionDot(
        fret,
        (
          getStringTopPercent(2) +
          getStringTopPercent(3)
        ) / 2,
        true
      );

      addPositionDot(
        fret,
        (
          getStringTopPercent(4) +
          getStringTopPercent(5)
        ) / 2,
        true
      );
    }
  );


  /*
    Visual order is conventional guitar orientation:
    highest string at the top, lowest string at the bottom.

    Internal stringIndex remains unchanged:
    0 = physical String 1 / lowest.
  */

  for (
    let displayIndex = 0;
    displayIndex <
      tuning.length;
    displayIndex++
  ) {
    const stringIndex =
      tuning.length -
      1 -
      displayIndex;

    const openPitch =
      tuning[
        stringIndex
      ];

    const topPercent =
      getStringTopPercent(
        displayIndex
      );


    const stringLine =
      document.createElement('div');

    stringLine.className =
      'fretboardString';

    stringLine.style.top =
      topPercent + '%';

    stringLine.style.height =
      (
        1 +
        displayIndex *
          0.42
      ) + 'px';

    fretboard.appendChild(
      stringLine
    );


    /* OPEN STRING */

    const openCell =
      document.createElement('div');

    openCell.className =
      'fretboardNote openStringNote';

    openCell.style.top =
      topPercent + '%';

    configureNoteCell(
      openCell,
      openPitch,
      stringIndex,
      0,
      true
    );

    openStringLayer.appendChild(
      openCell
    );

    restoreCellDisplay(
      openCell
    );


    /* FRETTED NOTES */

    for (
      let fret = 1;
      fret <= maxFret;
      fret++
    ) {
      const cell =
        document.createElement('div');

      cell.className =
        'fretboardNote';

      cell.style.left =
        (
          (
            fret - 0.5
          ) /
          maxFret *
          100
        ) + '%';

      cell.style.top =
        topPercent + '%';

      const absolutePitch =
        openPitch +
        fret;

      configureNoteCell(
        cell,
        absolutePitch,
        stringIndex,
        fret,
        false
      );

      fretboard.appendChild(
        cell
      );

      restoreCellDisplay(
        cell
      );
    }
  }


  /* =======================================================
     SHAPE AROUND INTERVAL
     ======================================================= */

  if (
    lessonType === 'shape'
  ) {
    currentShapeExercise =
      createShapeExercise(
        allCells,
        selectedIntervals,
        scaleName
      );

    if (
      !currentShapeExercise
    ) {
      document
        .getElementById(
          'answerNote'
        )
        .textContent =
          'No valid shape for these settings.';

      return;
    }

    displayShapeQuestion();

    startCueLayer.appendChild(
      createNpsStartMarker(
        currentShapeExercise,
        tuning.length
      )
    );

    return;
  }


  /* =======================================================
     CAGED PENTATONIC
     ======================================================= */

  if (
    lessonType === 'caged'
  ) {
    currentCagedExercise =
      createCagedExercise(
        allCells,
        root,
        scaleName
      );

    if (
      !currentCagedExercise
    ) {
      document
        .getElementById(
          'answerNote'
        )
        .textContent =
          'No valid CAGED pentatonic shape for these settings.';

      return;
    }


    /*
      Translate all visible intervals relative to the
      randomly selected modal root, exactly like NPS.
    */

    allCells.forEach(
      item => {
        const pitchClass =
          midiToPitchClass(
            item.absolutePitch
          );

        const translatedInterval =
          getNpsIntervalForPitch(
            pitchClass,
            currentCagedExercise
              .modeRoot,
            currentCagedExercise
              .mode
          );

        item.element.dataset
          .displayInterval =
            translatedInterval || '';

        const key =
          makeCellKey(
            item.stringIndex,
            item.fret
          );

        if (
          currentCagedExercise
            .usesNpsBridge &&
          currentCagedExercise
            .bridgeCellKeys
            .has(key) &&
          key !==
            currentCagedExercise
              .connectionCellKey
        ) {
          item.element.classList.add(
            'cagedNpsBridge'
          );
        }

        hideCell(
          item.element
        );
      }
    );


    displayCagedQuestion();

    startCueLayer.appendChild(
      createNpsStartMarker(
        currentCagedExercise,
        tuning.length,
        currentCagedExercise
          .usesNpsBridge
          ? 'cagedNpsStartGuide'
          : ''
      )
    );

    return;
  }


  /* =======================================================
     INTERVAL LESSON
     ======================================================= */

  if (
    lessonType === 'intervals'
  ) {
    questions = [];

    selectedIntervals.forEach(
      interval => {

        const matching =
          [
            ...availableTargets.values()
          ]
            .filter(
              item =>
                item.interval ===
                interval
            )
            .sort(
              (a, b) =>
                a.octave -
                b.octave
            );

        matching.forEach(
          item =>
            questions.push(
              item.target
            )
        );
      }
    );

    generateIntervalAnswer();

    return;
  }


  /* =======================================================
     R-R PENTATONIC + COLOR NOTES
     ======================================================= */

  if (
    lessonType === 'rrPent'
  ) {
    const exercises =
      getRrPentExerciseCandidates(
        allCells,
        root,
        scaleName
      );

    if (
      exercises.length === 0
    ) {
      document
        .getElementById(
          'answerNote'
        )
        .textContent =
          'No valid R-R pentatonic starting positions for these settings.';

      return;
    }

    currentRrPentExercise =
      randomItem(
        exercises
      );

    allCells.forEach(
      item => {
        const pathItem =
          currentRrPentExercise
            .fullPath
            .find(
              pathCell =>
                pathCell.stringIndex ===
                  item.stringIndex &&
                pathCell.fret ===
                  item.fret
            );

        const translatedInterval =
          pathItem?.rrInterval ||
          getNpsIntervalForPitch(
            midiToPitchClass(
              item.absolutePitch
            ),
            currentRrPentExercise
              .modeRoot,
            currentRrPentExercise
              .mode
          );

        item.element.dataset
          .displayInterval =
            translatedInterval || '';

        hideCell(
          item.element
        );
      }
    );

    displayRrPentQuestion();

    startCueLayer.appendChild(
      createNpsStartMarker(
        currentRrPentExercise,
        tuning.length
      )
    );

    return;
  }


  /* =======================================================
     NPS LESSON
     ======================================================= */

  const exercises =
    getNpsExerciseCandidates(
      allCells,
      root,
      scaleName
    );

  if (
    exercises.length === 0
  ) {
    document
      .getElementById(
        'answerNote'
      )
      .textContent =
        'No valid 2/3 NPS starting positions for these settings.';

    return;
  }

  currentNpsExercise =
    randomItem(exercises);


  /*
    Translate intervals relative to the
    randomly selected modal root.
  */

  allCells.forEach(
    item => {

      const pitchClass =
        midiToPitchClass(
          item.absolutePitch
        );

      const translatedInterval =
        getNpsIntervalForPitch(
          pitchClass,
          currentNpsExercise.modeRoot,
          currentNpsExercise.mode
        );

      item.element.dataset
        .displayInterval =
          translatedInterval || '';

      hideCell(
        item.element
      );
    }
  );

  displayNpsQuestion();

  startCueLayer.appendChild(
    createNpsStartMarker(
      currentNpsExercise,
      tuning.length
    )
  );
}

/* =========================================================
   INTERVAL QUESTION
   ========================================================= */

function generateIntervalAnswer() {
  const answerDisplay =
    document.getElementById(
      'answerNote'
    );

  if (
    questions.length === 0
  ) {
    currentAnswer = null;

    answerDisplay.innerText =
      'Done!';

    return;
  }

  const order =
    document
      .getElementById(
        'orderSelect'
      )
      .value;

  if (
    order === 'ordered'
  ) {
    currentAnswer =
      questions[0];
  } else {
    currentAnswer =
      randomItem(questions);
  }

  const {
    interval,
    octave
  } =
    parseTarget(
      currentAnswer
    );

  answerDisplay.innerHTML = '';
  answerDisplay.className = 'intervalQuizPrompt';

  answerDisplay.appendChild(
    document.createTextNode(
      'Select all '
    )
  );

  const targetDisplay =
    document.createElement(
      'span'
    );

  setIntervalOctaveDisplay(
    targetDisplay,
    interval,
    octave
  );

  answerDisplay.appendChild(
    targetDisplay
  );

  answerDisplay.appendChild(
    document.createTextNode(
      ' notes'
    )
  );
}


/* =========================================================
   R-R PENTATONIC QUESTION
   ========================================================= */

function displayRrPentQuestion() {
  const answerDisplay =
    document.getElementById(
      'answerNote'
    );

  const exercise =
    currentRrPentExercise;

  if (!exercise) {
    answerDisplay.textContent =
      'Done!';
    return;
  }

  answerDisplay.innerHTML = '';
  answerDisplay.className =
    'npsExerciseCard';

  const primaryLine =
    document.createElement(
      'div'
    );

  primaryLine.className =
    'npsExercisePrimary';

  const mode =
    document.createElement(
      'span'
    );

  mode.className =
    'npsExerciseMode';

  mode.textContent =
    modeNames[
      exercise.mode
    ];

  const direction =
    document.createElement(
      'span'
    );

  direction.className =
    'npsExerciseDirection';

  direction.textContent =
    exercise.direction === 'up'
      ? '⬆️'
      : exercise.direction === 'down'
        ? '⬇️'
        : '↕️';

  primaryLine.appendChild(
    mode
  );

  primaryLine.appendChild(
    direction
  );

  answerDisplay.appendChild(
    primaryLine
  );
}


/* =========================================================
   NPS QUESTION
   ========================================================= */

function displayNpsQuestion() {
  const answerDisplay =
    document.getElementById(
      'answerNote'
    );

  const exercise =
    currentNpsExercise;

  if (!exercise) {
    answerDisplay.textContent =
      'Done!';

    return;
  }

  answerDisplay.innerHTML = '';
  answerDisplay.className = 'npsExerciseCard';

  const primaryLine =
    document.createElement('div');

  primaryLine.className =
    'npsExercisePrimary';

  const mode =
    document.createElement('span');

  mode.className =
    'npsExerciseMode';

  mode.textContent =
    modeNames[exercise.mode];

  const direction =
    document.createElement('span');

  direction.className =
    'npsExerciseDirection';

  direction.textContent =
    exercise.direction === 'up'
      ? '⬆️'
      : exercise.direction === 'down'
        ? '⬇️'
        : '↕️';

  primaryLine.appendChild(mode);
  primaryLine.appendChild(direction);

  answerDisplay.appendChild(primaryLine);
}


/* =========================================================
   NPS START MARKER
   ========================================================= */

function createNpsStartMarker(
  exercise,
  stringCount,
  guideClassName = ''
) {
  const guide =
    document.createElement('div');

  guide.className =
    'npsStartGuide' +
    (
      guideClassName
        ? ' ' + guideClassName
        : ''
    );

  const displayIndex =
    stringCount -
    1 -
    exercise.startStringIndex;

  const topPercent =
    stringCount <= 1
      ? 50
      : (
          7 +
          displayIndex *
            (93 - 7) /
            (stringCount - 1)
        );

  guide.style.top =
    topPercent + '%';

  const interval =
    document.createElement('div');

  interval.className =
    'npsStartInterval';

  interval.textContent =
    exercise.startInterval;

  interval.setAttribute(
    'aria-label',
    'Start on ' +
      exercise.startStringName +
      ', interval ' +
      exercise.startInterval
  );

  applyIntervalStyle(
    interval,
    exercise.startInterval
  );

  const arrow =
    document.createElement('div');

  arrow.className =
    'npsStartArrow';

  arrow.textContent = '→';

  guide.appendChild(
    interval
  );

  guide.appendChild(
    arrow
  );

  return guide;
}

/* =========================================================
   INTERVAL COMPLETE
   ========================================================= */

function getIntervalDebugState() {
  const prompt = document.getElementById('answerNote')?.textContent?.trim() || '—';

  if (getLessonType() !== 'intervals' || !currentAnswer) {
    return { prompt, played: '—', remaining: '—' };
  }

  const matchingCells = [...document.querySelectorAll('.noteCell')]
    .filter(cell => cell.dataset.target === currentAnswer);

  const formatCell = cell =>
    `S${cell.dataset.string} F${cell.dataset.fret}`;

  const played = matchingCells
    .filter(cell => cell.classList.contains('correct'))
    .map(formatCell);

  const remaining = matchingCells
    .filter(cell => !cell.classList.contains('correct'))
    .map(formatCell);

  return {
    prompt,
    played: played.length ? played.join(', ') : '—',
    remaining: remaining.length ? remaining.join(', ') : '—'
  };
}

window.getGuitarTrainerDebugState = getIntervalDebugState;


/* =========================================================
   LIVE-GUITAR ANSWER HINTS

   The microphone/string classifier may use the CURRENT quiz
   state as a soft prior when the detected pitch matches one
   or more remaining answer positions.

   Important:
     - only REMAINING answers are returned
     - already-correct positions are excluded
     - multiple valid positions for the same MIDI are all kept
     - this does not answer the quiz itself; it only tells the
       audio layer which physical-string interpretations are
       currently plausible answers
   ========================================================= */

function getCurrentAudioAnswerCellKeys() {
  const lessonType =
    getLessonType();

  if (
    lessonType === 'intervals'
  ) {
    if (!currentAnswer) {
      return new Set();
    }

    return new Set(
      [
        ...document.querySelectorAll(
          '.noteCell'
        )
      ]
        .filter(
          cell =>
            cell.dataset.target ===
              currentAnswer &&
            !cell.classList.contains(
              'correct'
            )
        )
        .map(
          cell =>
            makeCellKey(
              Number(
                cell.dataset.stringIndex
              ),
              Number(
                cell.dataset.fret
              )
            )
        )
    );
  }

  if (
    lessonType === 'shape' &&
    currentShapeExercise
  ) {
    if (
      currentShapeExercise.phase ===
      'start'
    ) {
      return new Set(
        [
          currentShapeExercise
            .startCellKey
        ]
      );
    }

    return new Set(
      currentShapeExercise
        .currentPromptCellKeys
    );
  }

  if (
    lessonType === 'caged' &&
    currentCagedExercise
  ) {
    return new Set(
      currentCagedExercise
        .remainingCellKeys
    );
  }

  if (
    lessonType === 'rrPent' &&
    currentRrPentExercise
  ) {
    return new Set(
      currentRrPentExercise
        .remainingCellKeys
    );
  }

  if (
    lessonType === 'nps' &&
    currentNpsExercise
  ) {
    return new Set(
      currentNpsExercise
        .remainingCellKeys
    );
  }

  return new Set();
}

window.getGuitarTrainerAudioHints =
  midi => {
    const midiNumber =
      Number(midi);

    if (
      !Number.isInteger(
        midiNumber
      )
    ) {
      return {
        hasMatchingAnswer:
          false,

        answerStrings:
          [],

        answerPositions:
          []
      };
    }

    const remainingKeys =
      getCurrentAudioAnswerCellKeys();

    const matchingCells =
      [
        ...document.querySelectorAll(
          '.noteCell'
        )
      ].filter(
        cell => {
          const key =
            makeCellKey(
              Number(
                cell.dataset.stringIndex
              ),
              Number(
                cell.dataset.fret
              )
            );

          return (
            remainingKeys.has(key) &&
            Number(
              cell.dataset.absolutePitch
            ) === midiNumber
          );
        }
      );

    const answerPositions =
      matchingCells.map(
        cell => ({
          string:
            Number(
              cell.dataset.string
            ),

          fret:
            Number(
              cell.dataset.fret
            ),

          interval:
            cell.dataset
              .displayInterval ||
            cell.dataset.interval ||
            '',

          octave:
            Number(
              cell.dataset.octave
            )
        })
      );

    const answerStrings =
      [
        ...new Set(
          answerPositions.map(
            position =>
              position.string
          )
        )
      ];

    return {
      hasMatchingAnswer:
        answerPositions.length > 0,

      answerStrings,

      answerPositions
    };
  };


function intervalTargetComplete() {
  const matchingCells = [
    ...document.querySelectorAll(
      '.noteCell'
    )
  ].filter(
    cell =>
      cell.dataset.target ===
      currentAnswer
  );

  return (
    matchingCells.length > 0 &&
    matchingCells.every(
      cell =>
        cell.classList.contains(
          'correct'
        )
    )
  );
}


/* =========================================================
   WRONG ANSWER
   ========================================================= */

function temporarilyShowWrong(cell) {
  const interval =
    ['nps', 'rrPent', 'caged'].includes(
      getLessonType()
    )
      ? cell.dataset.displayInterval
      : cell.dataset.interval;

  if (!interval) {
    return;
  }

  if (
    ['nps', 'rrPent', 'shape', 'caged'].includes(
      getLessonType()
    )
  ) {
    cell.textContent =
      interval;
  } else {
    setIntervalOctaveDisplay(
      cell,
      interval,
      Number(
        cell.dataset.octave
      )
    );
  }

  clearCellStyle(cell);

  cell.classList.remove(
    'unknownInterval'
  );

  cell.classList.add(
    'wrong'
  );

  setTimeout(
    () => {
      cell.classList.remove(
        'wrong'
      );

      restoreCellDisplay(
        cell
      );
    },
    800
  );
}


/* =========================================================
   CLICK HANDLER
   ========================================================= */

document
  .getElementById('chartDiv')
  .addEventListener(
    'click',
    event => {

      const cell =
        event.target.closest(
          '.noteCell'
        );

      if (!cell) {
        return;
      }

      if (showAll) {
        return;
      }

      if (isQuizTransitioning) {
        return;
      }

      if (!event.detail?.guitarAudio) {
        window.dispatchEvent(new CustomEvent('guitar-manual-fret-click', {
          detail: {
            midi: Number(cell.dataset.absolutePitch),
            string: Number(cell.dataset.string),
            fret: Number(cell.dataset.fret),
            note: cell.dataset.scientificPitch || cell.dataset.noteName || '—'
          }
        }));
      }


      /* INTERVAL LESSON */

      if (
        getLessonType() ===
        'intervals'
      ) {
        if (!currentAnswer) {
          return;
        }

        if (
          cell.classList.contains(
            'correct'
          )
        ) {
          return;
        }

        const correct =
          cell.dataset.target ===
          currentAnswer;

        if (correct) {
          cell.classList.remove(
            'wrong'
          );

          cell.classList.add(
            'correct'
          );

          revealCell(cell);

          if (
            intervalTargetComplete()
          ) {
            const questionIndex =
              questions.indexOf(
                currentAnswer
              );

            if (
              questionIndex !== -1
            ) {
              questions.splice(
                questionIndex,
                1
              );
            }

            scheduleQuizTransition(
              () => {
                document
                  .querySelectorAll(
                    '.noteCell.correct'
                  )
                  .forEach(
                    correctCell => {
                      correctCell
                        .classList
                        .remove(
                          'correct'
                        );

                      restoreCellDisplay(
                        correctCell
                      );
                    }
                  );

                if (
                  questions.length === 0 &&
                  finishDailyIntervals()
                ) {
                  return;
                }

                generateIntervalAnswer();
              }
            );
          }

        } else {
          temporarilyShowWrong(
            cell
          );
        }

        return;
      }


      /* SHAPE AROUND INTERVAL */

      if (
        getLessonType() ===
        'shape'
      ) {
        const exercise =
          currentShapeExercise;

        if (!exercise) {
          return;
        }

        if (
          cell.classList.contains(
            'correct'
          )
        ) {
          return;
        }

        const cellKey =
          makeCellKey(
            Number(
              cell.dataset.stringIndex
            ),
            Number(
              cell.dataset.fret
            )
          );

        const correct =
          exercise.phase ===
            'start'
            ? (
                cellKey ===
                exercise
                  .startCellKey
              )
            : exercise
                .currentPromptCellKeys
                .has(
                  cellKey
                );

        if (!correct) {
          temporarilyShowWrong(
            cell
          );

          return;
        }

        cell.classList.remove(
          'wrong'
        );

        cell.classList.add(
          'correct'
        );

        revealCell(
          cell
        );

        if (
          exercise.phase ===
          'start'
        ) {
          advanceShapeExercise();

          return;
        }

        exercise
          .currentPromptCellKeys
          .delete(
            cellKey
          );

        if (
          exercise
            .currentPromptCellKeys
            .size === 0
        ) {
          advanceShapeExercise();
        } else {
          displayShapeQuestion();
        }

        return;
      }


      /* CAGED PENTATONIC LESSON */

      if (
        getLessonType() ===
        'caged'
      ) {
        const exercise =
          currentCagedExercise;

        if (!exercise) {
          return;
        }

        if (
          cell.classList.contains(
            'correct'
          )
        ) {
          return;
        }

        const cellKey =
          makeCellKey(
            Number(
              cell.dataset.stringIndex
            ),
            Number(
              cell.dataset.fret
            )
          );


        if (
          !exercise
            .remainingCellKeys
            .has(
              cellKey
            )
        ) {
          temporarilyShowWrong(
            cell
          );

          return;
        }


        cell.classList.remove(
          'wrong'
        );

        cell.classList.add(
          'correct'
        );

        revealCell(
          cell
        );

        exercise
          .remainingCellKeys
          .delete(
            cellKey
          );


        if (
          exercise
            .remainingCellKeys
            .size === 0
        ) {
           scheduleQuizTransition(
            completeExerciseAndContinue
          );
        }

        return;
      }


      /* R-R PENTATONIC + COLOR NOTES */

      if (
        getLessonType() ===
        'rrPent'
      ) {
        const exercise =
          currentRrPentExercise;

        if (!exercise) {
          return;
        }

        if (
          cell.classList.contains(
            'correct'
          )
        ) {
          return;
        }

        const cellKey =
          makeCellKey(
            Number(
              cell.dataset.stringIndex
            ),
            Number(
              cell.dataset.fret
            )
          );

        if (
          !exercise
            .remainingCellKeys
            .has(cellKey)
        ) {
          temporarilyShowWrong(
            cell
          );
          return;
        }

        cell.classList.remove(
          'wrong'
        );

        cell.classList.add(
          'correct'
        );

        if (
          exercise.direction ===
            'upDown' &&
          cellKey ===
            exercise.startCellKey
        ) {
          cell.classList.add(
            'npsAnchor'
          );
        }

        revealCell(
          cell
        );

        exercise
          .remainingCellKeys
          .delete(cellKey);

        if (
          exercise
            .remainingCellKeys
            .size === 0
        ) {
           scheduleQuizTransition(
            completeExerciseAndContinue
          );
        }

        return;
      }


      /* 2/3 NPS LESSON */

      const exercise =
        currentNpsExercise;

      if (!exercise) {
        return;
      }

      if (
        cell.classList.contains(
          'correct'
        )
      ) {
        return;
      }

      const cellKey =
        makeCellKey(
          Number(
            cell.dataset.stringIndex
          ),
          Number(
            cell.dataset.fret
          )
        );


      /*
        ONLY cells in the actual generated
        directional shape are valid.
      */

      if (
        !exercise
          .remainingCellKeys
          .has(cellKey)
      ) {
        temporarilyShowWrong(
          cell
        );

        return;
      }


      cell.classList.remove(
        'wrong'
      );

      cell.classList.add(
        'correct'
      );


      if (
        exercise.direction ===
          'upDown' &&
        cellKey ===
          exercise.startCellKey
      ) {
        cell.classList.add(
          'npsAnchor'
        );
      }


      revealCell(cell);


      exercise
        .remainingCellKeys
        .delete(cellKey);


      if (
        exercise
          .remainingCellKeys
          .size === 0
      ) {
         scheduleQuizTransition(
            completeExerciseAndContinue
          );
      }
    }
  );


/* =========================================================
   SHOW ALL
   ========================================================= */

document
  .getElementById(
    'showAllButton'
  )
  .addEventListener(
    'click',
    () => {

      showAll =
        !showAll;

      document
        .getElementById(
          'showAllButton'
        )
        .innerText =
          showAll
            ? 'Hide Answer'
            : 'Show Answer';

      document
        .querySelectorAll(
          '.noteCell'
        )
        .forEach(
          cell => {
            restoreCellDisplay(
              cell
            );
          }
        );
    }
  );


/* =========================================================
   CONTROLS
   ========================================================= */

document
  .getElementById(
    'lessonTypeSelect'
  )
  .addEventListener(
    'change',
    () => {
      if (
        getSelectedLessonType() ===
        'daily'
      ) {
        initializeDailyPractice();
      } else {
        dailyPracticeState = null;
      }

      updateLessonControls();
      buildTrainer();
    }
  );

document
  .getElementById(
    'rootSelect'
  )
  .addEventListener(
    'change',
    buildTrainer
  );

document
  .getElementById(
    'scaleSelect'
  )
  .addEventListener(
    'change',
    () => {
      buildIntervalControls();
      buildTrainer();
    }
  );

document
  .getElementById(
    'orderSelect'
  )
  .addEventListener(
    'change',
    () => {
      if (
        ['intervals', 'shape'].includes(
          getLessonType()
        )
      ) {
        buildTrainer();
      }
    }
  );


/* =========================================================
   CLOSE POPOVERS
   ========================================================= */

document.addEventListener(
  'click',
  event => {

    document
      .querySelectorAll(
        '.tuningPopover.open'
      )
      .forEach(
        popover => {
          if (
            !popover.contains(
              event.target
            )
          ) {
            popover.classList.remove(
              'open'
            );
          }
        }
      );

    document
      .querySelectorAll(
        'details.multiSelect[open]'
      )
      .forEach(
        details => {
          if (
            !details.contains(
              event.target
            )
          ) {
            details.removeAttribute(
              'open'
            );
          }
        }
      );
  }
);


document
  .getElementById(
    'rrColorToggle'
  )
  .addEventListener(
    'change',
    () => {
      if (
        getLessonType() ===
        'rrPent'
      ) {
        buildTrainer();
      }
    }
  );


/* =========================================================
   START
   ========================================================= */

buildIntervalControls();
buildNpsModeControls();
buildStartDegreeControls();
buildDirectionControls();
buildCagedShapeControls();

updateLessonControls();
buildTrainer();

/* =========================================================
   NEXT BUTTON
   ========================================================= */

document
  .getElementById('nextButton')
  .addEventListener('click', () => {
    showAll = false;

    document
      .getElementById(
        'showAllButton'
      )
      .innerText =
        'Show Answer';

    if (
      isDailyPracticeSelected() &&
      dailyPracticeState
    ) {
      if (
        dailyPracticeState.phase ===
        'intervals'
      ) {
        if (
          currentAnswer
        ) {
          const questionIndex =
            questions.indexOf(
              currentAnswer
            );

          if (
            questionIndex !== -1
          ) {
            questions.splice(
              questionIndex,
              1
            );
          }
        }

        document
          .querySelectorAll(
            '.noteCell.correct'
          )
          .forEach(
            cell => {
              cell.classList.remove(
                'correct'
              );

              restoreCellDisplay(
                cell
              );
            }
          );

        if (
          questions.length === 0
        ) {
          finishDailyIntervals();
        } else {
          generateIntervalAnswer();
        }

        return;
      }

      if (
        dailyPracticeState.phase ===
        'pairs'
      ) {
        completeDailyPair();
        return;
      }

      return;
    }

    buildTrainer();
  });


/* =========================================================
   LIVE GUITAR -> QUIZ INPUT
   Audio detections become the exact same interaction as a
   physical fretboard click. No duplicate quiz-answer logic.
   ========================================================= */

let lastAudioCellKey = null;
let lastAudioCellAt = 0;
const AUDIO_REPEAT_LOCK_MS = 350;

function activateDetectedFret({ midi, string }) {
  const midiNumber = Number(midi);
  const stringNumber = Number(string);

  if (!Number.isInteger(midiNumber) || !Number.isInteger(stringNumber)) {
    return false;
  }

  const stringIndex = stringNumber - 1;
  const openMidi = currentTuning[stringIndex];

  if (!Number.isInteger(openMidi)) {
    return false;
  }

  const fret = midiNumber - openMidi;

  if (fret < 0 || fret > 24) {
    return false;
  }

  const cell = document.querySelector(
    `.noteCell[data-string-index="${stringIndex}"][data-fret="${fret}"]`
  );

  if (!cell) {
    return false;
  }

  const cellKey = makeCellKey(stringIndex, fret);
  const now = performance.now();

  // A sustained note produces many audio frames. Treat it as one fret press.
  if (
    cellKey === lastAudioCellKey &&
    now - lastAudioCellAt < AUDIO_REPEAT_LOCK_MS
  ) {
    return false;
  }

  lastAudioCellKey = cellKey;
  lastAudioCellAt = now;

  cell.dispatchEvent(new CustomEvent('click', {
    bubbles: true,
    detail: { guitarAudio: true }
  }));
  return true;
}

window.addEventListener('guitar-note-detected', event => {
  activateDetectedFret(event.detail || {});
});



setupLiveGuitarInput();

