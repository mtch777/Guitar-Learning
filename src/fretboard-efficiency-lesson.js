// Controls and viewport decisions for the existing trainer/Song Player lesson.
// Sound, score timing and active contacts remain owned by Song Player.
export const EFFICIENCY_LESSON_ID = 'fretboardEfficiency';
export const EFFICIENCY_TUNING_LOW_TO_HIGH = [28, 35, 40, 45, 50, 55, 59, 64];
const BUILT_IN_FIXTURE_IDS = ['cfa029a2', 'da80eca9', 'c5a35486'];
const MAPPING_IDS = ['optimized', 'greedy', 'strumPick'];

export function efficiencySelectionFromSearch(search) {
  const params = new URLSearchParams(search);
  return {
    selected: params.get('lesson') === EFFICIENCY_LESSON_ID,
    fixtureId: BUILT_IN_FIXTURE_IDS.includes(params.get('riff'))
      ? params.get('riff') : BUILT_IN_FIXTURE_IDS[0],
    versionId: MAPPING_IDS.includes(params.get('mapping')) ? params.get('mapping') : 'optimized'
  };
}

export function efficiencySourceTick(nativeTick, sourceTicksPerBeat = 960) {
  // Song Player reports alphaTab's 960 PPQN clock; the optimizer preserves
  // the original MIDI resolution in each fixture's positions and note events.
  return Number(nativeTick) * Number(sourceTicksPerBeat) / 960;
}

