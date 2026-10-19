"""Opt-in barline continuity research, with exact returns and literal locks.

Both frozen whole-piece candidates have mixed results; neither is a new default
or an accepted musical improvement. Written minima/roles are limited proxies.
"""
from copy import deepcopy
from fractions import Fraction as F
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
import json,math,random
from role_pitch_model import distribution
from role_pitch_transfer import locked_context,propose as reset_proposal
from corpus_composer import choose_family
from controlled_generation import position_chord
from generation_freedom import validate,mix,facets
from artist_profiles import stable_hash
from form_returns import plan_returns,apply as preserve_returns
from engine_contract import _read,sha
from technique_edits import transact
from gp_author import write_gp


def apply_register(probs,lowest,model):
    if model.get('schema')!='experimental-boundary-register-prior-v1' or model.get('alpha')!=.0001:
        raise ValueError('Fixed experimental register prior required')
    weighted=[p*(model['probabilities'].get(str(i-lowest),0)+model['alpha']) for i,p in enumerate(probs)]
    total=sum(weighted)
    if not math.isfinite(total) or total<=0:raise ValueError('Invalid register normalization')
    return [p/total for p in weighted]

def _propose(reference,roles,composer,pitch_model,sections,seed=17,carry=False,register_prior=None):
    context=locked_context(reference,roles)
    returns=plan_returns(reference,sections)
    return_map={r['start']+i:r['origin']+i for r in returns for i in range(r['length'])}
    section_for={s['start']+i:s['start'] for s in sections for i in range(s['length'])}
    if pitch_model.get('schema')!='written-role-pitch-mixture-v1' or pitch_model.get('source_composer_sha256')!=stable_hash(composer):raise ValueError('Exact source-composer provenance required')
    if composer['artist']!=pitch_model.get('artist'):raise ValueError('Artist model mismatch')
    if set(composer['training_songs'])!=set(pitch_model['training_songs']):
        # Pitch observations may omit songs with no usable melody/bass role.
        if not set(pitch_model['training_songs'])<=set(composer['training_songs']):raise ValueError('Training provenance mismatch')
    rng=random.Random(seed);out=deepcopy(context);harmony=[];cache={};decisions=[]
    for ti,t in enumerate(context['tracks']):
        if roles[ti]=='harmony':harmony.extend(e for m in t['measures'] for v in m['voices'] for e in v if e['notes'])
    # Supported harmony is one contiguous main voice. Index the exact clock once
    # instead of repeatedly reparsing every harmony event for every target note.
    harmony.sort(key=lambda e:F(e['onset_q']))
    starts=[F(e['onset_q']) for e in harmony];ends=[q+F(e['duration_q']) for q,e in zip(starts,harmony)]
    for ti,t in enumerate(out['tracks']):
        role=roles[ti]
        if role=='harmony':continue
        tuning=t['tunings'][0]
        last_pitch=None;last_fingering=();last_end=None;last_section=None
        for m in t['measures']:
            for vi,v in enumerate(m['voices']):
                section=section_for[m['number']-1]
                first=v[0] if v else None
                can_carry=(carry and role=='melody' and vi==0 and last_pitch is not None
                    and last_section==section and first is not None and bool(first['notes'])
                    and F(first['onset_q'])==F(m['onset_q'])==last_end)
                previous_pitch=last_pitch if can_carry else None
                previous_fingering=last_fingering if can_carry else ()
                previous_end=last_end if can_carry else None
                for ei,e in enumerate(v):
                    count=len(e['notes'])
                    if not count:previous_pitch=None;previous_end=None;continue
                    key=(role,count)
                    if key not in cache:
                        cache[key]={f:[p for p in records if any(len(x['intervals'])==count for x in p['events'])]
                            for f,records in composer['parts'][role].items()}
                        cache[key]={f:ps for f,ps in cache[key].items() if ps}
                    if not cache[key]:raise ValueError('No source voicing support for locked cardinality')
                    q=F(e['onset_q']);hi=bisect_right(starts,q)-1
                    anchor=min(n['midi'] for n in harmony[hi]['notes']) if hi>=0 and ends[hi]>q else None
                    conditioned_previous=previous_pitch;conditioned_end=previous_end
                    probs=distribution(pitch_model,role,previous_pitch,anchor)
                    register_applied=bool(register_prior is not None and can_carry and role=='melody' and ei==0)
                    if register_applied:probs=apply_register(probs,min(tuning),register_prior)
                    for retry in range(50):
                        p=choose_family(rng,cache[key]);intervals=rng.choice([x['intervals'] for x in p['events'] if len(x['intervals'])==count])
                        candidates={}
                        for root in range(max(0,min(tuning)),min(127,max(tuning)+24)+1):
                            pitches=[root+d for d in intervals]
                            if max(pitches)>127:continue
                            try:positions=position_chord(pitches,tuning,max_span=4,previous=previous_fingering)
                            except ValueError:continue
                            candidates[root]=[(pitch,s,f) for pitch,(s,f) in zip(pitches,positions)]
                        if candidates:break
                    else:raise ValueError('No playable source-supported voicing after bounded retries')
                    roots=sorted(candidates);root=rng.choices(roots,weights=[probs[p] for p in roots],k=1)[0]
                    e['notes']=[dict(midi=p,string=s,fret=f,tie=None,technique_tags=[]) for p,s,f in candidates[root]]
                    sampled_root=root
                    copied_from=return_map.get(m['number']-1) if role=='melody' else None
                    if copied_from is not None:
                        e['notes']=deepcopy(out['tracks'][ti]['measures'][copied_from]['voices'][vi][ei]['notes'])
                    root=min(n['midi'] for n in e['notes'])
                    previous_pitch=root;previous_fingering=[(n['string'],n['fret']) for n in e['notes']]
                    previous_end=q+F(e['duration_q'])
                    decisions.append(dict(track=ti,bar=m['number'],voice=vi,event=ei,anchor=anchor,root=root,sampled_root=sampled_root,register_factor_applied=register_applied,input_previous=conditioned_previous,input_previous_end=None if conditioned_end is None else str(conditioned_end),carried_at_bar_start=bool(can_carry and ei==0),section_instance=section,copied_from=copied_from,playable_roots=len(roots)))
                if vi==0:
                    last_pitch=previous_pitch;last_fingering=previous_fingering;last_end=previous_end;last_section=section
    validate(out)
    return out,decisions



