// Controls and viewport decisions for the existing trainer/Song Player lesson.
// Sound, score timing and active contacts remain owned by Song Player.
export const EFFICIENCY_LESSON_ID = 'fretboardEfficiency';
export const EFFICIENCY_TUNING_LOW_TO_HIGH = [28, 35, 40, 45, 50, 55, 59, 64];

export function efficiencySelectionFromSearch(search) {
  const params = new URLSearchParams(search);
  return {
    selected: params.get('lesson') === EFFICIENCY_LESSON_ID,
    fixtureId: params.get('riff') === 'da80eca9' ? 'da80eca9' : 'cfa029a2',
    versionId: params.get('mapping') === 'greedy' ? 'greedy' : 'optimized'
  };
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
    const builtIn = ['cfa029a2', 'da80eca9'].includes(fixtureSelect.value);
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
    info.textContent = `Drop E · intervals relative to E · ${metrics.open_used} open notes` +
      ` · ${metrics.rapid_shift_count} rapid shifts · ${metrics.hand_travel_frets} frets travelled`;
    info.title = 'Open-string priority, then rapid neck shifts, total movement, picking and familiar shapes. ' +
      'Greedy comparison uses the same original notes and timing; the original MIDI contains no fingering.';
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
      const version = fixture?.versions.find(item => item.id === versionSelect.value);
      if (!fixture || !version) throw new Error('The selected MIDI mapping is missing.');
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
