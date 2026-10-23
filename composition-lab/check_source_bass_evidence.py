"""Independent literal TSV oracle; imports no bass producer or annotations."""
import csv
from fractions import Fraction as F
from bisect import bisect_left


def read(path):
    with open(path,encoding='utf-8',newline='')as stream:return list(csv.DictReader(stream,delimiter='\t'))


def check(piece,observations,notes_path,measures_path,features):
    measures=read(measures_path);starts={};offset=F(0)
    for row in measures:
        mc=int(row['mc'])
        if mc in starts:raise ValueError('Duplicate raw MC')
        starts[mc]=offset;offset+=4*F(row['act_dur'])
    clocks=[F(r['start_q'])for r in observations];active=[[]for r in observations];raw_issues=[]
    if len(clocks)!=len(set(clocks))or clocks!=sorted(clocks):raise ValueError('Ambiguous observation clocks')
    # Interval-to-cell indexing deliberately differs from producer's sweep.
    for index,row in enumerate(read(notes_path)):
        a=starts[int(row['mc'])]+4*F(row['mc_onset']);duration=4*F(row['duration'])
        if duration<0:raise ValueError('Negative raw duration')
        if duration==0:continue
        pitch=None if row.get('midi','')==''else int(row['midi'])
        for boundary in (a,a+duration):
            insertion=bisect_left(clocks,boundary)
            if insertion and clocks[insertion-1]<boundary<F(observations[insertion-1]['end_q']):
                raw_issues.append('Raw note boundary inside fixed observation cell')
        for i in range(bisect_left(clocks,a),bisect_left(clocks,a+duration)):
            active[i].append((f'note-row:{index}',pitch))
    expected=[];issues=list(dict.fromkeys(raw_issues))
    for row,notes in zip(observations,active):
        pitches=[p for ref,p in notes if p is not None];unknown=sorted(ref for ref,p in notes if p is None)
        status='UNRESOLVED'if unknown else'EMPTY'if not notes else'KNOWN';lowest=min(pitches)if status=='KNOWN'else None
        wanted=dict(piece=piece,observation_ref=row['id'],start_q=row['start_q'],end_q=row['end_q'],status=status,lowest_midi=lowest,lowest_pc=None if lowest is None else lowest%12,
            lowest_note_refs=[]if lowest is None else sorted(ref for ref,p in notes if p==lowest),active_note_refs=sorted(ref for ref,p in notes),unknown_note_refs=unknown)
        if sum(1<<p for p in {p%12 for p in pitches})!=row['mask']:issues.append('Independent raw mask differs')
        expected.append(wanted)
    # JSON spelling catches bool/int aliases and unexpected fields.
    import json
    if json.dumps(expected,sort_keys=True)!=json.dumps(features,sort_keys=True):issues.append('Exact raw bass feature inventory/value/type/witness differs')
    return dict(status='PASS_RAW_SOURCE_BASS_FEATURES'if not issues else'FAIL',piece=piece,expected_cells=len(expected),actual_cells=len(features),issues=issues,
        scope='Lowest active nominal MIDI from raw notes/measures only; not a structural bass, key or acoustic label')
