# Joint key/function inference — bounded audit

2026-10-22. Research only; no new model installed or executed.

| Candidate | Observed constraint | Decision |
|---|---|---|
| [Raphael–Stoddard2003](https://ismir2003.ismir.net/papers/Raphael.pdf) | Fixed metric windows; secondary function encoded as modulation. Some experimental transition parameters set by hand; verified runnable parameter artifacts not located in this search. | Do not invent parameters or call its states structural key changes. |
| [Rameau2009](https://www.ic.unicamp.br/~tachard/docs/sbcm2009.pdf) | Its Pardo extension derives whole-piece key from the first chord. HMM reproduction still requires verified learned parameters. | No first-chord-as-key shortcut. |
| [McLeod–Rohrmeier2021](https://github.com/apmcleod/harmonic-inference) | Released weights/settings exist. All14 inspected metadata files across both checkpoint families specify TPC, not semitone-only inputs. README encodes applied chords as key changes. | Cannot force current Songsterr facts into the native pretrained input or reinterpret its effective tonics as established keys. |

Pinned McLeod source: `b257424fcb049bb318fe05c22c0ae9318d6e2a0f`.
The enum defines TPC=0/MIDI=1; metadata pitch fields all contain0. Native note
features include spelled pitch, register and metric timing. Current Songsterr
T1 preserves semitone pitches but does not own authored letter spelling.
Reading metadata does not prove checkpoint-binary compatibility or accuracy.

Private audit retains source/configuration files, all metadata fields and hashes.
AST literal enum inspection and YAML node composition execute no tagged objects.
No model weights were downloaded, loaded, trained or published.

This is a different model from the previously audited Masada–Bunescu CRF;
that earlier investigation is preserved, not restarted or silently replaced.

## Required distinctions

| Concept | Current status |
|---|---|
| Established primary/local key | Not solved by this audit. |
| Effective local-tonic proposal | Potential model output; cannot imply structural modulation. |
| Temporary tonicized target | Requires evidence distinguishing it from established key. |
| Conditional chord degree/membership | Exact coordinates under an explicit context hypothesis; not inferred function. |

Planner reviewed and rejected forced deployment. Next independent musical work:
conditional note-role evidence over the existing harmonic-span alternatives.
Use unambiguous source voice sequences, exact approach/departure/timing and
contextual membership. Preserve path-consistent alternatives. Refuse ambiguous
polyphony; do not claim diatonic steps without spelling or label artistic intent.
