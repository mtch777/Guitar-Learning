"""Compare actual pretrained outputs with the existing V20 hypotheses.

Agreement is NOT accuracy. Global pitched context differs from a selected-track
V20 view. Collapse predictions by exact onset, not fragile per-note row identity.
"""
import argparse
from collections import Counter,defaultdict
from fractions import Fraction
import hashlib
import importlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from exact_score import extract_score
from source_ablations import checkpoint_models
from relational_graph import build_graph

QUALITY={'major triad':'major','minor triad':'minor','minor seventh chord':'minor7',
         'major seventh chord':'major7','dominant seventh chord':'dom7',
         'half-diminished seventh chord':'half_dim7','diminished seventh chord':'dim7',
         'diminished triad':'dim','augmented triad':'aug'}


def pitch_class(name):
    if not name or name[0] not in 'CDEFGAB':return None
    pc=dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[name[0]]
    for c in name[1:]:
        if c=='#':pc+=1
        elif c in ('b','-'):pc-=1
        else:return None
    return pc%12


def compare(source,xml,predictions,track,graph_out=None):
    import csv,numpy as np,partitura as pt
    array=pt.load_musicxml(str(xml)).note_array()
    rows=list(csv.DictReader(predictions.open(encoding='utf-8',newline='')))
    if len(array)!=len(rows):raise ValueError('Prediction count does not match inference input')
    groups=defaultdict(Counter)
    for row,note in zip(rows,array):
        # Upstream exports float32 beat coordinates as decimal CSV. Validate
        # that serialization precision, then use exact integer divisions below.
        if not np.isclose(float(row['onset']),float(note['onset_beat']),rtol=2e-7,atol=1e-6):
            raise ValueError('Prediction onset alignment mismatch')
        onset=Fraction(int(note['onset_div']),int(note['divs_pq']))
        groups[onset][(pitch_class(row['root']),QUALITY.get(row['quality'],row['quality']))]+=1
    checkpoint_models()  # Resolve checkpoint's absolute module imports.
    checkpoint=str(Path(__file__).resolve().parents[1]/'checkpoints/2026-10-14')
    sys.path.insert(0,checkpoint)
    try:joint=importlib.import_module('joint_interpretation_v20')
    finally:sys.path.remove(checkpoint)
    baseline=joint.interpret(extract_score(source),track)
    aligned=[];tied_votes=0
    for event in baseline:
        votes=groups.get(event['onset'])
        if not votes:continue
        ranked=votes.most_common()
        if len(ranked)>1 and ranked[0][1]==ranked[1][1]:tied_votes+=1;continue
        (root,quality),count=ranked[0];old=event['candidates'][0]
        aligned.append(dict(onset_q=str(event['onset']),gnn_root=root,gnn_quality=quality,
            vote_share=count/sum(votes.values()),v20_root=old['root'],v20_quality=old['quality'],
            root_agree=root==old['root'],quality_agree=quality==old['quality']))
    common=[e for e in aligned if e['v20_quality'] in set(QUALITY.values())]
    if graph_out:
        score=extract_score(source);members=defaultdict(list);head_votes=defaultdict(lambda:defaultdict(Counter))
        for t in score['tracks']:
            if t.get('is_percussion'):continue
            for mi,m in enumerate(t['measures']):
                for vi,v in enumerate(m['voices']):
                    for ei,e in enumerate(v):
                        for ni,n in enumerate(e['notes']): members[Fraction(e['onset_q'])].append(f't{t["index"]}:m{mi}:v{vi}:b{ei}:n{ni}')
        for row,note in zip(rows,array):
            onset=Fraction(int(note['onset_div']),int(note['divs_pq']))
            for head in ('root','quality','bass','inversion','phrase','section','tpc_in_label'):
                if head in row:head_votes[onset][head][row[head]]+=1
        hypotheses=[]
        for onset,heads in head_votes.items():
            for kind,keys in [('harmony',('root','quality','bass','inversion')),('phrase',('phrase','section'))]:
                hypotheses.append(dict(kind=kind,onset_q=str(onset),scope='onset point only; not an inferred span',
                    heads={k:dict(heads[k]) for k in keys if k in heads},confidence=None,
                    provenance='AnalysisGNN decoded note-row votes; uncalibrated, not truth',
                    prediction_sha256=hashlib.sha256(predictions.read_bytes()).hexdigest(),members=members[onset]))
        graph_out.parent.mkdir(parents=True,exist_ok=True)
        graph_out.write_text(json.dumps(build_graph(score,hypotheses)),encoding='utf-8')
    return dict(source=source.name,track=track,prediction_csv_sha256=hashlib.sha256(predictions.read_bytes()).hexdigest(),
        rows=len(rows),unique_model_onsets=len(groups),v20_onsets=len(baseline),compared_onsets=len(aligned),
        vote_ties_abstained=tied_votes,unmatched_v20_onsets=sum(e['onset'] not in groups for e in baseline),
        root_agreement=sum(e['root_agree'] for e in aligned)/len(aligned) if aligned else None,
        quality_agreement=sum(e['quality_agree'] for e in aligned)/len(aligned) if aligned else None,
        joint_agreement=sum(e['root_agree'] and e['quality_agree'] for e in aligned)/len(aligned) if aligned else None,
        v20_quality_distribution=dict(Counter(e['v20_quality'] for e in aligned)),
        mapped_common_quality_count=len(common),
        quality_agreement_mapped_common_vocabulary=sum(e['quality_agree'] for e in common)/len(common) if common else None,
        quality_distribution=dict(Counter(row['quality'] for row in rows)),
        accuracy_evaluated=False,aligned=aligned,
        limitations=['Agreement is not accuracy; no adjudicated harmonic labels',
          'AnalysisGNN sees global pitched context; V20 sees the explicitly selected track',
          'Same-onset majority aggregation can hide per-note disagreement; vote ties abstain',
          'Vocabularies differ; common-vocabulary metric covers only explicitly mapped shared qualities',
          'Full-source ties/grace and three stored-versus-sounding harmonic differences require separate interpretation'])


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('musicxml',type=Path)
    p.add_argument('predictions',type=Path);p.add_argument('--track',required=True,type=int);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--graph-out',type=Path)
    args=p.parse_args();report=compare(args.source,args.musicxml,args.predictions,args.track,args.graph_out)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='aligned'},indent=2))


if __name__=='__main__':main()
