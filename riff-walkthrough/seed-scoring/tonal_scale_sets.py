"""Distinct diatonic pitch-class collections; roots/modes remain alternatives."""
import json,collections
MODES={'Ionian':(0,2,4,5,7,9,11),'Dorian':(0,2,3,5,7,9,10),'Phrygian':(0,1,3,5,7,8,10),'Lydian':(0,2,4,6,7,9,11),'Mixolydian':(0,2,4,5,7,9,10),'Aeolian':(0,2,3,5,7,8,10),'Locrian':(0,1,3,5,6,8,10)}
NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];ROOTS={n:i for i,n in enumerate(NAMES)}
ALIASES=collections.defaultdict(list)
for root in range(12):
 for mode,intervals in MODES.items():ALIASES[tuple(sorted((root+p)%12 for p in intervals))].append({'tonic':NAMES[root],'mode':mode})
ALL=tuple(sorted(ALIASES))
def from_notes(notes,previous=None):
 pcs={n['midi_pitch']%12 for n in notes}
 return tuple(s for s in (ALL if previous is None else previous) if pcs<=set(s))
def estimated(row):
 root=ROOTS.get(row.get('Provisional tonal center/key (riff; mapped)',''))
 if root is None:return (), 'unknown candidate provisional tonic'
 try:modes=json.loads(row.get('Compatible modes (phrase; mapped; provisional riff tonic)','[]'))
 except (ValueError,TypeError):return (), 'invalid candidate compatible-mode evidence'
 if not isinstance(modes,list) or any(m not in MODES for m in modes):return (), 'invalid candidate compatible-mode evidence'
 if not modes:return (), 'no candidate compatible-mode evidence'
 return tuple(sorted({tuple(sorted((root+p)%12 for p in MODES[m])) for m in modes})),None
def public(scales):return [{'pitch_classes':list(s),'relative_key_aliases':ALIASES[tuple(s)]} for s in scales]
