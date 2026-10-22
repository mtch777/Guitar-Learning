"""Read-only joint-error accounting on frozen qualified reference artifacts.

No predictions are changed; no annotations enter the musical analysis.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path


def classify(key_predictions, chord_labels, reference_key, reference_chord,
             unsupported=False, no_evidence=False):
    if unsupported:
        return 'unsupported_vocabulary'
    keys = {tuple(k) for k in key_predictions}
    chords = {(c['root_pc'], tuple(c['formula'])) for c in chord_labels}
    if len(keys) != 1 or len(chords) != 1 or no_evidence:
        return 'ambiguous_or_unknown'
    key_ok = tuple(reference_key) in keys
    chord_ok = (reference_chord['reference_root_pc'], tuple(reference_chord['reference_formula'])) in chords
    return 'both_agree' if key_ok and chord_ok else 'chord_only_disagrees' if key_ok else 'key_only_disagrees' if chord_ok else 'both_disagree'


def account(temporal, harmonic_result, harmonic):
    frames = temporal['annotated_evaluation']['frames']
    gold = harmonic_result['annotated_evaluation']['reference_spans']
    cells = harmonic['all_optimal_path_cell_consensus']
    end = F(temporal['annotated_evaluation']['alignment']['source_end_q'])
    boundaries = {F(0), end}
    for frame in frames:
        for key in frame['reference_slices']:
            boundaries.update((F(key['start_q']), F(key['end_q'])))
    for row in gold+cells:
        boundaries.update((F(row['start_q']), F(row['end_q'])))
    if min(boundaries) != 0 or max(boundaries) != end:
        raise ValueError('Qualified common support differs')
    points = sorted(boundaries); rows = []
    for a, b in zip(points, points[1:]):
        keys = [(frame, key) for frame in frames for key in frame['reference_slices'] if F(key['start_q']) <= a < F(key['end_q'])]
        chords = [c for c in gold if F(c['start_q']) <= a < F(c['end_q'])]
        covering = [c for c in cells if F(c['start_q']) <= a < F(c['end_q'])]
        if len(keys) != 1 or len(chords) != 1 or len(covering) != 1:
            raise ValueError('Missing, overlapping or duplicated reference/model coverage')
        frame, key = keys[0]; chord, cell = chords[0], covering[0]
        reference_key = (key['reference_tonic_pc'], key['reference_mode'])
        states = {window: classify(frame['predictions'][window], cell['candidate_labels'], reference_key, chord, chord['outside_published_vocabulary'], cell['no_pitched_evidence_possibility']) for window in ('window0', 'window4')}
        rows.append(dict(start_q=str(a), end_q=str(b), frame_ref=frame['frame_ref'], reference_key=reference_key, reference_chord=chord, key_predictions={w:frame['predictions'][w] for w in states}, harmonic_labels=cell['candidate_labels'], no_pitched_evidence_possibility=cell['no_pitched_evidence_possibility'], outcomes=states))
    totals = {}
    for window in ('window0', 'window4'):
        counts = Counter()
        for row in rows:
            counts[row['outcomes'][window]] += F(row['end_q'])-F(row['start_q'])
        if sum(counts.values(), F(0)) != end:
            raise ValueError('Duration denominator lost')
        totals[window] = {k:str(v) for k,v in sorted(counts.items())}
    ceiling=F(0);within_frame=[]
    for frame in frames:
        durations=Counter()
        for key in frame['reference_slices']:
            durations[key['reference_tonic_pc'],key['reference_mode']]+=F(key['end_q'])-F(key['start_q'])
        ceiling+=max(durations.values())
        if len(durations)>1:within_frame.append(dict(frame_ref=frame['frame_ref'],reference_key_durations=[dict(tonic_pc=k[0],quality=k[1],duration_q=str(d)) for k,d in sorted(durations.items())]))
    return dict(common_support_q=str(end), duration_by_class=totals, intervals=rows,one_key_per_measure_oracle_ceiling_q=str(ceiling),unavoidable_key_disagreement_q=str(end-ceiling),multi_key_frames=within_frame,ceiling_claim='Reference-label representability only, not an achievable model accuracy or universal key truth')


def trace(row, window, upper, raw, source):
    from check_musicxml_context_source import raw_notes
    import xml.etree.ElementTree as ET
    import zipfile
    # Literal tie tags only: no inferred chain, attack, sustain or function.
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            container=ET.fromstring(archive.read('META-INF/container.xml'))
            name=next(x.attrib['full-path'] for x in container.iter() if x.tag.endswith('rootfile'))
            xml=ET.fromstring(archive.read(name))
    else:
        xml=ET.parse(source).getroot()
    tags=[dict(tie=[dict(t.attrib) for t in n.findall('tie')], tied=[dict(t.attrib) for t in n.findall('notations/tied')]) for p in xml.findall('part') for m in p.findall('measure') for n in m.findall('note') if n.find('pitch') is not None]
    literal,_=raw_notes(source)
    if len(tags)!=len(literal) or literal!=raw:
        raise ValueError('Literal tie-tag/source occurrence alignment differs')
    a,b=F(row['start_q']),F(row['end_q'])
    notes=[dict(part_id=p,bar=bar,pitch=pitch,onset_q=start,duration_q=duration,literal_tie_tags=tag) for (p,bar,pitch,start,duration),tag in zip(raw,tags) if F(start)<b and F(start)+F(duration)>a]
    scope=next(s for s in upper['temporal_tonal_evidence']['scopes'] if s['id']=='song-pooled')
    target=next(i for i,r in enumerate(scope['measures']) if r['frame_ref']==row['frame_ref'])
    tonic,quality=row['reference_key'];offset=tonic+(12 if quality=='minor' else 0)
    candidates=[c for c in scope['measures'][target]['candidates'] if c['raw_score'] is not None]
    # Explain the exact saved evaluator decision (including its tie tolerance),
    # never a subtly different exact-float winner reconstructed for display.
    saved_winners={tuple(k) for k in row['key_predictions'][window]}
    winners=[c for c in candidates if (c['tonic_pc'],c['quality']) in saved_winners]
    indices=sorted({offset}|{c['tonic_pc']+(12 if c['quality']=='minor' else 0) for c in winners})
    contributions=[]
    for i in indices:
        terms=[]
        for j,record in enumerate(scope['measures']):
            if abs(j-target)> (0 if window=='window0' else 4) or record['raw_scores'][i] is None:
                continue
            weight=1/(1+abs(j-target))
            terms.append(dict(frame_ref=record['frame_ref'],raw_score=record['raw_scores'][i],weight=weight,contribution=record['raw_scores'][i]*weight))
        expected=scope['measures'][target]['raw_scores' if window=='window0' else 'smoothed_scores'][i]
        if expected is not None and abs(sum(t['contribution'] for t in terms)-expected)>1e-12:
            raise ValueError('Trace contribution sum differs from frozen score')
        contributions.append(dict(tonic_pc=i%12,quality='minor' if i>=12 else 'major',score=expected,terms=terms))
    return dict(interval=row,window=window,actual_source_notes=notes,tonal_contributions=contributions,limits='Literal XML tie tags are inspection evidence only; current XML Tier1 does not own/reconstruct them. Scores show arithmetic attribution, not causal proof of true harmony.')


def run(temporal_dir,harmonic_dir,selection_path,alignment_path,output):
    from check_musicxml_context_source import raw_notes
    if output.exists():raise ValueError('Fresh diagnostic output required')
    selection=json.loads(selection_path.read_text(encoding='utf-8'));alignment=json.loads(alignment_path.read_text(encoding='utf-8'))
    paths=[Path(__file__),selection_path,alignment_path,Path(__file__).with_name('check_musicxml_context_source.py')];results=[];examples={}
    for item in selection['selected']:
        name=item['name'].split('.')[0]
        paths += [temporal_dir/name/'result.json',temporal_dir/name/'tier2-stripped.json',harmonic_dir/name/'result.json',harmonic_dir/name/'harmonic.json',Path(item['score'])]
    hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    for selected in selection['selected']:
        name=selected['name'].split('.')[0]
        inputs=[temporal_dir/name/'result.json',temporal_dir/name/'tier2-stripped.json',harmonic_dir/name/'result.json',harmonic_dir/name/'harmonic.json',Path(selected['score'])]
        temporal,upper,hresult,harmonic=[json.loads(p.read_text(encoding='utf-8')) for p in inputs[:4]]
        source=inputs[-1]
        if hashlib.sha256(source.read_bytes()).hexdigest()!=selected['score_sha256']:raise ValueError('Frozen source changed')
        qualified=next(r for r in alignment['references'] if r['reference']==selected['name'])
        if temporal['annotated_evaluation']['alignment']['annotation_to_source_pc_offset']!=qualified['annotation_to_source_pc_offset']:raise ValueError('Qualified edition alignment differs')
        result=account(temporal,hresult,harmonic);result['reference']=selected['name'];result['alignment_qualification']=qualified
        raw,_=raw_notes(source)
        for row in result['intervals']:
            for window,kind in row['outcomes'].items():
                key=(window,kind)
                rank=(F(row['start_q']),selected['name'])
                if key not in examples or rank<examples[key][0]:examples[key]=(rank,trace(row,window,upper,raw,source)|dict(reference=selected['name']))
        results.append(result)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=digest for p,digest in hashes.items()):raise ValueError('Diagnostic inputs/code changed while running')
    report=dict(status='PASS_COMPLETE_ACCOUNTING_NOT_ACCURACY',inputs=hashes,results=results,earliest_class_examples=[dict(category=k[1],**v[1]) for k,v in sorted(examples.items())],claims='Read-only diagnosis of qualified existing references; no model/parameter/inference changes, no new Gate1 selection or Gate2 rerun claimed')
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps([dict(reference=r['reference'],duration_by_class=r['duration_by_class']) for r in results],indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('temporal',type=Path);p.add_argument('harmonic',type=Path);p.add_argument('selection',type=Path);p.add_argument('alignment',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.temporal,a.harmonic,a.selection,a.alignment,a.output)
