# Time solo intervals relative to F# minor

Analyzed the public `time.gp` Guitar Solo track, measures 94–143 (score ticks 357120–549120), with F# as tonic. Input SHA-256: `bd656f927c89b00fbc366b8659879d606937e4ff33fef60367023802c53aa89b`.

## Method

- Count each pitched note attack from the selected Guitar Solo track. Exclude the same rake beats the site filters (6 notes) and tie continuations (51 notes). Include six grace attacks. Count simultaneous double-stop notes individually.
- Intervals use the note's source concert pitch (`realValue`) modulo 12 against F#; all 147 counted pitches agree with string tuning + fret + capo. Bend destinations are separate from fretted attacks.
- Held share sums score beat durations for pitched notes, including tie continuations. This assigns bent notes' whole duration to their starting pitch, so it is a notation-weighted approximation, not measured acoustic occupancy.
- For next-note movement, select the highest pitch at each of 139 onsets and collapse adjacent repetitions of that exact pitch into 105 runs. This leaves 104 directed movements; simultaneous notes have no invented internal order. A next-note movement alone does not prove harmonic resolution.
- A stricter local approach means a non-chord tone followed within two semitones by a chord tone without crossing one of the site's 23 estimated chord sections. This chord model is inferred from the score, not an independent harmony annotation.

## Distribution of fretted/source note attacks

| Interval | Pitch class | Attacks | Share | Held share |
|---|---|---:|---:|---:|
| R | F# | 21 | 14.3% | 16.2% |
| b2 | G | 2 | 1.4% | 2.0% |
| 2 | G# | 10 | 6.8% | 5.4% |
| m3 (♭3) | A | 26 | 17.7% | 11.6% |
| M3 | A# | 0 | 0% | 0% |
| 4 | B | 33 | 22.4% | 34.7% |
| b5 | C | 0 | 0% | 0% |
| 5 | C# | 12 | 8.2% | 5.7% |
| b6 | D | 6 | 4.1% | 2.6% |
| 6 | D# | 0 | 0% | 0% |
| b7 | E | 37 | 25.2% | 21.8% |
| 7 | F | 0 | 0% | 0% |

The five F# minor pentatonic pitch classes (R, m3, 4, 5, b7) account for 129/147 attacks, or 87.8%. B (4) and E (b7) together account for 70/147, or 47.6%. Only two attacks are outside F# natural minor: G (b2). This says nothing about chromatic pitches reached *during* bends.

## Where the line goes next

Across 104 movements between different played pitches, the destinations are b7: 22, m3: 21, R: 20, 4: 20, 5: 9, 2: 7, b6: 4, b2: 1. The strongest directed pairs are **4 → m3** (11), **b7 → R** (9), **m3 → 4** (8), and **R → b7** (7). The 4 → m3 move is B → A; b7 → R is E → F#, commonly an upward whole step in this score.

With the stricter within-chord, stepwise non-chord-tone → chord-tone definition there are 16 approaches. Their destinations relative to F# are R: 7, m3: 5, 5: 2, 2: 1, 4: 1. The most repeated specific approach is b7 → R (6), followed by 4 → m3 (4). Only two of these 16 are semitone approaches; most are whole steps. These figures depend on the site's estimated chord labels, so treat them as candidate harmonic resolutions.

## Bends

There are 36 bend-marked attacks. Thirty-one have whole-semitone peak offsets (22 peaks at +2, seven at +1, two at +3); the remainder have fractional or zero peak offsets and are excluded from the integer-target tally. Those 31 bend peaks target 5 (C#) 13 times and R (F#) seven times; the remaining peaks are b6: 3, 4: 2, b5: 2, and b2, m3, M3, 7: one each. Thus the fifth is a stronger bend target than its 12 fretted attacks alone suggest. These are score-declared maximum bend pitches, not an acoustic measurement or separate attacks.