def boundary_observations(composer,report):
    """Exact accepted barline joins; no inferred phrase or functional role labels."""
    from collections import Counter
    songs={s['song_id']:s for s in report['songs']}
    if len(songs)!=len(report['songs']):raise ValueError('Duplicate source song')
    index={role:defaultdict(list) for role in composer['parts']};events=[];excluded=Counter()
    for role,fs in composer['parts'].items():
        for family,records in fs.items():
            for p in records:index[role][p['song_id'],p['bar']].append((family,p))
    for role in ('melody','bass'):
        for (sid,bar),rs in sorted(index[role].items()):
            if (sid,bar-1) not in index[role]:excluded['no_previous_selected_role_bar']+=1;continue
            fam,p=min(rs,key=lambda v:v[1]['part_id']);_,prev=min(index[role][sid,bar-1],key=lambda v:v[1]['part_id'])
            if p['part_id']!=prev['part_id']:excluded['selected_part_changes']+=1;continue
            song=songs[sid];headers={h['bar']:h for h in song['shared_layout']}
            if len(headers)!=len(song['shared_layout']):raise ValueError('Duplicate source bar header')
            h0,h1=headers[bar-1],headers[bar];last,first=prev['root_events'][-1],p['root_events'][0]
            left,right=F(h0['start_q'])+F(last['local_q']),F(h1['start_q'])+F(first['local_q'])
            if left+F(last['duration_q'])!=right or right!=F(h1['start_q']) or left>=right:
                excluded['rest_gap_or_no_boundary_attack']+=1;continue
            ts=[t for t in song['tracks'] if t['part_id']==p['part_id']]
            if len(ts)!=1:raise ValueError('Ambiguous source track')
            a=[n for n in ts[0]['rows'] if n['voice']==0 and F(n['onset_q'])==left]
            b=[n for n in ts[0]['rows'] if n['voice']==0 and F(n['onset_q'])==right]
            if not a or not b or any(n['tie_destination'] or n['midi'] is None or n.get('raw_note',{}).get('dead') for n in a+b):
                excluded['unsupported_boundary_notes']+=1;continue
            sections={n['section_start'] for n in a+b}
            if len(sections)!=1 or None in sections:excluded['section_change_or_unknown']+=1;continue
            if min(n['midi'] for n in a)!=int(last['root']) or min(n['midi'] for n in b)!=int(first['root']):
                raise ValueError('Composer/accepted-analysis pitch join differs')
            anchor=None
            if index['harmony'][sid,bar]:
                _,h=min(index['harmony'][sid,bar],key=lambda v:v[1]['part_id']);q=F(first['local_q'])
                active=[e for e in h['root_events'] if F(e['local_q'])<=q<F(e['local_q'])+F(e['duration_q'])]
                if active:anchor=int(active[-1]['root'])
            events.append(dict(partition=song['provisional_partition'],role=role,song_id=sid,family=fam,part_id=p['part_id'],
                previous_bar=bar-1,bar=bar,previous_q=str(left),onset_q=str(right),previous=int(last['root']),target=int(first['root']),
                interval=int(first['root'])-int(last['root']),anchor=anchor,register=int(first['root'])-min(p['tuning'])))
    return dict(events=events,excluded=dict(excluded),source_composer_sha256=stable_hash(composer),
        limitations=['Written minima/main voice and heuristic roles; not phrase intent or functional harmony.',
                    'Source marks define known section instances; unknowns/gaps/part changes excluded.'])


