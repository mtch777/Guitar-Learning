"""Private frozen annotated evaluation; annotations never enter Tier1/Tier2.

Published default windows 0/4, no fitting. Retains alignment/model failures.
"""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from music21 import corpus, converter
from music21.analysis import discrete
from musicxml_context_tier1 import extract
from check_musicxml_context_source import check, raw_notes
from musical_tier2 import analyze, strip_lower
from qa_isolation_harness import execute
from audit_tonal_reference_alignment import audit


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_scores(path,upper):
    raw,_=raw_notes(path)
    return compare_raw_scores(raw,upper)


def compare_raw_scores(raw,upper):
    issues=[];comparisons=0
    blocked={w['bar'] for category in ('layout_warnings','timing_warnings') for w in upper['source_quality'][category]}
    for scope in upper['temporal_tonal_evidence']['scopes']:
        hist=defaultdict(lambda:[F(0)]*12)
        for part,bar,pitch,onset,duration in raw:
            if scope['id']!='song-pooled' and scope['id']!=f'part:{part}':continue
            p,d=None if pitch is None else F(pitch),F(duration)
            if p is not None and F(p).denominator==1 and d>0 and bar not in blocked:hist[bar][int(F(p)%12)]+=d
        expected=[]
        for i,row in enumerate(scope['measures'],1):
            h=hist[i]
            if list(map(str,h))!=row['pitch_class_duration_q']:issues.append('XML duration histogram differs')
            method=discrete.AardenEssen()
            vector=None if len(set(h))==1 else sum((method._getDifference([0]*12,list(map(float,h)),q) for q in ('major','minor')),[])
            expected.append(vector)
            for k,value in enumerate(row['raw_scores']):
                wanted=None if vector is None else vector[k]
                if (value is None)!=(wanted is None) or (value is not None and abs(value-wanted)>1e-12):issues.append('Native AardenEssen raw correlation differs')
                comparisons+=1
        # Independent stateless sum: deliberately does not call core smoothing.
        for i,row in enumerate(scope['measures']):
            for k,value in enumerate(row['smoothed_scores']):
                wanted=None if expected[i] is None else sum(v[k]/(1+abs(i-j)) for j,v in enumerate(expected) if v is not None and abs(i-j)<=4)
                if (value is None)!=(wanted is None) or (value is not None and abs(value-wanted)>1e-12):issues.append('Immutable temporal sum differs')
                comparisons+=1
    return dict(status='FAIL' if issues else 'PASS',issues=issues[:20],score_comparisons=comparisons)


def winners(candidates,field):
    valid=[c for c in candidates if c[field] is not None]
    if not valid:return []
    best=max(c[field] for c in valid)
    return [(c['tonic_pc'],c['quality']) for c in valid if abs(c[field]-best)<1e-12]


def evaluate(annotation,upper,alignment):
    score=converter.parse(str(annotation))
    offset=alignment['annotation_to_source_pc_offset']
    if type(offset) is not int or not 0<=offset<12:raise ValueError('Typed audited reference coordinate offset required')
    gold=[(F(r.getOffsetInHierarchy(score)),((r.key.tonic.pitchClass+offset)%12,r.key.mode)) for r in score.recurse().getElementsByClass('RomanNumeral')]
    gold.sort(key=lambda r:r[0])
    frames=upper['measure_geometry']['frames'];end=F(frames[-1]['start_q'])+F(frames[-1]['duration_q'])
    annotation_end=F(score.highestTime)
    if not gold or gold[0][0]!=0 or str(end)!=alignment['common_support_end_q'] or annotation_end<end:raise ValueError(f'Gold/source audited clock mismatch: annotation={annotation_end}, source={end}')
    temporal=next(s for s in upper['temporal_tonal_evidence']['scopes'] if s['id']=='song-pooled')
    global_scope=next(s for s in upper['tonal_evidence']['scopes'] if s['id']=='song-pooled')
    totals={name:dict(correct=F(0),unknown=F(0),ambiguous=F(0),total=F(0)) for name in ('window0','window4','globalKrumhanslSchmuckler','globalTemperleyKostkaPayne')}
    rows=[]
    for frame,record in zip(frames,temporal['measures']):
        a=F(frame['start_q']);b=a+F(frame['duration_q']);predictions={f'window{w}':winners(record['candidates'],field) for w,field in ((0,'raw_score'),(4,'smoothed_score'))}
        for family in ('KrumhanslSchmuckler','TemperleyKostkaPayne'):predictions['global'+family]=winners([c for c in global_scope['candidates'] if c['family']==family],'score')
        slices=[]
        for j,(start,key) in enumerate(gold):
            stop=gold[j+1][0] if j+1<len(gold) else end
            duration=min(b,stop)-max(a,start)
            if duration<=0:continue
            slices.append(dict(start_q=str(max(a,start)),end_q=str(min(b,stop)),reference_tonic_pc=key[0],reference_mode=key[1]))
            for name,guess in predictions.items():
                t=totals[name];t['total']+=duration
                if not guess:t['unknown']+=duration
                elif len(guess)>1:t['ambiguous']+=duration
                elif guess[0]==key:t['correct']+=duration
        rows.append(dict(frame_ref=frame['id'],source_label=frame['label'],predictions=predictions,reference_slices=slices))
    metrics={name:dict(strict_unique_correct_q=str(v['correct']),unknown_q=str(v['unknown']),ambiguous_q=str(v['ambiguous']),evaluated_q=str(v['total']),strict_duration_accuracy=float(v['correct']/v['total'])) for name,v in totals.items()}
    transitions=[]
    for (a,old),(b,new) in zip(gold,gold[1:]):
        if old==new:continue
        frame=next(f for f in frames if F(f['start_q'])<=b<F(f['start_q'])+F(f['duration_q']))
        transitions.append(dict(at_q=str(b),from_key=old,to_key=new,enclosing_frame_ref=frame['id'],within_measure_change=b!=F(frame['start_q']),limitation='One hypothesis per written measure cannot express a mid-measure change'))
    return dict(metrics=metrics,frames=rows,reference_key_changes=transitions,alignment=dict(source_end_q=str(end),annotation_end_q=str(annotation_end),annotation_tail_excluded_q=str(annotation_end-end),annotation_to_source_pc_offset=offset,status='PASS_AUDITED_COMMON_SUPPORT'),claim='Agreement with these analysts local major/minor labels only; not universal key truth, artist style, chord function or emotion')


