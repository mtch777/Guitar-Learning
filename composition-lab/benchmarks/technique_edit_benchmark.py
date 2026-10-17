"""Actual source GP technique edits; outputs/annotations stay private."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from exact_score import extract_score
from technique_analysis import analyze
from technique_effects import normalize_report
from technique_edits import generate_hopo,generate_vibrato,transact


def main():
    p=argparse.ArgumentParser();p.add_argument('sources',nargs='+',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);records=[];vibrato_proofs=[];zero_checks=0
    families=('hammer_on_fretted','pull_off_fretted','hammer_on_from_open','pull_off_to_open')
    for si,source in enumerate(a.sources):
        report=analyze(extract_score(source));base=a.out/f'source-{si+1}';base.mkdir()
        # Authorized hidden-annotation perturbation: remove HOPO markers, not notes.
        with zipfile.ZipFile(source) as z:root=ET.fromstring(z.read('Content/score.gpif'))
        perms={('note',n.get('id'),'property'):{'HopoOrigin','HopoDestination'} for n in root.findall('./Notes/Note')}
        hidden=base/'hidden-hopo.gp';transact(source,hidden,{k:[] for k in perms},perms)
        for family in families:
            tracks=[t for t in report['tracks'] if t['technique_scope']=='guitar_or_bass']
            def count(t):return sum(p['direction']+'_'+p['context']==family and p['fret_distance']<=5 for p in t['eligible_transitions'])
            track=max(tracks,key=count)
            for method in ('short_intervals','long_arrivals'):
                path=base/f'{family}-{method}.gp'
                audit=generate_hopo(source,path,track['index'],family,method=method)
                proof=base/f'proof-{family}-{method}.gp'
                second=generate_hopo(hidden,proof,track['index'],family,method=method)
                if audit['decisions']!=second['decisions']:raise AssertionError('Reference dependence')
                out=normalize_report(analyze(extract_score(path)));path.with_suffix('.analysis.json').write_text(json.dumps(out),encoding='utf-8')
                records.append(dict(source_sha256=report['source_sha256'],file=str(path),family=family,method=method,track=track['index'],
                                    selected=audit['selected'],eligible=audit['eligible'],locks=audit['locked_xml_verified'],reference_perturbation_pass=True))
            zero=base/f'zero-{family}.gp'
            if not generate_hopo(source,zero,track['index'],family,0)['byte_identity']:raise AssertionError('Zero identity')
            zero_checks+=1
        track=max(tracks,key=lambda t:t['attack_count'])
        for width in ('Slight','Wide'):
            path=base/f'vibrato-{width}.gp';audit=generate_vibrato(source,path,track['index'],width=width)
            path.with_suffix('.analysis.json').write_text(json.dumps(normalize_report(analyze(extract_score(path)))),encoding='utf-8')
            records.append(dict(source_sha256=report['source_sha256'],file=str(path),family='finger_vibrato',width=width,track=track['index'],selected=audit['selected'],locks=audit['locked_xml_verified']))
        proof=base/'proof-vibrato-Slight.gp';generate_vibrato(base/'vibrato-Wide.gp',proof,track['index'],width='Slight')
        def vibrato_tags(path):
            with zipfile.ZipFile(path) as z:node=ET.fromstring(z.read('Content/score.gpif'))
            return [(n.get('id'),n.findtext('Vibrato')) for n in node.findall('./Notes/Note')]
        if vibrato_tags(proof)!=vibrato_tags(base/'vibrato-Slight.gp'):raise AssertionError('Vibrato reference dependence')
        vibrato_proofs.append(dict(source_sha256=report['source_sha256'],reference_width_perturbation_pass=True))
        (a.out/'vibrato-proof.json').write_text(json.dumps(vibrato_proofs,indent=2))
        print(json.dumps(dict(source=source.name,cases=len(records),finished=True)),flush=True)
        (a.out/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    summary=dict(cases=len(records),all_locks=all(r['locks'] for r in records),
                 nonempty_cases=sum(r['selected']>0 for r in records),reference_perturbation_pass=all(r.get('reference_perturbation_pass',True) for r in records),
                 hopo_reference_perturbation_cases=sum('reference_perturbation_pass' in r for r in records),
                 vibrato_reference_perturbation_cases=len(vibrato_proofs),zero_source_checks=zero_checks,
                 limitations=['Independent import verification is a separate command','No human listening judgments','No claim of authentic legato from GM previews'])
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))


if __name__=='__main__':main()
