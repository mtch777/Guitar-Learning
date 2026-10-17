"""Atomic note/beat technique edits with fail-closed literal locks."""
from copy import deepcopy
from technique_strength import released
import hashlib
from pathlib import Path
import shutil
import zipfile
from xml.etree import ElementTree as ET


def strip(root,permissions):
    out=deepcopy(root)
    tables={'note':{n.get('id'):n for n in out.findall('./Notes/Note')},'beat':{n.get('id'):n for n in out.findall('./Beats/Beat')}}
    for (kind,ident,domain),names in permissions.items():
        node=tables[kind].get(ident)
        if node is None:raise ValueError('Unknown occurrence definition')
        container=node.find('Properties') if domain=='property' else node
        if container is None:continue
        for c in list(container):
            key=c.get('name') if domain=='property' else c.tag
            if key in names:container.remove(c)
        if domain=='property' and not len(container) and not container.attrib and not (container.text or '').strip():node.remove(container)
    return ET.tostring(out)


def transact(source,destination,edits,permissions):
    source,destination=Path(source),Path(destination)
    if destination.exists():raise FileExistsError(destination)
    for key,names in permissions.items():
        if len(key)!=3 or key[0] not in ('note','beat') or key[2] not in ('property','tag'):raise ValueError('Invalid permission domain')
        if not names or key[2]=='tag' and any(n in ('Properties','Notes','Rhythm','Tie') for n in names):raise ValueError('Structural edits prohibited')
    if set(edits)-set(permissions):raise ValueError('Undeclared edit')
    with zipfile.ZipFile(source) as src:
        original=ET.fromstring(src.read('Content/score.gpif'));root=deepcopy(original)
        tables={'note':{n.get('id'):n for n in root.findall('./Notes/Note')},'beat':{n.get('id'):n for n in root.findall('./Beats/Beat')}}
        for (kind,ident,domain),replacements in edits.items():
            names=permissions[kind,ident,domain]
            node=tables[kind].get(ident)
            if node is None:raise ValueError('Unknown occurrence definition')
            parsed=[ET.fromstring(x) for x in replacements]
            if any((p.tag!='Property' or p.get('name') not in names) if domain=='property' else p.tag not in names for p in parsed):raise ValueError('Locked field edit')
            container=node.find('Properties') if domain=='property' else node
            old=[] if container is None else [ET.tostring(c,encoding='unicode') for c in container if (c.get('name') if domain=='property' else c.tag) in names]
            if old==replacements:continue
            if container is None:container=ET.SubElement(node,'Properties')
            for c in list(container):
                if (c.get('name') if domain=='property' else c.tag) in names:container.remove(c)
            container.extend(parsed)
        if strip(original,permissions)!=strip(root,permissions):raise AssertionError('Locked score data changed')
        destination.parent.mkdir(parents=True,exist_ok=True)
        if ET.tostring(original)==ET.tostring(root):shutil.copyfile(source,destination)
        else:
            with zipfile.ZipFile(destination,'w') as dst:
                dst.comment=src.comment
                for entry in src.infolist():dst.writestr(entry,ET.tostring(root,encoding='utf-8',xml_declaration=True) if entry.filename=='Content/score.gpif' else src.read(entry.filename))
    with zipfile.ZipFile(source) as src,zipfile.ZipFile(destination) as dst:
        if src.namelist()!=dst.namelist() or src.comment!=dst.comment:raise AssertionError('Archive metadata changed')
        for name in src.namelist():
            if name!='Content/score.gpif' and src.read(name)!=dst.read(name):raise AssertionError('Locked archive member changed')
        if strip(original,permissions)!=strip(ET.fromstring(dst.read('Content/score.gpif')),permissions):raise AssertionError('Export lock violation')
    return dict(locked_xml_verified=True,archive_members_verified=True,byte_identity=source.read_bytes()==destination.read_bytes(),
                sha256=hashlib.sha256(destination.read_bytes()).hexdigest())


def enable_property(name):return f'<Property name="{name}"><Enable /></Property>'