def run(selection,output,alignment_path=None):
    output.mkdir(parents=True,exist_ok=False)
    selected=json.loads(selection.read_text(encoding='utf-8'));results=[]
    code=Path(__file__).with_name('musical_tier2.py').read_text(encoding='utf-8')
    alignments=json.loads(alignment_path.read_text(encoding='utf-8')) if alignment_path else None
    freeze=dict(selection_sha256=sha(selection),alignment_sha256=sha(alignment_path) if alignment_path else None,code_sha256=sha(Path(__file__).with_name('musical_tier2.py')),adapter_sha256=sha(Path(__file__).with_name('musicxml_context_tier1.py')),runner_sha256=sha(__file__),windows=[0,4])
    (output/'freeze.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    for item in selected['selected']:
        case=output/item['name'].split('.')[0];case.mkdir();result=dict(reference=item['name'])
        try:
            source=Path(item['score']);annotation=Path(corpus.getWork('bach/choraleAnalyses/'+item['name']))
            if sha(source)!=item['score_sha256'] or sha(annotation)!=item['sha256']:raise ValueError('Frozen source/reference hash changed')
            lower=extract(source);result['source_oracle']=check(source,lower)
            if result['source_oracle']['status']!='PASS':raise ValueError('Independent source gate failed')
            upper=analyze(lower);blind=strip_lower(upper)
            (case/'tier1.json').write_text(json.dumps(lower,indent=2),encoding='utf-8')
            (case/'tier2-stripped.json').write_text(json.dumps(blind,indent=2),encoding='utf-8')
            result['isolated_inverse']=execute(code,blind,{'variation':0},lower,case/'inverse',timeout=120)
            result['independent_scores']=independent_scores(source,upper)
            result['reference_alignment_audit']=audit(source,annotation)
            result['evaluation_status']='WITHHELD_PENDING_AUDITED_REFERENCE_ALIGNMENT'
            if alignments is not None:
                alignment=next(r for r in alignments['references'] if r['reference']==item['name'])
                if alignment['source_sha256']!=sha(source) or alignment['annotation_sha256']!=sha(annotation) or result['reference_alignment_audit']['clock_status']!='PASS':raise ValueError('Reference alignment no longer matches audited source')
                result['annotated_evaluation']=evaluate(annotation,upper,alignment)
                result['evaluation_status']='EVALUATED_NOT_KEY_ACCURACY_ACCEPTANCE'
            result['status']='PASS' if all(result[k]['status']=='PASS' for k in ('source_oracle','isolated_inverse','independent_scores')) else 'FAIL'
        except Exception as exc:result.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
        (case/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');results.append(result)
    summary=dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',technical_results=results,reference_accuracy_is_not_a_pass_threshold=True)
    (output/'result.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps([dict(reference=r['reference'],status=r['status'],error=r.get('error'),metrics=r.get('annotated_evaluation',{}).get('metrics')) for r in results],indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('selection',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--alignment',type=Path);args=parser.parse_args()
    raise SystemExit(0 if run(args.selection,args.output,args.alignment)['status']=='PASS' else 1)
