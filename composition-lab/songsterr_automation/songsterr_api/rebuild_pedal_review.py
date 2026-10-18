"""Recompute private review evidence from original rows, preserving prior media.

No case-specific detector rules or hand-assigned roles. Original review is never
modified. The listening scope is explicit, not asserted to be a phrase boundary.
"""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pedal_register import analyze_register
from pedal_evidence import analyze_evidence
from pedal_dialogue import describe


def events_for(rows,roles,kind,start,stop,chains):
    grouped=defaultdict(list)
    for n in rows:
        if n['tie_destination'] or roles.get(n['occurrence'])!=kind or not start<=F(n['onset_q'])<stop:continue
        q=F(n['onset_q']);end=F(chains.get(n['occurrence'],{}).get('end_q',q+F(n['duration_q'])))
        grouped[q].append(dict(occurrence=n['occurrence'],midi=n['midi'],duration_q=n['duration_q'],
            sustain_q=str(end-q),effects=sorted(n['effects'])))
    return [dict(onset_q=str(q),end_q=str(max(q+F(n['sustain_q']) for n in ns)),
                 notes=ns,pitches=sorted({n['midi'] for n in ns})) for q,ns in sorted(grouped.items())]


def rebuild(report,source,out,corpus_audit=False,evidence=False):
    out.mkdir(parents=True,exist_ok=False)
    songs={s['song_id']:s for s in report['songs']};cases=json.loads((source/'cases.json').read_text(encoding='utf-8'))
    records=[];result=[]
    analyze = analyze_evidence if evidence else analyze_register
    for case in cases:
        part=int(case['notes'][0]['id'].split(':')[0]);track=next(t for t in songs[case['song_id']]['tracks'] if t['part_id']==part)
        base,limit=F(case['base_q']),F(case['end_q'])
        rows=[n for n in track['rows'] if base<=F(n['onset_q'])<limit]
        prediction=analyze(rows);roles=prediction['roles']
        chains={c['origin']:c for c in track.get('sustain_relationships',{}).get('chains',[])}
        tie_roles={member:roles[c['origin']]+'_sustain' for c in chains.values() if c['origin'] in roles
                   for member in c['members'][1:] if roles[c['origin']]=='call'}
        revised=dict(case);revised['baseline_anchor']=case['anchor'];revised['baseline_category']=case['category']
        revised['anchor']=prediction['anchor_pitches'];revised['cycles']=[]
        revised['notes']=[dict(n,role=roles.get(n['id'],tie_roles.get(n['id'],'context'))) for n in case['notes']]
        revised['heading']='Following the repeating low part' if prediction['accepted'] else 'No repeated pedal exchange identified here'
        revised['category']='register_review' if prediction['accepted'] else 'outside_current_rule'
        revised['explanation']=('Gold marks the proposed pedal; blue marks answers that start later. '
            'A simultaneous upper note is not an answer. Different pedals need independent evidence.' if prediction['accepted'] else prediction['reason'])
        if not evidence and prediction['accepted']:
            revised['explanation']='Frozen register baseline: upper coattacks may be labeled as responses. Compare against the evidence method before interpreting these labels.'
        revised['caveat']='Unchanged source audio. This is a bounded excerpt, not a claimed phrase ending. These revised hypotheses need listening review.'
        for c in prediction['cycles']:
            start,answer,end=F(c['call_start_q']),F(c['response_start_q']),F(c['return_q'])
            calls=events_for(rows,roles,'call',start,answer,chains)
            replies=events_for(rows,roles,'response',start,end,chains)
            a,b=describe(calls,revised['anchor']),describe(replies,revised['anchor'])
            if not a or not b:raise ValueError('Cycle evidence missing')
            revised['cycles'].append(dict(call=a,response=b,call_members=[n['occurrence'] for e in calls for n in e['notes']],
                response_members=[n['occurrence'] for e in replies for n in e['notes']],
                response_to_call_span_ratio=str(F(b['span_q'])/F(a['span_q'])),
                call_sustain_into_response_q=str(max(F(0),F(a['end_q'])-F(b['start_q']))),
                call_to_response_gap_q=str(max(F(0),F(b['start_q'])-F(a['end_q']))),
                anchor_return_period_q=str(end-start),right_censored=False,closed_by_anchor_return=True))
        prefix=case.get('audio_prefix',case['id'])
        for filename in (case['id']+'.gp',prefix+'.context.wav',prefix+'.focused.wav'):
            shutil.copyfile(source/filename,out/filename)
            if hashlib.sha256((source/filename).read_bytes()).digest()!=hashlib.sha256((out/filename).read_bytes()).digest():raise ValueError('Media changed')
        if [dict(n,role=None) for n in case['notes']]!=[dict(n,role=None) for n in revised['notes']]:raise ValueError('Source note changed')
        result.append(revised)
        records.append(dict(id=case['id'],accepted=prediction['accepted'],anchor=prediction['anchor_pitches'],
            cycles=len(prediction['cycles']),attack_roles=len(roles),source_notes=len(case['notes'])))
    manifest=dict(cases=len(result),unavailable_categories=[],review_version='pedal-evidence-v1' if evidence else 'pedal-register-v1',
        algorithm_sha256=hashlib.sha256((Path(__file__).parents[2]/('pedal_evidence.py' if evidence else 'pedal_register.py')).read_bytes()).hexdigest(),
        dataset_sha256=hashlib.sha256(json.dumps(result,separators=(',',':')).encode()).hexdigest(),
        sampling='Same private passages and byte-identical audio; revised source-derived analysis, not new compositions.')
    (out/'cases.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for name in ('dialogue-explorer.html','dialogue-explorer.js'):
        shutil.copyfile(Path(__file__).parents[2]/name,out/('index.html' if name.endswith('.html') else name))
    validation=dict(cases=records,unchanged_source_and_media=True)
    if corpus_audit:
        counts=defaultdict(int);analyses=[]
        for song in report['songs']:
            for track in song['tracks']:
                if not track['guitar_or_bass'] or not track['temporal_relationships_eligible']:continue
                counts['tracks']+=1;sections=defaultdict(list)
                for n in track['rows']:sections[n['section_start']].append(n)
                for rows in sections.values():
                    p=analyze(rows);counts['source_scopes']+=1
                    counts['accepted_scopes']+=p['accepted'];counts['closed_exchanges']+=len(p['cycles'])
                    counts['assigned_attack_occurrences']+=len(p['roles'])
                    byid={n['occurrence']:n for n in rows}
                    if not set(p['roles'])<=byid.keys():raise ValueError('Invented source identity')
                    if any(byid[i]['tie_destination'] for i in p['roles']):raise ValueError('Tie counted as attack')
                    counts['audited_scopes']+=1
                    analyses.append(dict(song_id=song['song_id'],part_id=track['part_id'],
                        section_start=rows[0]['section_start'],accepted=p['accepted'],
                        anchor_pitches=p['anchor_pitches'],roles=p['roles'],cycles=p['cycles'],reason=p['reason']))
        validation['corpus']=dict(counts)
        (out/'corpus-analysis.json').write_text(json.dumps(analyses,separators=(',',':')),encoding='utf-8')
    (out/'verification.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print(json.dumps(validation))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path);p.add_argument('source',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--corpus-audit',action='store_true')
    p.add_argument('--evidence',action='store_true',help='Evaluate the corrected evidence method; baseline remains the default until acceptance')
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Source evidence stays private')
    rebuild(json.loads(a.report.read_text(encoding='utf-8')),a.source,a.out,a.corpus_audit,a.evidence)