export function efficiencyPositionAtTick(version, tick) {
  const positions = version?.positions || [];
  let low = 0;
  let high = positions.length - 1;
  let result = null;
  while (low <= high) {
    const middle = (low + high) >> 1;
    if (Number(positions[middle].tick) <= tick) {
      result = positions[middle];
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return result;
}

export function efficiencyFretWindow(position, notes, previous = null, fullNeck = false) {
  if (fullNeck) return { first: 1, last: 24 };
  const frets = (notes || []).map(note => Number(note.fret))
    .filter(fret => Number.isInteger(fret) && fret > 0 && fret <= 24);
  const anchor = Math.max(1, Math.min(24, Math.floor(Number(position) || 1)));
  // Keep a stable frame while the hand and every ringing contact fit. Open
  // strings have their own column, so they never force a 1–24 view.
  if (previous && previous.last - previous.first < 12 &&
      anchor >= previous.first && anchor <= previous.last - 2 &&
      frets.every(fret => fret >= previous.first && fret <= previous.last)) {
    return previous;
  }
  let first = Math.max(1, Math.min(18, anchor - 1));
  let last = first + 6;
  if (frets.length) {
    first = Math.min(first, ...frets);
    last = Math.max(last, ...frets);
  }
  return { first, last };
}

export function setupFretboardEfficiencyLesson({ player, isSelected, onSelection }) {
  const initial = efficiencySelectionFromSearch(window.location.search);
  const fixtureSelect = document.getElementById('fretboardEfficiencyRiff');
  const versionSelect = document.getElementById('fretboardEfficiencyMapping');
  const status = document.getElementById('songPlayerStatus');
  const info = document.getElementById('fretboardEfficiencyInfo');
  const link = document.getElementById('fretboardEfficiencyLink');
  fixtureSelect.value = initial.fixtureId;
  versionSelect.value = initial.versionId;
  let request = 0;
  let dataPromise;
  const uploadedFixtures = new Map();

  function updateLink() {
    const builtIn = BUILT_IN_FIXTURE_IDS.includes(fixtureSelect.value);
    link.hidden = !builtIn;
    if (!builtIn) return;
    const url = new URL(window.location.href);
    url.searchParams.set('lesson', EFFICIENCY_LESSON_ID);
    url.searchParams.set('riff', fixtureSelect.value);
    url.searchParams.set('mapping', versionSelect.value);
    link.href = url.href;
    if (isSelected()) window.history.replaceState(null, '', url);
  }

  function showMetrics(version) {
    const metrics = version.metrics;
    const prefix = `Drop E · intervals relative to E · ${metrics.open_used} open notes`;
    if (version.id === 'strumPick') {
      info.textContent = prefix + ` · ${metrics.chord_skipped_strings ?? '—'} chord string skips` +
        ` · ${metrics.rapid_single_skipped_strings ?? '—'} rapid single-note string skips`;
    } else {
      info.textContent = prefix + ` · ${metrics.rapid_shift_count} rapid shifts` +
        ` · ${metrics.hand_travel_frets} frets travelled`;
    }
    if (version.objective) {
      const priorities = version.objective.priority_labels || version.objective.priority_order || [];
      info.title = ['Priorities: ' + priorities.join(' → ') + '.', version.description]
        .filter(Boolean).join(' ');
      if (Number.isFinite(version.objective.rapid_max_gap_seconds)) {
        info.title += ` Rapid pairs use at most ${version.objective.rapid_max_gap_seconds * 1000} ms between source attacks.` +
          ' Playback speed does not recompute the fingering.';
      }
    } else {
      info.title = 'Open-string priority, then rapid neck shifts, total movement, picking and familiar shapes. ' +
        'Greedy comparison uses the same original notes and timing; the original MIDI contains no fingering.';
    }
  }

  function updateAvailableVersions(fixture) {
    const available = new Set(fixture.versions.map(version => version.id));
    for (const option of versionSelect.options) option.disabled = !available.has(option.value);
  }

  async function activate() {
    if (!isSelected()) return;
    const attempt = ++request;
    fixtureSelect.disabled = true;
    versionSelect.disabled = true;
    status.textContent = 'Loading fretboard mapping…';
    info.textContent = 'Drop E · intervals relative to E';
    updateLink();
    try {
      dataPromise ||= fetch(import.meta.env.BASE_URL + 'data/fretboard-efficiency-fixtures.json')
        .then(response => {
          if (!response.ok) throw new Error('The MIDI mappings could not be loaded.');
          return response.json();
        }).catch(error => { dataPromise = null; throw error; });
      const data = await dataPromise;
      if (attempt !== request || !isSelected()) return;
      if (data.schema !== 'drop-e-fretboard-efficiency/1' || !Array.isArray(data.fixtures)) {
        throw new Error('This fretboard mapping format is not supported.');
      }
      const fixture = uploadedFixtures.get(fixtureSelect.value) ||
        data.fixtures.find(item => item.id === fixtureSelect.value);
      if (!fixture) throw new Error('The selected MIDI mapping is missing.');
      updateAvailableVersions(fixture);
      const version = fixture?.versions.find(item => item.id === versionSelect.value);
      if (!version) throw new Error('This fingering is unavailable for the saved mapping. Choose another fingering.');
      onSelection(fixture, version);
      await player.loadFretboardEfficiency(fixture, version.id);
      if (attempt !== request || !isSelected()) return;
      showMetrics(version);
    } catch (error) {
      if (attempt !== request || !isSelected()) return;
      status.textContent = error.message || 'The fretboard mapping could not be loaded.';
      info.textContent = 'Choose the riff again to retry.';
    } finally {
      if (attempt === request) {
        fixtureSelect.disabled = false;
        versionSelect.disabled = false;
      }
    }
  }

  fixtureSelect.addEventListener('change', activate);
  versionSelect.addEventListener('change', activate);
  updateLink();
  return {
    activate,
    syncSelection(fixture, versionId) {
      const version = fixture?.versions.find(item => item.id === versionId);
      if (!fixture || !version) return;
      uploadedFixtures.set(fixture.id, fixture);
      if (![...fixtureSelect.options].some(option => option.value === fixture.id)) {
        fixtureSelect.add(new Option(fixture.label || fixture.id, fixture.id));
      }
      fixtureSelect.value = fixture.id;
      updateAvailableVersions(fixture);
      versionSelect.value = version.id;
      onSelection(fixture, version);
      showMetrics(version);
      updateLink();
    },
    deactivate() {
      request++;
      fixtureSelect.disabled = false;
      versionSelect.disabled = false;
      const url = new URL(window.location.href);
      if (url.searchParams.get('lesson') === EFFICIENCY_LESSON_ID) {
        ['lesson', 'riff', 'mapping'].forEach(key => url.searchParams.delete(key));
        window.history.replaceState(null, '', url);
      }
    },
  };
}
