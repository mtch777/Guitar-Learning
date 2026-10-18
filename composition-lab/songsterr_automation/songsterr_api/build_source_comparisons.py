"""Controlled edits of real reconstructed source scores; no authored phrases.

Zero controls are byte-identical and are not offered as listening stimuli.
Only selected technique properties/tags can change in each full GP archive.
"""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as E
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from exact_score import extract_score
from technique_edits import transact


def properties(xml):
    return {p.get('name'):p for p in E.fromstring(xml).findall('./Properties/Property')}


def replacements(xml,family,method):
    root=E.fromstring(xml);props=properties(xml)
    if family in ('whammy_arrival','whammy_transfer'):
        node=root.find('Whammy')
        if node is None or len({v for k,v in node.attrib.items() if k.endswith('Value')})<2:return None
        node=deepcopy(node)
        for name,value in list(node.attrib.items()):
            if 'Offset' in name:
                old=F(value);node.set(name,str(float(old*F(3,4) if method=='earlier_arrival' else 100-(100-old)*F(3,4))))
        return 'tag',{'Whammy'},[E.tostring(node,encoding='unicode')]
    if family=='bend_arrival':
        prefix='Bend' if family=='bend_arrival' else 'Whammy'
        names={k for k in props if k.startswith(prefix) and 'Offset' in k}
        values=[F(p.findtext('Float','0')) for k,p in props.items() if k.startswith(prefix) and k.endswith('Value')]
        if not names or len(set(values))<2:return None
        out=[]
        for name in sorted(names):
            node=deepcopy(props[name]);old=F(node.findtext('Float','0'))
            new=old*F(3,4) if method=='earlier_arrival' else 100-(100-old)*F(3,4)
            node.find('Float').text=str(float(new));out.append(E.tostring(node,encoding='unicode'))
        return 'property',names,out
    if family=='brush_spread':
        node=root.find("./XProperties/XProperty[@id='687935489']")
        if 'Brush' not in props or node is None or not node.findtext('Int'):return None
        node=deepcopy(node);old=int(node.findtext('Int'));node.find('Int').text=str(max(1,old*int(method)))
        return 'xproperty',{'687935489'},[E.tostring(node,encoding='unicode')]
    if family=='tremolo_picking':
        if root.find('Tremolo') is None:return None
        return 'tag',{'Tremolo'},[f'<Tremolo>{method}</Tremolo>']
    if family=='vibrato_width':
        if root.find('Vibrato') is None:return None
        return 'tag',{'Vibrato'},[f'<Vibrato>{method}</Vibrato>']
    raise ValueError(family)


FAMILIES=dict(bend_arrival=('note',('earlier_arrival','later_arrival')),
              whammy_transfer=('beat',('earlier_arrival','later_arrival')),
              brush_spread=('beat',('2','8')),
              tremolo_picking=('beat',('1/2','1/8')))


