"""Compatibility entrypoint; implementation lives in harmonic_inference.py.

Run: python infer_tonality.py <GP files> --output result.json
"""
from harmonic_inference import (
    NAMES, MODES, CHORDS, DEFAULTS, collect, chords_for,
    tonal_candidates, analyze_measure, infer_score, infer, main
)
chord_hypotheses = chords_for
candidate_evidence = tonal_candidates
if __name__=="__main__":
    main()
