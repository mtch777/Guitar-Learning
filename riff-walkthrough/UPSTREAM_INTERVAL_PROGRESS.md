# Upstream interval preference

- Seed stays uniformly random within existing artist/role filters.
- Scaffold selection multiplies existing similarity by the interval preference once when a retained donor phrase (2+) has an exactly two-slot sounding overlap. Replaced donor opening is not evidence. Invalid/partial timing is neutral. Default 2x.
- Rhythm selection uses exactly two simultaneous sounding slots, including staggered attacks/holds, clipped to exact phrase boundaries. This selects the capacity for an interval before pitches exist, not a promise of distinct pitches. Chords with 3+ active slots alone do not qualify.
- Scaffold source evidence is a preference, not a guarantee of subsequent rhythm. Rhythm is the actual slot-setting step.
- Pitch-only interval multiplier removed, including old saved dictionaries. Actual minor-second pitch boost remains 2x and checks assigned sounding pitches. No upstream minor-second claim added.
- All other filters and weights unchanged. Preferences are exposed at Scaffold/Rhythm; pitch stages expose minor-second only.

## Verification
- 66 existing Python tests and 7 frontend suites passed (optional fixture rendering unavailable).
- Real-dataset 10,000 draws at each weight, same candidate sets: scaffold interval-capable share 37.97% (1x), 56.08% (2x), 86.38% (10x); rhythm 23.27%, 38.59%, 75.76%.
- This is one fixed seed/context comparison, not a corpus-wide musical-quality guarantee.
- Actual generated rhythm comparison with fixed seed/scaffold: 37 phrases; interval-capable phrases at 1x = 0, 2x = 14, 10x = 37. Repeat links preserved.
