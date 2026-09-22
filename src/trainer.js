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

// Visible single-selects share one component; hidden native selects remain state only.
buildUnifiedSingleSelect('lessonTypeDropdown', 'lessonTypeSelect');
buildUnifiedSingleSelect('rootDropdown', 'rootSelect', 'rootOptions');
buildUnifiedSingleSelect('scaleDropdown', 'scaleSelect', 'scaleOptions');
buildUnifiedSingleSelect('orderDropdown', 'orderSelect');

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

function getLessonType() {
  return document
    .getElementById('lessonTypeSelect')
    .value;
}

function getTuning() {
  return [...currentTuning];
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
        true;

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
    getLessonType() === 'intervals'
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
    getLessonType() === 'nps'
  ) {
    buildTrainer();
  }
}

function getSelectedNpsModes() {
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
    getLessonType() === 'nps'
  ) {
    buildTrainer();
  }
}

function getSelectedStartDegrees() {
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

  if (getLessonType() === 'nps') {
    buildTrainer();
  }
}

function getSelectedDirections() {
  return [...document.querySelectorAll('.directionCheckbox:checked')]
    .map(input => input.value);
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
  const nps =
    getLessonType() === 'nps';

  document
    .getElementById(
      'intervalLessonControls'
    )
    .hidden =
      nps;

  document
    .getElementById(
      'npsControls'
    )
    .hidden =
      !nps;

  document
    .getElementById(
      'orderControl'
    )
    .hidden =
      nps;
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
    getLessonType() === 'nps'
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

  applyIntervalStyle(
    cell,
    interval
  );
}

function hideCell(cell) {
  clearCellStyle(cell);

  if (
    cell.dataset.openString ===
    'true'
  ) {
    cell.innerText =
      cell.dataset.noteName;
  } else {
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
  }
}


/* =========================================================
   TUNING SETTINGS
   ========================================================= */

function createTuningSettings() {
  const wrapper = document.createElement('div');

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
   COLUMN WIDTHS
   ========================================================= */

function lockColumnWidths() {
  const table = document.querySelector('#chartDiv table');
  if (!table) return;

  const stringWidth = 32;
  const fretWidth = 32;

  const oldColgroup = table.querySelector('colgroup');
  if (oldColgroup) oldColgroup.remove();

  const colgroup = document.createElement('colgroup');

  for (let i = 0; i < 8; i++) {
    const col = document.createElement('col');
    col.style.width = `${stringWidth}px`;
    colgroup.appendChild(col);
  }

  const fretCol = document.createElement('col');
  fretCol.style.width = `${fretWidth}px`;
  colgroup.appendChild(fretCol);

  table.insertBefore(colgroup, table.firstChild);
  table.style.tableLayout = 'fixed';
  table.style.width = `${stringWidth * 8 + fretWidth}px`;
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
   BUILD TRAINER
   ========================================================= */

function buildTrainer() {
  const lessonType =
    getLessonType();

  const root =
    Number(
      document
        .getElementById(
          'rootSelect'
        )
        .value
    );

  const scaleName =
    document
      .getElementById(
        'scaleSelect'
      )
      .value;

  const tuning =
    getTuning();

  const selectedIntervals =
    getSelectedIntervals();

  currentAnswer = null;
  currentNpsExercise = null;
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

  const table =
    document.createElement(
      'table'
    );

  chartDiv.appendChild(table);

  const availableTargets =
    new Map();

  const allCells = [];


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


  /* OPEN STRINGS */

  const headerRow =
    document.createElement('tr');

  table.appendChild(
    headerRow
  );

  tuning.forEach(
    (
      openPitch,
      stringIndex
    ) => {

      const th =
        document.createElement('th');

      configureNoteCell(
        th,
        openPitch,
        stringIndex,
        0,
        true
      );

      headerRow.appendChild(th);

      restoreCellDisplay(th);
    }
  );


  /* SETTINGS */

  const settingsHeader =
    document.createElement('th');

  settingsHeader.classList.add(
    'settingsHeader'
  );

  settingsHeader.appendChild(
    createTuningSettings()
  );

  headerRow.appendChild(
    settingsHeader
  );


  /* FRETS */

  const maxFret =
    lessonType === 'nps'
      ? 24
      : 12;

  for (
    let fret = 1;
    fret <= maxFret;
    fret++
  ) {
    const row =
      document.createElement('tr');

    table.appendChild(row);

    tuning.forEach(
      (
        openPitch,
        stringIndex
      ) => {

        const cell =
          document.createElement('td');

        const absolutePitch =
          openPitch + fret;

        configureNoteCell(
          cell,
          absolutePitch,
          stringIndex,
          fret,
          false
        );

        row.appendChild(cell);

        restoreCellDisplay(cell);
      }
    );

    const fretCell =
      document.createElement('td');

    fretCell.innerText =
      fret;

    fretCell.classList.add(
      'fretNumber'
    );

    if (
      dotFrets.includes(fret)
    ) {
      fretCell.classList.add(
        'fretDot'
      );
    }

    row.appendChild(
      fretCell
    );
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

    lockColumnWidths();
    generateIntervalAnswer();

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

    lockColumnWidths();

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

  lockColumnWidths();
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

  const secondaryLine =
    document.createElement('div');

  secondaryLine.className =
    'npsExerciseSecondary';

  secondaryLine.appendChild(
    document.createTextNode('Start on ')
  );

  const stringName =
    document.createElement('strong');

  stringName.textContent =
    exercise.startStringName;

  secondaryLine.appendChild(stringName);

  secondaryLine.appendChild(
    document.createTextNode(' · ')
  );

  const interval =
    document.createElement('strong');

  interval.textContent =
    exercise.startInterval;

  secondaryLine.appendChild(interval);

  answerDisplay.appendChild(primaryLine);
  answerDisplay.appendChild(secondaryLine);
}

/* =========================================================
   INTERVAL COMPLETE
   ========================================================= */

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
    getLessonType() === 'nps'
      ? cell.dataset.displayInterval
      : cell.dataset.interval;

  if (!interval) {
    return;
  }

  if (
    getLessonType() === 'nps'
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

            generateIntervalAnswer();
          }

        } else {
          temporarilyShowWrong(
            cell
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
        buildTrainer();
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
            ? 'Hide All'
            : 'Show All';

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
        getLessonType() ===
        'intervals'
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


/* =========================================================
   START
   ========================================================= */

buildIntervalControls();
buildNpsModeControls();
buildStartDegreeControls();
buildDirectionControls();

updateLessonControls();
buildTrainer();

/* =========================================================
   NEXT BUTTON
   ========================================================= */

document
  .getElementById('nextButton')
  .addEventListener('click', () => {
    showAll = false;

    document.getElementById('showAllButton').innerText = 'Show All';

    buildTrainer();
  });


setupLiveGuitarInput();

