/*
  Time — Guitar Solo source fret data.

  Extracted from the user-provided 6-string HTML tab using ONLY:
    - source string
    - fret number

  Relative-interval annotations are intentionally ignored because
  they are relative to the chord sounding at that moment and do not
  represent one fixed fretboard-relative interval map.

  Source low -> high: E A D G B e
  Mapped to 8-string physical strings 3 -> 8:
    E2 A2 D3 G3 B3 E4

  Internal stringIndex is zero-based / low -> high,
  so source strings map to indices 2..7.
*/

export const TIME_SOLO_DROP_E_TUNING =
  Object.freeze([
    28, // E1
    35, // B1
    40, // E2
    45, // A2
    50, // D3
    55, // G3
    59, // B3
    64  // E4
  ]);

// The uploaded Time score sounds in F# minor (pitch class 6). The fretboard's
// Drop E tuning changes fingering, not the source harmony or its tonic.
const TIME_SOLO_SOURCE_TONIC = 6;
const MINOR_KEY_DEGREES = Object.freeze([
  'I', '♭II', 'II', '♭III', 'III', 'IV',
  '♭V', 'V', '♭VI', 'VI', '♭VII', 'VII'
]);

export function timeSoloChordNumeral(root, quality) {
  if (!Number.isInteger(root) || root < 0 || root > 11 ||
      !['major', 'minor', 'diminished'].includes(quality)) return null;
  const interval = (root - TIME_SOLO_SOURCE_TONIC + 12) % 12;
  const degree = MINOR_KEY_DEGREES[interval];
  if (quality === 'major') return degree;
  return degree.toLowerCase() + (quality === 'diminished' ? '°' : '');
}

const TIME_SOLO_ENCODED_FRETS =
  '6,0;6,2;6,2;6,2;6,0;6,2;6,2;6,2;6,2;6,4;6,3;6,3;6,5;6,3;6,5;6,3;6,5;6,3;6,5;5,2;6,2;6,0;6,2;6,4;6,7;6,7;4,7;6,7;6,8;6,8;6,7;6,7;6,7;6,7;6,7;6,14;6,12;6,15;6,15;6,15;6,15;6,15;6,15;6,15;6,15;6,14;6,14;6,14;6,14;6,14;6,14;6,14;6,14;6,15;6,15;6,14;6,12;5,14;6,12;6,15;6,15;6,15;6,15;6,15;6,14;6,12;6,14;6,12;6,14;6,17;6,17;6,17;6,17;6,17;6,14;6,15;6,15;6,17;6,15;6,17;6,15;6,15;6,12;6,12;6,12;6,0;5,2;6,5;6,5;6,8;6,10;6,8;6,7;6,8;6,7;6,3;6,3;6,3;6,5;6,7;6,7;6,5;6,3;6,3;6,5;6,3;6,0;6,3;6,0;6,2;6,2;6,2;6,2;6,2;6,0;6,2;6,0;6,2;6,0;6,0;6,2;6,4;6,4;6,2;6,0';

export const TIME_SOLO_TAB_NOTES =
  Object.freeze(
    TIME_SOLO_ENCODED_FRETS
      .split(';')
      .map(
        encodedNote => {
          const [
            stringIndex,
            fret
          ] =
            encodedNote.split(',');

          return Object.freeze({
            stringIndex:
              Number(stringIndex),
            fret:
              Number(fret)
          });
        }
      )
  );

/* Historical original-tab chord-relative labels, preserved in occurrence order.
   The source provides no beat positions or timestamps; chord sections below
   are therefore event-order sections, not timed harmonic measurements. */
const TIME_SOLO_ORIGINAL_ANNOTATIONS = '6,0,5;6,2,6;6,2,6;6,2,b5;6,0,3;6,2,7;6,2,7;6,2,_;6,2,6;6,4,7;6,3,b7;6,3,b7;6,5,R;6,3,b7;6,5,R;6,3,b7;6,5,R;6,3,b7;6,5,R;5,2,4;6,2,_;6,0,_;6,2,b5;6,4,b6;6,7,7;6,7,3;4,7,5;6,7,3;6,8,4;6,8,4;6,7,3;6,7,_;6,7,_;6,7,2;6,7,2;6,14,6;6,12,5;6,15,b7;6,15,b7;6,15,b7;6,15,R;6,15,R;6,15,5;6,15,5;6,15,5;6,14,7;6,14,7;6,14,7;6,14,7;6,14,6;6,14,6;6,14,6;6,14,6;6,15,b7;6,15,b7;6,14,6;6,12,5;5,14,4;6,12,5;6,15,b7;6,15,b7;6,15,b7;6,15,b7;6,15,5;6,14,b5;6,12,3;6,14,b5;6,12,3;6,14,b5;6,17,6;6,17,6;6,17,2;6,17,2;6,17,2;6,14,6;6,15,b7;6,15,b7;6,17,R;6,15,b7;6,17,R;6,15,b7;6,15,2;6,12,7;6,12,7;6,12,7;6,0,7;5,2,6;6,5,2;6,5,2;6,8,4;6,10,6;6,8,5;6,7,b5;6,8,5;6,7,b5;6,3,R;6,3,R;6,3,R;6,5,2;6,7,3;6,7,3;6,5,2;6,3,R;6,3,2;6,5,3;6,3,2;6,0,7;6,3,2;6,0,7;6,2,b2;6,2,b2;6,2,b2;6,2,b2;6,2,b2;6,0,7;6,2,b2;6,0,7;6,2,_;6,0,_;6,0,_;6,2,_;6,4,_;6,4,_;6,2,_;6,0,_';
export const TIME_SOLO_SOURCE_EVENTS = Object.freeze(
  TIME_SOLO_ORIGINAL_ANNOTATIONS.split(';').map((encoded, index) => {
    const [stringIndex, fret, interval] = encoded.split(',');
    const original = TIME_SOLO_TAB_NOTES[index];
    if (!original || original.stringIndex !== Number(stringIndex) ||
        original.fret !== Number(fret)) {
      throw new Error('Time solo source event mismatch at index ' + index);
    }
    return Object.freeze({...original, interval: interval === '_' ? null : interval});
  })
);