def fit_register(rows,composer):
    if not rows or any(r['partition']!='development' or r['role']!='melody' for r in rows):
        raise ValueError('Nonempty development melody boundaries required')
    if any(r['song_id'] not in composer['training_songs'] for r in rows):raise ValueError('Outside source training cohort')
    groups=defaultdict(list)
    for r in rows:
        if type(r['register'])is not int:raise ValueError('Known integer written register required')
        groups[r['family'],r['song_id']].append(r['register'])
    fs=defaultdict(set)
    for family,song in groups:fs[family].add(song)
    table=defaultdict(float)
    for (family,song),values in groups.items():
        weight=1/len(fs)/len(fs[family])/len(values)
        for value in values:table[str(value)]+=weight
    return dict(schema='experimental-boundary-register-prior-v1',probabilities=dict(table),alpha=.0001,
        training_families=sorted(fs),training_songs=sorted({r['song_id'] for r in rows}),artist=composer['artist'],
        source_composer_sha256=stable_hash(composer),observations_sha256=stable_hash(rows),
        limitations=['Fixed soft boundary factor; no quotas, new style labels or musical acceptance.'])


def check_history(score,decisions,roles,sections):
    section_for={s['start']+i:s['start'] for s in sections for i in range(s['length'])};count=0
    for d in decisions:
        if roles[d['track']]!='melody':continue
        t=score['tracks'][d['track']];mi=d['bar']-1;vi=d['voice'];ei=d['event'];m=t['measures'][mi];e=m['voices'][vi][ei]
        prev=m['voices'][vi][ei-1] if ei else t['measures'][mi-1]['voices'][vi][-1] if mi else None
        same=bool(ei or mi and section_for[mi-1]==section_for[mi])
        eligible=bool(prev and prev['notes'] and same and F(prev['onset_q'])+F(prev['duration_q'])==F(e['onset_q']))
        expected=min(n['midi'] for n in prev['notes']) if eligible else None
        if d['input_previous']!=expected:raise AssertionError('Stale/incorrect actual preceding pitch')
        if ei==0 and d['carried_at_bar_start']!=eligible:raise AssertionError('Missed/invented carry')
        count+=d['carried_at_bar_start']
    return count


def apply(reference,roles,composer,pitch_model,sections,*,freedom=100,seed=17,mode='carry',register_model=None):
    if type(freedom)is not int or freedom not in (0,100):raise ValueError('Live-history pitch controls currently support literal0/unlocked100 only')
    if mode not in ('bar_reset','carry','register_carry') or type(seed)is not int:raise ValueError('Explicit supported mode/integer seed required')
    validate(reference)
    if freedom==0:return deepcopy(reference),dict(all_locked=True,decisions=[],carried_boundaries=0)
    if roles!=['harmony','melody','bass']:raise ValueError('Three explicit ordered roles required')
    if mode=='register_carry':
        if (register_model is None or register_model.get('artist')!=composer['artist']
            or register_model.get('source_composer_sha256')!=stable_hash(composer)
            or not set(register_model['training_songs'])<=set(composer['training_songs'])
            or not set(register_model['training_families'])<=set(pitch_model['training_families'])):
            raise ValueError('Exact source-register provenance required')
        probabilities=register_model['probabilities']
        if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in probabilities.values()) or abs(sum(probabilities.values())-1)>1e-9:
            raise ValueError('Normalized finite source register probabilities required')
    if mode=='bar_reset':proposal,decisions=reset_proposal(locked_context(reference,roles),roles,composer,pitch_model,seed)
    else:proposal,decisions=_propose(reference,roles,composer,pitch_model,sections,seed,True,register_model if mode=='register_carry' else None)
    score,_=mix(reference,proposal,{'melody':100},roles);final,return_audit=preserve_returns(score,sections,roles,{'melody':100})
    before,after=facets(reference,roles),facets(final,roles)
    for dimension in ('harmony','bass','rhythm','form','instrumentation','performance'):
        if before[dimension]!=after[dimension]:raise AssertionError('Locked '+dimension+' changed')
    count=0
    if mode!='bar_reset':
        if return_audit['changed_track_bars']:raise AssertionError('Late returns changed live-history notes')
        count=check_history(final,decisions,roles,sections)
    return final,dict(mode=mode,decisions=decisions,carried_boundaries=count,returns=return_audit,locked_facets_exact=True,
        musical_acceptance=False,limitations=['Both tested candidates have mixed outcomes; no new default.',
            'Only explicit plain generated cores, main voice and supplied section/return constraints.',
            'Literal GP data locks are not calibrated perceptual independence or functional melody locks.'])