def build(root,out,max_per_family=1):
    cases=[];failures=[];done=Counter();jobs=[]
    for folder in sorted((root/'songs').iterdir()):
        if all(done[k]>=max_per_family for k in FAMILIES):break
        if not (folder/'score.gp').exists():continue
        meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8-sig'))
        validation=json.loads((folder/'gp7-validation.json').read_text(encoding='utf-8-sig'))
        if meta.get('aiGenerated') is not False or meta.get('isJunk') is not False or not validation.get('roundtripPass'):continue
        source=folder/'score.gp'
        score=extract_score(source);counts=Counter();beat_counts=Counter()
        for track in score['tracks']:
            for measure in track['measures']:
                for voice in measure['voices']:
                    for event in voice:
                        beat_counts[event['beat_id']]+=1
                        counts.update(n['note_id'] for n in event['notes'])
        for track in score['tracks']:
            ti=track['index'];catalog=(meta.get('tracks') or [])
            if not isinstance(track.get('program'),int) or not 24<=track['program']<=39:continue
            if ti<len(catalog) and (catalog[ti].get('isVocalTrack') or catalog[ti].get('isEmpty')):continue
            for family,(kind,methods) in FAMILIES.items():
                if done[family]>=max_per_family:continue
                chosen=None
                for measure in track['measures']:
                    for vi,voice in enumerate(measure['voices']):
                        for event in voice:
                            nodes=event['notes'] if kind=='note' else [event]
                            for node in nodes:
                                ident=node['note_id'] if kind=='note' else event['beat_id'];xml=node['note_xml'] if kind=='note' else event['beat_xml']
                                if (counts if kind=='note' else beat_counts)[ident]!=1:continue
                                proposal=replacements(xml,family,methods[0])
                                if proposal:
                                    if family in ('bend_arrival','whammy_arrival','tremolo_picking') and F(event['duration_q'])<1:continue
                                    if family in ('whammy_arrival','tremolo_picking') and not any((n.get('tie') or {}).get('destination')!='true' and 'Muted' not in n['property_names'] for n in event['notes']):continue
                                    if family=='bend_arrival':
                                        if (node.get('tie') or {}).get('destination')=='true' or any(k in node['property_names'] for k in ('HarmonicType','Muted')):continue
                                        vals=[F(p.findtext('Float','0')) for k,p in properties(xml).items() if k.startswith('Bend') and k.endswith('Value')]
                                        if not vals or max(vals)-min(vals)<50:continue
                                    chosen=(measure,event,node,ident,xml,proposal);break
                            if chosen:break
                        if chosen:break
                    if chosen:break
                if not chosen:continue
                source_curve_bar=None
                if family=='whammy_transfer':
                    source_curve_bar=chosen[0]['number'];targets=[]
                    for target_measure in track['measures']:
                        for target_voice in target_measure['voices']:
                            for target_event in target_voice:
                                if F(target_event['duration_q'])<1 or E.fromstring(target_event['beat_xml']).find('Whammy') is not None or beat_counts[target_event['beat_id']]!=1:continue
                                if not any((n.get('tie') or {}).get('destination')!='true' and not any(k in n['property_names'] for k in ('Muted','HarmonicType')) for n in target_event['notes']):continue
                                targets.append((abs(target_measure['number']-source_curve_bar),target_measure,target_event))
                    if not targets:continue
                    _,target_measure,target_event=min(targets,key=lambda x:x[0])
                    chosen=(target_measure,target_event,target_event,target_event['beat_id'],chosen[4],chosen[5])
                measure,event,node,ident,xml,proposal=chosen
                if family=='tremolo_picking':methods=tuple(x for x in ('1/2','1/4','1/8') if x!=E.fromstring(xml).findtext('Tremolo'))[:2]
                case_id=f'{family}-{done[family]+1}';case_dir=out/case_id;case_dir.mkdir(parents=True,exist_ok=False)
                permissions={(kind,ident,proposal[0]):proposal[1]}
                zero=case_dir/'zero-lock.gp';zero_audit=transact(source,zero,{},{});
                if not zero_audit['byte_identity']:raise AssertionError('Zero lock failed')
                variants=[];start=max(1,measure['number']-2);end=min(len(track['measures']),measure['number']+5)
                for method in methods:
                    domain,names,changes=replacements(xml,family,method)
                    destination=case_dir/(method.replace('/','-')+'.gp')
                    audit=transact(source,destination,{(kind,ident,domain):changes},permissions)
                    if audit['byte_identity']:raise AssertionError('Unchanged source must not be offered for listening')
                    variants.append(dict(method=method,file=str(destination.resolve()),lock_audit=audit))
                    for mode in ('context','focused'):
                        jobs.append(dict(case_id=case_id,method=method,mode=mode,file=str(destination.resolve()),
                                         track=ti,start_bar=start,end_bar=end,target_bar=measure['number'],target_offset_q=str(F(event['onset_q'])-F(measure['onset_q'])),out=str(destination.with_suffix('.'+mode+'.wav').resolve())))
                case=dict(id=case_id,family=family,title=meta['title'],artist=meta['artist'],song_id=meta['songId'],revision_id=meta['revisionId'],
                          track_index=ti,track_name=track['name'],source_curve_origin_bar=source_curve_bar,target_bar=measure['number'],start_bar=start,end_bar=end,
                          variants=variants,zero_lock=zero_audit,
                          original_technique_xml=xml,changed_definition=ident,source_gp=str(source.resolve()),
                          source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                          locked='All note pitches/frets/strings, written rhythm/voicings, form, tracks and other techniques; only the named technique field on one occurrence is released.',
                          comparison_semantics='Explicit source-technique experiment, not a calibrated 0..100 generation lever.',
                          limitations=['Reconstructed GP baseline; raw API remains authoritative','GM preview, not human guitar performance','No musical-quality/listening acceptance judgment'])
                cases.append(case);done[family]+=1
    result=dict(schema='real-source-technique-comparisons-v1',cases=cases,
                missing_families=[k for k in FAMILIES if not done[k]],candidate_errors=failures)
    (out/'comparisons.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'render-jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Source scores must remain private')
    a.out.mkdir(parents=True,exist_ok=False);report=build(a.corpus,a.out)
    print(json.dumps(dict(cases=len(report['cases']),missing=report['missing_families'])))