def generate_hopo(source,destination,track_index,family,strength=100,method='short_intervals'):
    from technique_analysis import analyze
    from exact_score import extract_score
    from fractions import Fraction as F
    if family not in ('hammer_on_fretted','pull_off_fretted','hammer_on_from_open','pull_off_to_open'):raise ValueError('Unknown HOPO family')
    released('validation',strength)
    if method not in ('short_intervals','long_arrivals'):raise ValueError('Unknown HOPO method')
    if strength==0:
        return dict(**transact(source,destination,{},{}),family=family,strength=0,method=method,
                    eligible=None,selected=None,reference_annotations_used=True,decisions=[])
    score=extract_score(source);proposal_score=deepcopy(score)
    # Redact both valid and malformed original HOPO labels before analysis/selection.
    for t in proposal_score['tracks']:
        for m in t['measures']:
            for v in m['voices']:
                for e in v:
                    for n in e['notes']:
                        xml=ET.fromstring(n['note_xml']);props=xml.find('Properties')
                        if props is not None:
                            for p in list(props):
                                if p.get('name') in ('HopoOrigin','HopoDestination'):props.remove(p)
                        n['note_xml']=ET.tostring(xml,encoding='unicode')
                        n['property_names']=[p for p in n['property_names'] if p not in ('HopoOrigin','HopoDestination')]
    report=analyze(proposal_score)
    track=report['tracks'][track_index]
    if track['hopo_warnings'] or track['unresolved_ties']:raise ValueError('Resolve source relationships before editing')
    # Only non-reference observations reach selection; annotation_status/markers excluded.
    candidates=[{k:p[k] for k in ('origin','origin_terminal','destination','direction','context','fret_distance')} for p in track['eligible_transitions'] if p['direction']+'_'+p['context']==family]
    lookup={};counts={}
    for t in score['tracks']:
        for m in t['measures']:
            for vi,v in enumerate(m['voices']):
                for ei,e in enumerate(v):
                    for ni,n in enumerate(e['notes']):
                        ident=f"{t['index']}:{m['number']}:{vi}:{ei}:{ni}"
                        lookup[ident]=dict(note=n,event=e)
                        counts[n['note_id']]=counts.get(n['note_id'],0)+1
    decisions=[];permissions={};edits={}
    with zipfile.ZipFile(source) as z:root=ET.fromstring(z.read('Content/score.gpif'))
    existing={n.get('id'):n for n in root.findall('./Notes/Note')}
    for pair in candidates:
        a,b=lookup[pair['origin_terminal']],lookup[pair['destination']]
        selected=pair['fret_distance']<=5 and (pair['fret_distance']<=2 if method=='short_intervals' else F(b['note']['duration_q'])>=F(a['note']['duration_q']))
        for row,name in ((a,'HopoOrigin'),(b,'HopoDestination')):
            note=row['note'];nid=note['note_id']
            if counts[nid]!=1:raise ValueError('Shared note definition requires cloning')
            key=('note',nid,'property');permissions.setdefault(key,set()).add(name)
        decisions.append(dict(origin=pair['origin_terminal'],destination=pair['destination'],selected=selected))
    # Merge origin/destination permissions for notes participating in chains.
    enabled_by_id={}
    for p in decisions:
        if p['selected']:
            enabled_by_id.setdefault(lookup[p['origin']]['note']['note_id'],set()).add('HopoOrigin')
            enabled_by_id.setdefault(lookup[p['destination']]['note']['note_id'],set()).add('HopoDestination')
    for key,names in permissions.items():
        if strength==0:edits[key]=[ET.tostring(p,encoding='unicode') for p in existing[key[1]].findall('./Properties/Property') if p.get('name') in names]
        else:
            enabled=enabled_by_id.get(key[1],set())
            proposed={n:enable_property(n) for n in sorted(enabled&names)}
            original={p.get('name'):ET.tostring(p,encoding='unicode') for p in existing[key[1]].findall('./Properties/Property') if p.get('name') in names}
            # Release complete directed relationships, never isolated origin/destination flags.
            for pair in decisions:
                if not released(pair['origin']+'>'+pair['destination'],strength):
                    for occurrence,name in ((pair['origin'],'HopoOrigin'),(pair['destination'],'HopoDestination')):
                        if lookup[occurrence]['note']['note_id']==key[1] and name in names:
                            if name in original:proposed[name]=original[name]
                            else:proposed.pop(name,None)
            edits[key]=[proposed[n] for n in sorted(proposed)]
    for d in decisions:
        d['proposed_selected']=d['selected']
        d['reference_released']=released(d['origin']+'>'+d['destination'],strength)
        flags=[]
        for occurrence,name in ((d['origin'],'HopoOrigin'),(d['destination'],'HopoDestination')):
            nid=lookup[occurrence]['note']['note_id']
            flags.append(any(ET.fromstring(x).get('name')==name and ET.fromstring(x).find('Enable') is not None for x in edits['note',nid,'property']))
        d['selected']=all(flags)
    return dict(**transact(source,destination,edits,permissions),family=family,strength=strength,method=method,
                eligible=len(candidates),selected=sum(d['selected'] for d in decisions),reference_annotations_used=strength<100,
                freedom_semantics='Nested deterministic release of eligible relationships; not a difference quota',
                decisions=decisions,limitations=['Same-string existing-note articulation only','Fret-span rule is engineering eligibility, not certified physical playability','Neck position follows actual source frets; no universal higher-neck cutoff'])