def export(source,score,destination,roles):
    """Occurrence-only pitch properties; all source archive/other XML retained."""
    source,destination=Path(source),Path(destination);temp=destination.with_suffix('.proposal.gp')
    if destination.exists() or temp.exists() or destination.with_suffix('.expected.json').exists():raise FileExistsError('Fresh output and intermediates required')
    if roles!=['harmony','melody','bass']:raise ValueError('Explicit supported roles required')
    from compose_controlled import plain_core
    reference=json.loads(source.with_suffix('.expected.json').read_text(encoding='utf-8'))
    plain_core(source,reference)
    a,b=facets(reference,roles),facets(score,roles)
    if any(a[k]!=b[k] for k in ('harmony','bass','rhythm','form','instrumentation','performance')):
        raise ValueError('Export permits melody pitches only')
    _,_,_,before=_read(source)
    ids=[r['note']['note_id'] for r in before.values()]
    if len(set(ids))!=len(ids):raise ValueError('Shared note definitions require occurrence splitting')
    write_gp(score,temp);_,_,_,after=_read(temp)
    if set(before)!=set(after):raise ValueError('Occurrence topology changed')
    names={'Midi','String','Fret','ConcertPitch','TransposedPitch'};permissions={};edits={}
    for oid,row in after.items():
        if roles[int(oid.split(':')[0])]!='melody':continue
        key=('note',before[oid]['note']['note_id'],'property');permissions[key]=names
        edits[key]=[ET.tostring(p,encoding='unicode') for p in ET.fromstring(row['note']['note_xml']).findall('./Properties/Property') if p.get('name') in names]
    audit=transact(source,destination,edits,permissions)
    destination.with_suffix('.expected.json').write_text(json.dumps(score,separators=(',',':')),encoding='utf-8')
    return audit


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('observe')
    for name in ('composer','report','output'):q.add_argument(name,type=Path)
    q=sub.add_parser('fit-register')
    for name in ('observations','composer','output'):q.add_argument(name,type=Path)
    q=sub.add_parser('generate')
    for name in ('source','composer','pitch_model','sections','output'):q.add_argument(name,type=Path)
    q.add_argument('--mode',choices=('bar_reset','carry','register_carry'),default='carry')
    q.add_argument('--register-model',type=Path);q.add_argument('--seed',type=int,default=17)
    q.add_argument('--freedom',type=int,choices=(0,100),default=100)
    a=p.parse_args()
    if 'local-artifacts' not in a.output.resolve().parts:p.error('Private local-artifacts output required')
    targets=[a.output]
    if a.command=='generate':targets.extend(a.output.with_suffix(s) for s in ('.audit.json','.expected.json','.proposal.gp'))
    if any(t.exists() for t in targets):p.error('Fresh output and companion paths required')
    paths=[v for k,v in vars(a).items() if isinstance(v,Path) and k!='output']
    if a.command=='generate':paths.append(a.source.with_suffix('.expected.json'))
    seals={str(v):sha(v) for v in paths}
    read=lambda v:json.loads(v.read_text(encoding='utf-8-sig'))
    composer=read(a.composer)
    if a.command=='observe':result=boundary_observations(composer,read(a.report))
    elif a.command=='fit-register':
        data=read(a.observations)
        if data['source_composer_sha256']!=stable_hash(composer):raise ValueError('Observation source mismatch')
        result=fit_register([r for r in data['events'] if r['partition']=='development' and r['role']=='melody'],composer)
    else:
        ref=read(a.source.with_suffix('.expected.json'));roles=[t['name'] for t in ref['tracks']]
        from compose_controlled import plain_core
        plain_core(a.source,ref)
        score,result=apply(ref,roles,composer,read(a.pitch_model),read(a.sections),freedom=a.freedom,seed=a.seed,mode=a.mode,
            register_model=read(a.register_model) if a.register_model else None)
        if a.freedom==0:
            from shutil import copyfile
            copyfile(a.source,a.output)
            a.output.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8')
        else:result['export']=export(a.source,score,a.output,roles)
    if seals!={s:sha(s) for s in seals}:raise AssertionError('Inputs changed during execution')
    result['input_sha256']=seals
    target=a.output.with_suffix('.audit.json') if a.command=='generate' else a.output
    if target.exists():raise FileExistsError('Fresh audit required')
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(command=a.command,output=str(a.output),verified_inputs=len(seals),musical_acceptance=False)))


if __name__=='__main__':main()
