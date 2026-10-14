# V13 — Context-backed partial/rootless chord integration

Adds `contextual_harmony.supplement_anchors()` to the automatic reharmonization pipeline **before** continuity expansion and chord substitution.

- An incomplete / rootless voicing is promoted only when it is a strict subset of identical, independently observed chord anchors on both sides.
- Requires at least two distinct pitch classes, no other voice with contradictory pitch classes, and a configurable maximum gap.
- This is intentionally conservative and is **not a full rootless chord estimator**.
- All source note IDs/times stay untouched. Reharmonization remains restricted by shared-note-ID safety and guitar playability.

Local tests: 31 passing (includes four new contextual inference tests). On Chet Baker 41-bar nylon guitar:
- 69 observed chord events, 28 partial candidates, 0 promoted; 45 safely changed note definitions.
- No increase in recognized chords on this real song. The algorithm remains unable to infer chords that lack two concordant anchors.

Run: `python -m unittest discover -p 'test_*.py' -q` and
`python automatic_harmony_control.py 'Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp' --output output.gp`