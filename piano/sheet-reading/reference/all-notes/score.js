export const LOWEST_MIDI = 21; // A0
export const HIGHEST_MIDI = 108; // C8
export const NOTES_PER_MEASURE = 8;
export const EXPECTED_COUNT = HIGHEST_MIDI - LOWEST_MIDI + 1;

const SHARP_SPELLINGS = [
  ['C', 0], ['C', 1], ['D', 0], ['D', 1], ['E', 0], ['F', 0],
  ['F', 1], ['G', 0], ['G', 1], ['A', 0], ['A', 1], ['B', 0],
];

export function noteForMidi(midi) {
  if (!Number.isInteger(midi) || midi < LOWEST_MIDI || midi > HIGHEST_MIDI) {
    throw new RangeError('Expected a note on the 88-key piano.');
  }
  const [step, alter] = SHARP_SPELLINGS[midi % 12];
  const octave = Math.floor(midi / 12) - 1;
  return {midi, step, alter, octave, name: step + (alter ? '♯' : '') + octave};
}

export function buildAllNotesMusicXML({showNames = true} = {}) {
  const head = `<?xml version="1.0" encoding="utf-8"?>
<score-partwise version="4.0">
  <work><work-title>All Notes</work-title></work>
  <movement-title>All Notes</movement-title>
  <identification><creator type="composer">Sheet Reading</creator></identification>
  <part-list><score-part id="P1"><part-name>Piano</part-name><part-abbreviation>Pno.</part-abbreviation></score-part></part-list>
  <part id="P1">`;
  const measures = [];
  for (let measureIndex = 0; measureIndex < EXPECTED_COUNT / NOTES_PER_MEASURE; measureIndex++) {
    const attributes = measureIndex === 0
      ? '<attributes><divisions>480</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>F</sign><line>4</line></clef></attributes>'
      : measureIndex === 5
        ? '<attributes><clef><sign>G</sign><line>2</line></clef></attributes>'
        : '';
    const notes = [];
    for (let slot = 0; slot < NOTES_PER_MEASURE; slot++) {
      const midi = LOWEST_MIDI + measureIndex * NOTES_PER_MEASURE + slot;
      const n = noteForMidi(midi);
      const beam = slot % 4 === 0 ? 'begin' : slot % 4 === 3 ? 'end' : 'continue';
      const pitch = `<pitch><step>${n.step}</step>${n.alter ? '<alter>1</alter>' : ''}<octave>${n.octave}</octave></pitch>`;
      const accidental = n.alter ? '<accidental>sharp</accidental>' : '';
      const lyric = showNames ? `<lyric number="1"><syllabic>single</syllabic><text>${n.step+(n.alter?'♯':'')}</text></lyric>` : '';
      notes.push(`<note id="all-notes-${midi}">${pitch}<duration>240</duration><type>eighth</type>${accidental}<stem>up</stem><beam number="1">${beam}</beam>${lyric}</note>`);
    }
    measures.push(`<measure number="${measureIndex + 1}">${attributes}${notes.join('')}</measure>`);
  }
  return head + measures.join('') + '</part></score-partwise>';
}
