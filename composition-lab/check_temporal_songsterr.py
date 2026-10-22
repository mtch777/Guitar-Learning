"""Independent raw Songsterr measure geometry and temporal-score witnesses."""
from fractions import Fraction as F
import json
from check_reversible_source import source_expectation
from run_temporal_tonal_reference import compare_raw_scores


def check(capture,lower,upper):
    expected,_=source_expectation(capture);layout=source_expectation(capture,include_layout=True)
    parts=[json.loads(p.read_text(encoding='utf-8-sig')) for p in sorted(capture.glob('track-*.json'),key=lambda p:int(p.stem.split('-')[-1]))]
    geometry=lower['measure_geometry'];issues=[];signature=None;last=0
    if len(geometry['frames'])!=len(layout):issues.append('Source measure count differs')
    for ordinal,((start,span),row) in enumerate(zip(layout,geometry['frames']),1):
        signatures=[p['measures'][ordinal-1]['signature'] for p in parts if ordinal<=len(p.get('measures',[])) and p['measures'][ordinal-1].get('signature')]
        if signatures:signature=signatures[0];last=ordinal
        wanted=dict(id=f'measure:{ordinal}',ordinal=ordinal,label=str(ordinal),start_q=str(start),span_q=str(span),signature=signature,meter_source='explicit' if signatures else 'inherited',meter_source_frame=last)
        if row!=wanted:issues.append('Raw source frame/meter/provenance differs')
    memberships=[dict(part_id=p['partId'],frame_refs=[f'measure:{i+1}' for i in range(len(p.get('measures',[])))],source_pickup_declared=p.get('anacrusis')) for p in parts]
    if geometry['parts']!=memberships:issues.append('Source part/frame/pickup membership differs')
    # Source events come from independent raw JSON arithmetic, not Tier1.
    raw=[]
    for ident,event in expected.items():
        address=ident.split(':');raw.append((int(address[2]),int(address[3]),event['pitch'],event['onset_q'],event['duration_q']))
    temporal=compare_raw_scores(raw,upper)
    if temporal['status']!='PASS':issues.extend(temporal['issues'])
    return dict(status='FAIL' if issues else 'PASS',issues=issues[:20],raw_measure_frames=len(layout),temporal_oracle=temporal,
                scope='Actual source frame clocks/meter and published temporal arithmetic; not tonal accuracy')
