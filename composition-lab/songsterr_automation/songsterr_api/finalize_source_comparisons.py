"""Verify source-passage stimuli and build a private contextual review page."""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import html
import json
from pathlib import Path
import sys
import wave
from array import array
import math
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from exact_score import extract_score


def compare_audio(a,b):
    def read(path):
        with wave.open(str(path),'rb') as w:
            if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,44100):raise ValueError('Unexpected PCM format')
            return array('h',w.readframes(w.getnframes()))
    x,y=read(a),read(b)
    if len(x)!=len(y):raise ValueError('Paired audio durations differ')
    delta=math.sqrt(sum((p-q)**2 for p,q in zip(x,y))/len(x))/32768
    energy=math.sqrt(sum(p*p+q*q for p,q in zip(x,y))/(2*len(x)))/32768
    return dict(difference_rms=delta,relative_rms_difference=delta/energy if energy else None,
                differing_samples=sum(p!=q for p,q in zip(x,y)),frames=len(x))


def finalize(root,aggregate_path=None):
    data=json.loads((root/'comparisons.json').read_text(encoding='utf-8'))
    renders=json.loads((root/'render-jobs.results.json').read_text(encoding='utf-8'))
    study=[];results=[]
    labels=dict(brush_spread=('Brush spread','2× source GP stroke duration','8× source GP stroke duration'),
                bend_arrival=('Bend arrival timing','Earlier arrival','Later arrival'),
                whammy_arrival=('Whammy arrival timing','Earlier arrival','Later arrival'),
                whammy_transfer=('Source whammy curve in a new context','Earlier curve arrival','Later curve arrival'),
                tremolo_picking=('Tremolo picking rate','Eighth-note picking','Thirty-second-note picking'))
    for case in data['cases']:
        metrics={}
        for mode in ('context','focused'):
            pair=[r for r in renders if r['case_id']==case['id'] and r['mode']==mode]
            if len(pair)!=2:raise ValueError('Incomplete audio pair')
            for r in pair:
                if hashlib.sha256(Path(r['out']).read_bytes()).hexdigest()!=r['audio_sha256']:raise ValueError('Audio hash mismatch')
                if hashlib.sha256(Path(r['file']).read_bytes()).hexdigest()!=r['gp_sha256']:raise ValueError('GP hash mismatch')
            metrics[mode]=compare_audio(pair[0]['out'],pair[1]['out'])
            metrics[mode]['midi_events_differ']=pair[0]['midi_event_sha256']!=pair[1]['midi_event_sha256']
            if metrics[mode]['difference_rms']==0 or not metrics[mode]['midi_events_differ']:raise ValueError('Indistinguishable pair must not be presented: '+case['id'])
        if not case['zero_lock']['byte_identity'] or any(v['lock_audit']['byte_identity'] or not v['lock_audit']['locked_xml_verified'] for v in case['variants']):raise ValueError('Invalid source-control lock')
        score=extract_score(Path(case['variants'][0]['file']));track=score['tracks'][case['track_index']]
        measures=[m for m in track['measures'] if case['start_bar']<=m['number']<=case['end_bar']]
        origin=F(measures[0]['onset_q']);span=sum((F(m['time_signature'].split('/')[0])*4/F(m['time_signature'].split('/')[1]) for m in measures),F(0))
        notes=[]
        for m in measures:
            for voice in m['voices']:
                for e in voice:
                    for n in e['notes']:
                        if n['midi'] is not None:notes.append(dict(start=float(F(n['onset_q'])-origin),duration=float(F(n['duration_q'])),pitch=n['midi'],target=n['note_id']==case['changed_definition'] or e['beat_id']==case['changed_definition']))
        heading,left,right=labels[case['family']];variants=[]
        for i,v in enumerate(case['variants']):
            tracks=[r for r in renders if r['case_id']==case['id'] and r['method']==v['method']]
            variants.append(dict(label=(left,right)[i],gp=str(Path(v['file']).relative_to(root)).replace('\\','/'),
                                 context=str(Path(next(r for r in tracks if r['mode']=='context')['out']).relative_to(root)).replace('\\','/'),
                                 focused=str(Path(next(r for r in tracks if r['mode']=='focused')['out']).relative_to(root)).replace('\\','/'),
                                 target_seconds=tracks[0]['target_seconds']))
        fingerprint=hashlib.sha256(json.dumps(dict(source=case['source_sha256'],revision=case['revision_id'],media=[r['audio_sha256'] for r in renders if r['case_id']==case['id']]),sort_keys=True).encode()).hexdigest()[:20]
        study.append(dict(id=case['id'],fingerprint=fingerprint,revision_id=case['revision_id'],heading=heading,title=case['title'],track=case['track_name'].strip(),bars=[case['start_bar'],case['end_bar']],
                          target_bar=case['target_bar'],source_curve_origin_bar=case.get('source_curve_origin_bar'),variants=variants,notes=notes,span=float(span),locked=case['locked']))
        results.append(dict(family=case['family'],audio_comparison=metrics,zero_byte_lock=True,unrelated_xml_archive_locks=True))
    template=Path(__file__).parents[2]/'source_passage_review.html'
    payload=json.dumps(study,ensure_ascii=True).replace('<','\\u003c')
    (root/'index.html').write_text(template.read_text(encoding='utf-8-sig').replace('/*STUDY_DATA*/[]',payload),encoding='utf-8')
    public=dict(schema='source-passage-comparison-verification-v1',cases=len(study),variants=sum(len(s['variants']) for s in study),audio_clips=len(renders),
                results=results,missing_families=data['missing_families'],
                listening_judgment=None,limitations=['GM sampled previews, not physical guitar performance or Guitar Pro RSE',
                 'Edits compare reconstructed GP source passages, not learned generation or calibrated variation levers',
                 'Unchanged zero controls preserved privately and excluded from listening stimuli',
                 'Original whammy timing on tied/dead notes produced no verified difference; this study transfers its GP curve to a supported existing attack and labels the changed context explicitly'])
    (root/'verification.json').write_text(json.dumps(public,indent=2),encoding='utf-8')
    if aggregate_path:aggregate_path.write_text(json.dumps(public,indent=2),encoding='utf-8')
    return public


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--aggregate',type=Path);a=p.parse_args()
    if 'local-artifacts' not in a.directory.resolve().parts:p.error('Review source material must remain private')
    report=finalize(a.directory.resolve(),a.aggregate);print(json.dumps(dict(cases=report['cases'],audio_clips=report['audio_clips'],missing=report['missing_families'])))
