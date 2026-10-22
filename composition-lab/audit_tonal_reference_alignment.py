"""Source/annotation alignment audit independent of all model predictions."""
from collections import Counter
from fractions import Fraction as F
import re
from music21 import converter, stream
from check_musicxml_context_source import raw_notes


def audit(source,annotation):
    raw,parts=raw_notes(source);gold=converter.parse(str(annotation))
    frames=parts[0]
    if any(p!=frames for p in parts):raise ValueError('Unaligned source parts')
    gold_measures=list(gold.parts[0].getElementsByClass(stream.Measure))
    source_base={};issues=[];previous=None
    for label,start,span in frames:
        match=re.fullmatch(r'(\d+)([a-z]*)',label)
        if match is None:raise ValueError('Unsupported source measure label')
        base,suffix=match.groups()
        if not suffix:
            if base in source_base:issues.append('Duplicate source base measure')
            source_base[base]=start;previous=base
        elif previous!=base:issues.append('Continuation suffix without same base measure')
    annotation_starts={m.measureNumberWithSuffix():str(F(m.offset)) for m in gold_measures}
    if source_base!=annotation_starts:issues.append('Source/reference labelled measure downbeats differ')
    end=F(frames[-1][1])+F(frames[-1][2]);gold_end=F(gold.highestTime)
    roman=list(gold.recurse().getElementsByClass('RomanNumeral'))
    onsets=[F(r.getOffsetInHierarchy(gold)) for r in roman]
    trailing_only=not issues and gold_end>=end and all(t<end for t in onsets)
    if gold_end!=end and not trailing_only:issues.append('Unexplained annotation/source extent mismatch')
    witnesses=[];counts=Counter()
    for r,t in zip(roman,onsets):
        source_pcs={int(F(pitch)%12) for part,bar,pitch,onset,duration in raw if F(onset)<=t<F(onset)+F(duration)}
        annotated_pcs={p.pitchClass for p in r.pitches}
        offsets=[k for k in range(12) if {(p+k)%12 for p in annotated_pcs}==source_pcs]
        counts.update(offsets)
        witnesses.append(dict(at_q=str(t),figure=r.figure,annotated_chord_pcs=sorted(annotated_pcs),source_written_overlap_pcs=sorted(source_pcs),exact_set_offsets=offsets))
    return dict(clock_status='FAIL' if issues else 'PASS',issues=issues,source_downbeats=source_base,annotation_downbeats=annotation_starts,source_end_q=str(end),annotation_end_q=str(gold_end),annotation_tail_excluded_q=str(max(F(0),gold_end-end)),common_support_end_q=str(min(end,gold_end)),chord_set_offset_counts={str(k):counts[k] for k in range(12)},chord_witnesses=witnesses,
                no_predictions_read=True,offset_selection='Not selected automatically; review actual source/annotation witnesses and contradictions',claim='Notation coordinate/alignment audit only, not method accuracy')
