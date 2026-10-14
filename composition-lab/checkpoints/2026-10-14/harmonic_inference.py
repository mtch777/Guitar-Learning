"""Shared symbolic chord vocabulary and evidence-aware matching.

Extensions use their conventional octave intervals (9=14, 11=17, 13=21)
while recognition operates on pitch classes. Chord identities are hypotheses;
non-unique exact matches must not be used for destructive edits.
"""
CHORDS = {
    '5': (0,7), 'major': (0,4,7), 'minor': (0,3,7),
    'sus2': (0,2,7), 'sus4': (0,5,7), 'dim': (0,3,6), 'aug': (0,4,8),
    'major7': (0,4,7,11), 'minor7': (0,3,7,10), 'dom7': (0,4,7,10),
    'minor_major7': (0,3,7,11), 'half_dim7': (0,3,6,10),
    'dim7': (0,3,6,9), '7sus4': (0,5,7,10),
    '6': (0,4,7,9), 'minor6': (0,3,7,9),
    'add9': (0,4,7,14), 'minor_add9': (0,3,7,14),
    '6_9': (0,4,7,9,14), 'minor6_9': (0,3,7,9,14),
    'major9': (0,4,7,11,14), 'minor9': (0,3,7,10,14),
    'dom9': (0,4,7,10,14), '7b9': (0,4,7,10,13),
    '7#9': (0,4,7,10,15), 'major7#11': (0,4,7,11,18),
    '7#11': (0,4,7,10,18), '7b5': (0,4,6,10),
    '7#5': (0,4,8,10), '7b13': (0,4,7,10,20),
    'minor11': (0,3,7,10,14,17), 'dom11': (0,4,7,10,14,17),
    'major11': (0,4,7,11,14,17),
    'major13': (0,4,7,11,14,21), 'minor13': (0,3,7,10,14,21),
    'dom13': (0,4,7,10,14,21),
    '13b9': (0,4,7,10,13,21), '13#11': (0,4,7,10,14,18,21),
}
NAMES = ('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
def norm(p): return int(p)%12
def name(p): return NAMES[norm(p)]
def chords_for(notes, bass=None, limit=5):
    """Existing coverage/completeness scoring applied to expanded vocabulary."""
    notes={norm(p) for p in notes}
    if len(notes)<2:return []
    choices=[]
    for root in range(12):
        for quality,intervals in CHORDS.items():
            chord={(root+x)%12 for x in intervals}
            hit=notes&chord
            if len(hit)<2:continue
            covered=len(hit)/len(notes);completeness=len(hit)/len(chord)
            fit=.73*covered+.27*completeness
            relation='absent' if bass is None else ('root' if norm(bass)==root else
                     'inversion' if norm(bass) in chord else 'pedal_or_nonchord')
            if relation=='root':fit+=.1
            elif relation=='inversion':fit+=.035
            choices.append({'root':root,'quality':quality,'fit':round(fit,4),
                   'bass_relation':relation,'matched':[name(p) for p in sorted(hit)],
                   'nonchord':[name(p) for p in sorted(notes-chord)]})
    return sorted(choices,key=lambda v:(-v['fit'],-len(v['matched']),v['root']))[:limit]