"""Bounded written pitch/time extraction for private reference evaluation.

Never reads harmony annotations. This is not a full MusicXML/GP converter.
All parts must independently agree on their source measure clock and meter.
"""
from fractions import Fraction as F
from pathlib import Path
from music21 import converter, stream
from musical_tier2 import geometry_relation, geometry_inventory


def extract(path):
    score=converter.parse(str(path))
    frames=None;parts=[];events=[];first_extent=F(0)
    for part_id,part in enumerate(score.parts):
        measures=list(part.getElementsByClass(stream.Measure));local=[];meter=None;witness=0
        for ordinal,measure in enumerate(measures,1):
            explicit=measure.timeSignature
            if explicit is not None: meter=explicit;witness=ordinal
            if meter is None: raise ValueError("Source meter missing; cannot supply 4/4")
            start=F(measure.offset)
            span=F(measures[ordinal].offset)-start if ordinal<len(measures) else F(measure.duration.quarterLength)
            local.append(dict(id=f"measure:{ordinal}",ordinal=ordinal,label=measure.measureNumberWithSuffix(),start_q=str(start),span_q=str(span),signature=[meter.numerator,meter.denominator],meter_source="explicit" if explicit is not None else "inherited",meter_source_frame=witness))
            voices=list(measure.getElementsByClass(stream.Voice))
            # Music21 keeps ordinary single-voice notes directly in the measure.
            containers=voices if voices else [measure]
            direct=list(measure.notes) if voices else []
            if direct: raise ValueError("Mixed direct/voice note ownership requires explicit adapter support")
            for voice_id,voice in enumerate(containers):
                for beat_id,item in enumerate(voice.notes):
                    offset=F(item.getOffsetInHierarchy(measure));duration=F(item.duration.quarterLength)
                    if ordinal==1:first_extent=max(first_extent,offset+duration)
                    for note_id,pitch in enumerate(item.pitches):
                        events.append(dict(id=f"xml:{part_id}:{ordinal}:{voice_id}:{beat_id}:{note_id}",part_id=part_id,bar=ordinal,voice=voice_id,beat=beat_id,note=note_id,pitch=str(F(pitch.ps)),onset_q=str(start+offset),duration_q=str(duration)))
        if frames is None:frames=local
        elif local!=frames:raise ValueError("Source parts disagree on measure labels, clocks or meter declarations")
        parts.append(dict(part_id=part_id,frame_refs=[r['id'] for r in local],source_pickup_declared=None))
    geometry=dict(source_format="musicxml",source_id=Path(path).name,frames=frames or [],parts=parts,first_notated_span_q=str(first_extent) if frames else None)
    parameters=geometry_relation(source=geometry)['parameters']
    return dict(tier=1,schema="normalized-written-context-facts/3",scope="written_context_facts_geometry_and_optional_source_keys",events=events,
                source_coverage=dict(expected=len(events),actual=len(events),tracks=len(parts),layout_warnings=[],timing_warnings=[]),
                measure_geometry=geometry,source_key_declarations=None,source_key_inventory=geometry_inventory(parameters))
