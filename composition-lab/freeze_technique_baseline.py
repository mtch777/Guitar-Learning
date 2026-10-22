"""Freeze retained source analysis BEFORE adapting it to complete Tier1.

Baseline reports are private comparators, never the new Tier2 representation.
"""
import argparse
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'songsterr_automation/songsterr_api'))
from analyze_relationships import track_analysis
from source_semantics import layout,timeline,playback_order
from pedal_evidence import analyze_evidence
from build_pedal_evidence_review import support_regions
from pedal_expansion import expand_phrases


def canonical(value):
    if isinstance(value,F):return str(value)
    if type(value) is dict:return {k:canonical(v) for k,v in value.items()}
    if type(value) in (list,tuple):return [canonical(v) for v in value]
    if type(value) in (set,frozenset):return sorted((canonical(v) for v in value),key=lambda v:json.dumps(v,sort_keys=True))
    if type(value) not in (str,int,float,bool,type(None)):raise ValueError('Unexpected retained analysis result type')
    return value


def retained(documents):
    """Unchanged functions + exact established pedal sequence, no source I/O."""
    meta=documents['metadata.json'];names=sorted((n for n in documents if n.startswith('track-')),key=lambda n:int(Path(n).stem.split('-')[-1]))
    parts=[documents[n] for n in names];headers,warnings=layout(parts)
    tracks=[]
    for i,part in enumerate(parts):
        identity=[]
        for field,expected in [('songId',meta['songId']),('revisionId',meta['revisionId']),('partId',int(Path(names[i]).stem.split('-')[-1]))]:
            if field in part and part[field]!=expected:identity.append(dict(reason='mismatched_'+field,expected=expected,observed=part[field]))
        catalog=meta.get('tracks') or []
        result=track_analysis(part,headers,catalog[i] if i<len(catalog) else None,identity,warnings)
        rows=result['rows'];sections=[];seeds=[]
        for section in sorted({n['section_start'] for n in rows}):
            subset=[n for n in rows if n['section_start']==section]
            if result['guitar_or_bass'] and result['temporal_relationships_eligible']:
                evidence=analyze_evidence(subset)
                if evidence['accepted']:
                    for j,region in enumerate(support_regions(evidence,rows,result['sustain_relationships']['chains'])):
                        seeds.append(dict(region,id=f'{section}:{j}',roles={k:v for k,v in evidence['roles'].items() if k in region['members']},members=sorted(region['members']),return_members=sorted(region['return_members'])))
                sections.append(dict(section_start=section,evidence=evidence))
            else:sections.append(dict(section_start=section,status='RETAINED_SOURCE_ELIGIBILITY_EXCLUSION'))
        snapshot=deepcopy(seeds)
        phrases=expand_phrases(rows,seeds,sustain_chains=result['sustain_relationships']['chains']) if seeds else []
        if seeds!=snapshot:raise ValueError('Approved seed mutation')
        tracks.append(dict(analysis=result,approved_pedal_sections=sections,approved_pedal_seeds=seeds,approved_pedal_phrases=phrases))
    return canonical(dict(headers=headers,layout_warnings=warnings,timeline=timeline(parts,headers),playback_order=playback_order(headers),tracks=tracks))


def run(captures,output):
    output.mkdir(parents=True,exist_ok=False)
    modules=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).suffix=='.py' and ROOT in Path(m.__file__).resolve().parents and 'local-artifacts' not in Path(m.__file__).parts}|{Path(__file__).resolve()})
    paths=modules+[p for capture in captures for p in capture.glob('*.json')]
    sealed=ROOT/'local-artifacts/pedal-expansion-v1/evaluation-sealed.json'
    if sealed.exists():paths.append(sealed)
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (output/'freeze.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    for path in modules:
        dest=output/'frozen-code'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
    records=[]
    for i,capture in enumerate(captures):
        documents={p.name:json.loads(p.read_text(encoding='utf-8-sig')) for p in capture.glob('*.json')}
        result=retained(documents);file=output/f'baseline-{i}.json';file.write_text(json.dumps(result,indent=2),encoding='utf-8')
        records.append(dict(capture=str(capture),file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),tracks=len(result['tracks'])))
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    report=dict(status='FROZEN_RETAINED_BASELINE' if unchanged else 'FAIL_CODE_OR_SOURCE_CHANGED',inputs=hashes,records=records,claim='Exact retained JSON-projected analysis baseline; not new integration acceptance')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(dict(status=report['status'],records=records)));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('captures',nargs='+',type=Path);args=parser.parse_args();run(args.captures,args.output)
