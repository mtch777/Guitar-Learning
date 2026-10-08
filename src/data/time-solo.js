/*
  Time — Guitar Solo source data.

  Extracted from the user-provided 6-string HTML tab.
  Source low -> high: E A D G B e
  Mapped to 8-string physical strings 3 -> 8:
    E2 A2 D3 G3 B3 E4

  Internal stringIndex remains zero-based / low -> high,
  so source strings map to indices 2..7.

  "_" means the source note occurrence had no relative-interval
  annotation in the HTML. All 125 note events are preserved here;
  the lesson groups repeated events by physical fretboard position
  only for simultaneous display.
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

const TIME_SOLO_ENCODED_NOTES =
  '6,0,5;6,2,6;6,2,6;6,2,b5;6,0,3;6,2,7;6,2,7;6,2,_;6,2,6;6,4,7;6,3,b7;6,3,b7;6,5,R;6,3,b7;6,5,R;6,3,b7;6,5,R;6,3,b7;6,5,R;5,2,4;6,2,_;6,0,_;6,2,b5;6,4,b6;6,7,7;6,7,3;4,7,5;6,7,3;6,8,4;6,8,4;6,7,3;6,7,_;6,7,_;6,7,2;6,7,2;6,14,6;6,12,5;6,15,b7;6,15,b7;6,15,b7;6,15,R;6,15,R;6,15,5;6,15,5;6,15,5;6,14,7;6,14,7;6,14,7;6,14,7;6,14,6;6,14,6;6,14,6;6,14,6;6,15,b7;6,15,b7;6,14,6;6,12,5;5,14,4;6,12,5;6,15,b7;6,15,b7;6,15,b7;6,15,b7;6,15,5;6,14,b5;6,12,3;6,14,b5;6,12,3;6,14,b5;6,17,6;6,17,6;6,17,2;6,17,2;6,17,2;6,14,6;6,15,b7;6,15,b7;6,17,R;6,15,b7;6,17,R;6,15,b7;6,15,2;6,12,7;6,12,7;6,12,7;6,0,7;5,2,6;6,5,2;6,5,2;6,8,4;6,10,6;6,8,5;6,7,b5;6,8,5;6,7,b5;6,3,R;6,3,R;6,3,R;6,5,2;6,7,3;6,7,3;6,5,2;6,3,R;6,3,2;6,5,3;6,3,2;6,0,7;6,3,2;6,0,7;6,2,b2;6,2,b2;6,2,b2;6,2,b2;6,2,b2;6,0,7;6,2,b2;6,0,7;6,2,_;6,0,_;6,0,_;6,2,_;6,4,_;6,4,_;6,2,_;6,0,_';

export const TIME_SOLO_TAB_NOTES =
  Object.freeze(
    TIME_SOLO_ENCODED_NOTES
      .split(';')
      .map(
        encodedNote => {
          const [
            stringIndex,
            fret,
            interval
          ] =
            encodedNote.split(',');

          return Object.freeze({
            stringIndex:
              Number(stringIndex),
            fret:
              Number(fret),
            interval:
              interval === '_'
                ? null
                : interval
          });
        }
      )
  );

export const TIME_SOLO_INTERVAL_STYLES =
  Object.freeze({
    R:  { background: '#34a853', color: '#1a1a1a' },
    b2: { background: '#feffb3', color: '#1a1a1a' },
    2:  { background: '#ffff00', color: '#1a1a1a' },
    3:  { background: '#ff9900', color: '#1a1a1a' },
    4:  { background: '#b4a7d5', color: '#1a1a1a' },
    b5: { background: '#9900ff', color: '#ffffff' },
    5:  { background: '#ff0000', color: '#1a1a1a' },
    b6: { background: '#f9ca9c', color: '#1a1a1a' },
    6:  { background: '#ff9900', color: '#1a1a1a' },
    b7: { background: '#feffb3', color: '#1a1a1a' },
    7:  { background: '#ffff00', color: '#1a1a1a' }
  });