def generate_vibrato(source,destination,track_index,strength=100,width='Slight'):
    from exact_score import extract_score
    from fractions import Fraction as F
    released('validation',strength)
    if width not in ('Slight','Wide'):raise ValueError('Unsupported GP vibrato width')
    if strength==0:return dict(**transact(source,destination,{},{}),selected=None,strength=0)
    score=extract_score(source);counts={};selected=[];permissions={};edits={}
    for t in score['tracks']:
        for m in t['measures']:
            for v in m['voices']:
                for e in v:
                    for n in e['notes']:counts[n['note_id']]=counts.get(n['note_id'],0)+1
    for m in score['tracks'][track_index]['measures']:
        for v in m['voices']:
            for e in v:
                for n in e['notes']:
                    if counts[n['note_id']]!=1:raise ValueError('Shared note definition')
                    key=('note',n['note_id'],'tag');permissions[key]={'Vibrato'}
                    eligible=n['fret'] is not None and n['fret']>0 and F(n['duration_q'])>=1 and len(e['notes'])==1 and 'HarmonicType' not in n['property_names']
                    if released(n['note_id'],strength):edits[key]=[f'<Vibrato>{width}</Vibrato>'] if eligible else []
                    else:edits[key]=[ET.tostring(x,encoding='unicode') for x in ET.fromstring(n['note_xml']).findall('Vibrato')]
                    if eligible:selected.append(n['note_id'])
    profile_path=Path(destination).with_suffix('.playback.json')
    if width=='Slight' and profile_path.exists():raise FileExistsError(profile_path)
    audit=transact(source,destination,edits,permissions)
    profile=dict(noteSlightLength=360,noteSlightAmplitude=.25) if width=='Slight' else None
    if profile is not None:
        import json
        profile_path.write_text(json.dumps(profile),encoding='utf-8')
    return dict(**audit,eligible=len(selected),selected=sum(bool(v) for v in edits.values()),strength=strength,width=width,
                preview_profile=profile,preview_profile_scope='External renderer setting; GP marker does not encode exact depth/rate',
                reference_annotations_used=strength<100,rate_hz=None,rate_provenance='GP marker contains strength only; playback-engine interpretation',
                limitations=['Fretted single-note segments of at least one quarter beat','No open-string finger vibrato','No certified physical performance or inferred source vibrato rate'])


if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--track',type=int,required=True);p.add_argument('--family',required=True)
    p.add_argument('--strength',type=int,choices=range(101),default=100);p.add_argument('--method',default='short_intervals');p.add_argument('--width',choices=('Slight','Wide'),default='Slight')
    a=p.parse_args()
    result=generate_vibrato(a.source,a.out,a.track,a.strength,a.width) if a.family=='finger_vibrato' else generate_hopo(a.source,a.out,a.track,a.family,a.strength,a.method)
    a.out.with_suffix('.edit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='decisions'}))
