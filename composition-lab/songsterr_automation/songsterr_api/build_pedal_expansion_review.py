"""Four-way private phrase expansion diff; unchanged detector and source audio."""
import argparse
from fractions import Fraction as F
import json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from build_pedal_evidence_review import write_requests


LABELS=dict(before='Existing phrase: continuation BEFORE',after='Existing phrase: continuation AFTER',
            both='Existing phrase: continuation BEFORE AND AFTER',combined='Existing phrases: continuation COMBINED them')


def build(report,evaluation,corpus,out):
    songs={s['song_id']:s for s in report['songs']};requests=[]
    for record in evaluation['tracks']:
        song=songs[record['song_id']];track=next(t for t in song['tracks'] if t['part_id']==record['part_id'])
        byid={n['occurrence']:n for n in track['rows']};seeds={s['id']:s for s in record['seeds']}
        for r in record['phrases']:
            if r['direction']=='unchanged':continue
            originals=[seeds[i] for i in r['seed_ids']]
            oldroles={i:v for s in originals for i,v in s['roles'].items()}
            oldcycles=[c for s in originals for c in s['cycles']]
            before=dict(accepted=True,roles=oldroles,cycles=oldcycles,anchor_pitches=sorted({byid[i]['midi'] for i,v in oldroles.items() if v=='call'}))
            after=dict(accepted=True,roles=r['roles'],cycles=r['cycles'],anchor_pitches=sorted({byid[i]['midi'] for i,v in r['roles'].items() if v=='call'}))
            requests.append(dict(song_id=record['song_id'],part_id=record['part_id'],song=song['title'],track=track['name'].strip() or f"Track {track['part_id']+1}",
                bars=[r['start_bar'],r['end_bar']],direction=r['direction'],before=before,after=after,return_members=[],
                original_bounds=r['original_bounds'],expanded_bounds=dict(start_q=r['start_q'],end_q=r['end_q']),seed_ids=r['seed_ids'],added_exchanges=len(r['added_cycles']),
                review_message=f"{LABELS[r['direction']]}. {len(originals)} original pattern(s) retained; {len(r['added_cycles'])} additional complete exchanges. Orange outlines show original bounds; green outlines show expansion. Before/after share the same unchanged source audio."))
    metadata=dict(schema='pedal-expansion-review-v1',labels=LABELS,
        summary=f"{len(requests)} expanded/combined phrases · {evaluation['counts']['input_seeds']} original patterns all retained · no new detections and no removals.",
        definition='Before: unchanged evidence-detector support. After: separate additive continuation pass. Earlier material requires two exchanges; later material requires one. Same exact anchor, strictly later answers; no overlap or double counting.',
        dataset_sha256=hashlib.sha256(json.dumps(evaluation,separators=(',',':')).encode()).hexdigest(),
        expansion_sha256=evaluation['algorithm_sha256'],algorithm_sha256=evaluation['detector_sha256'])
    return write_requests(report,requests,corpus,out,metadata=metadata,template='pedal-expansion')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['report','evaluation','corpus','out']:p.add_argument(n,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    build(json.loads(a.report.read_text(encoding='utf-8')),json.loads(a.evaluation.read_text(encoding='utf-8')),a.corpus,a.out)
