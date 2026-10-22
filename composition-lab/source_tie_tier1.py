"""Pure source tie/position declarations required by written-lane eligibility."""
import json
from source_key_tier1 import extract as extract_context


def extract(capture):
    lower=extract_context(capture)
    metadata=json.loads((capture/'metadata.json').read_text(encoding='utf-8-sig'))
    parts=[];occurrences=[]
    for path in sorted(capture.glob('track-*.json'),key=lambda p:int(p.stem.split('-')[-1])):
        part=json.loads(path.read_text(encoding='utf-8-sig'));pid=part['partId']
        parts.append(dict(part_id=pid,fields={k:part[k] for k in ('instrumentId','tuning','capo') if k in part}))
        for mi,measure in enumerate(part.get('measures',[]),1):
            for vi,voice in enumerate(measure.get('voices',[])):
                for bi,beat in enumerate(voice.get('beats',[])):
                    for ni,note in enumerate(beat.get('notes',[])):
                        if note.get('rest'):continue
                        occurrences.append(dict(occurrence_ref=f"event:{metadata['songId']}:{pid}:{mi}:{vi}:{bi}:{ni}",fields={k:note[k] for k in ('string','fret','dead','tie') if k in note}))
    lower.update(schema='normalized-written-tie-context/4',scope='written_context_geometry_keys_and_tie_notation',tie_notation=dict(parts=parts,occurrences=occurrences))
    return lower
