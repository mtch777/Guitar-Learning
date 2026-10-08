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
