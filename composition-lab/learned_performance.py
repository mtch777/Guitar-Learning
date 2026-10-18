"""Source-fitted performance proposals through verified GP property transactions.

Only notation-conditioned bend/vibrato and eligible open-string HOPO are edited.
The proposal never receives original technique annotations. Other score/archive
data remains locked. Learned annotation rates are not performed-technique truth.
"""
from collections import defaultdict,Counter
from copy import deepcopy
from fractions import Fraction as F
import hashlib,json,random,sys,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from artist_profiles import context,predict,connected_families,stable_hash
from exact_score import extract_score
from technique_analysis import analyze
from technique_edits import transact,enable_property
from technique_strength import released
from reference_levers import BEND_PROPERTIES
from contextual_bends import segment_properties
from contextual_bends import interpolate
from bend_analysis import bend_shape
sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
from source_semantics import curve

FAMILIES=('bend','finger_vibrato','hammer_on_from_open','pull_off_to_open')


def native_curve_exact(points,properties):
    """Lossless-only gate for GPIF encoding and alphaTab1.8.4 normalization.

    That reader discards interior points unless they rise above both endpoints.
    Verify equivalence, including delayed/early endpoints; never approximate.
    Independent real-reader checks are still required for exported batches.
    """
    encoded=bend_shape('<Note><Properties>'+''.join(properties)+'</Properties></Note>')
    if not encoded:return False
    written=[(F(p['offset_fraction']),F(p['semitones'])) for p in encoded['points']]
    native=written
    if len(written)>2 and max(y for x,y in written[1:-1])<=max(written[0][1],written[-1][1]):native=[written[0],written[-1]]
    positions={F(0),F(1)}|{x for x,y in points+written+native}
    return all(interpolate(points,x)==interpolate(written,x)==interpolate(native,x) for x in positions)


def learn_shapes(report,artist):
    families=connected_families(report['songs']);shapes=defaultdict(lambda:defaultdict(list));excluded=Counter()
    for song in report['songs']:
        if song.get('artist')!=artist or song['provisional_partition']!='development' or song.get('ai_generated') is not False or song.get('is_junk') is not False:continue
        for track in song['tracks']:
            if not track.get('guitar_or_bass') or not track.get('temporal_relationships_eligible'):continue
            for n in track['rows']:
                if n['tie_destination'] or not n.get('raw_note',{}).get('bend'):continue
                shape=curve(n['raw_note']['bend'],n['duration_q'])
                if not shape['valid'] or any(p['point_vibrato'] for p in shape['points']):excluded['unrepresentable_or_point_vibrato']+=1;continue
                points=[(F(p['offset_fraction']),F(p['semitones'])) for p in shape['points']]
                # alphaTab's GPIF reader quantizes displacement to half-semitone
                # units. Preserve exact source shapes or exclude; never silently
                # round a quarter-semitone gesture into a different performance.
                if any((y*2).denominator!=1 for x,y in points):excluded['native_reader_displacement_resolution']+=1;continue
                try:encoded=segment_properties(points,F(0),F(1))
                except ValueError:excluded['unrepresentable_gp_curve']+=1;continue
                if not encoded:excluded['zero_displacement_curve']+=1;continue
                if not native_curve_exact(points,encoded):excluded['native_reader_curve_normalization_or_gp_encoding']+=1;continue
                shapes[families[song['song_id']]][str(song['song_id'])].append(dict(points=[(str(x),str(y)) for x,y in points],properties=encoded))
    training=[s for s in report['songs'] if s.get('artist')==artist and s['provisional_partition']=='development' and s.get('ai_generated') is False and s.get('is_junk') is False]
    return dict(schema='training-bend-shapes-v1',artist=artist,training_songs=sorted(s['song_id'] for s in training),
        training_source_sha256=stable_hash([s for s in report['songs'] if s['provisional_partition']=='development' and s.get('ai_generated') is False and s.get('is_junk') is False]),
        training_sha256=stable_hash(training),families={f:dict(s) for f,s in shapes.items()},excluded=dict(excluded))


def apply(source,destination,model,shapes,artist,freedom,seed=17):
    if set(freedom)-set(FAMILIES):raise ValueError('Unsupported performance family')
    for value in freedom.values():
        if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=100:raise ValueError('Integer performance freedom 0–100 required')
    if not any(freedom.values()):return dict(**transact(source,destination,{},{}),all_locked=True)
    sidecar=Path(destination).with_suffix('.playback.json')
    if Path(destination).exists() or sidecar.exists():raise FileExistsError('Performance output or playback sidecar already exists')
    if model.get('schema')!='artist-performance-opportunity-v1':raise ValueError('Eligibility-conditioned performance model required')
    if shapes.get('schema')!='training-bend-shapes-v1' or shapes.get('artist')!=artist or not shapes.get('training_sha256'):
        raise ValueError('Verified same-artist training bend shapes required')
    if not model.get('training_source_sha256') or shapes.get('training_source_sha256')!=model['training_source_sha256']:raise ValueError('Bend shape training provenance differs from model')
    score=extract_score(source);redacted=deepcopy(score)
    # Both ends, including malformed labels, are hidden from pair eligibility.
    for t in redacted['tracks']:
        for m in t['measures']:
            for voice in m['voices']:
                for e in voice:
                    for n in e['notes']:
                        xml=ET.fromstring(n['note_xml']);props=xml.find('Properties')
                        if props is not None:
                            for p in list(props):
                                if p.get('name') in ('HopoOrigin','HopoDestination'):props.remove(p)
                        n['note_xml']=ET.tostring(xml,encoding='unicode')
                        n['property_names']=[p for p in n['property_names'] if p not in ('HopoOrigin','HopoDestination')]
    linked=analyze(redacted)
    with zipfile.ZipFile(source) as z:root=ET.fromstring(z.read('Content/score.gpif'))
    nodes={n.get('id'):n for n in root.findall('./Notes/Note')}
    counts=Counter(n['note_id'] for t in score['tracks'] for m in t['measures'] for v in m['voices'] for e in v for n in e['notes'])
    if any(v!=1 for v in counts.values()):raise ValueError('Shared source note definition requires occurrence cloning')
    permissions={};values={};decisions=[];lookup={};probabilities={};feature_support={}
    def natural(n):
        return n['midi'] is not None and not n.get('tie') and not n.get('grace_type') and not any(x in n['property_names'] for x in ('Muted','HarmonicType')) and 'Dead' not in n.get('technique_tags',[])
    for table in model['tables']:
        if table['artist']==artist and table['context']=='*':feature_support=table['features']
    def set_fields(nid,domain,names,replacement,do_release):
        key=('note',nid,domain);permissions.setdefault(key,set()).update(names)
        original=nodes[nid].find('Properties') if domain=='property' else nodes[nid]
        old={p.get('name') if domain=='property' else p.tag:ET.tostring(p,encoding='unicode') for p in list(original) if (p.get('name') if domain=='property' else p.tag) in names} if original is not None else {}
        chosen={}
        for xml in replacement:
            node=ET.fromstring(xml);chosen[node.get('name') if domain=='property' else node.tag]=xml
        for name in names:values.setdefault(key,{})[name]=(chosen if do_release else old).get(name)
    for ti,track in enumerate(score['tracks']):
        if not isinstance(track.get('program'),int) or not 24<=track['program']<=39:continue
        pitches=[n['midi'] for m in track['measures'] for v in m['voices'] for e in v for n in e['notes'] if n['midi'] is not None and not n.get('grace_type') and F(e['duration_q'])>0]
        register=(min(pitches),max(pitches)) if pitches else (None,None)
        attack_groups=defaultdict(list)
        for measure in track['measures']:
            for lane in measure['voices']:
                for event in lane:
                    for note in event['notes']:
                        if not note.get('grace_type') and F(event['duration_q'])>0 and not (note.get('tie') or {}).get('destination')=='true':
                            attack_groups[F(event['onset_q'])].append(dict(midi=note['midi'],fret=note['fret'],duration_q=event['duration_q'],bar_offset_q=event['local_onset_q']))
        for m in track['measures']:
            for vi,voice in enumerate(m['voices']):
                for ei,e in enumerate(voice):
                    notes=e['notes']
                    if not notes:continue
                    basic=attack_groups[F(e['onset_q'])]
                    if not basic:continue
                    probs,backoff=predict(model,dict(artist=artist,context=context(basic[0],basic,register)))
                    if probs is None:raise ValueError('Unknown artist model')
                    for ni,n in enumerate(notes):
                        if n.get('grace_type') or F(e['duration_q'])<=0:continue
                        occurrence=f'{ti}:{m["number"]}:{vi}:{ei}:{ni}';lookup[occurrence]=n;probabilities[occurrence]=probs
                        for family in ('bend','finger_vibrato'):
                            strength=freedom.get(family,0)
                            if not strength:continue
                            rng=random.Random(f'{seed}:{family}:{occurrence}')
                            probability=probs[family]
                            eligible=len(basic)==1 and n['fret'] is not None and n['fret']>0 and natural(n)
                            if not eligible:continue  # unsupported source techniques remain locked
                            selected=eligible and probability is not None and F(feature_support.get(family,'0'))>0 and rng.random()<probability
                            replacement=[]
                            if family=='bend' and selected:
                                fs=shapes['families']
                                if fs:
                                    f=rng.choice(sorted(fs));song=rng.choice(sorted(fs[f]));replacement=rng.choice(fs[f][song])['properties']
                                else:selected=False
                            elif family=='finger_vibrato' and selected:replacement=['<Vibrato>Slight</Vibrato>']
                            domain,names=('property',set(BEND_PROPERTIES)) if family=='bend' else ('tag',{'Vibrato'})
                            unlocked=released((family,occurrence),strength)
                            set_fields(n['note_id'],domain,names,replacement,unlocked)
                            decisions.append(dict(family=family,occurrence=occurrence,eligible=eligible,probability=probability,proposed_selected=bool(selected),released=unlocked,context_backoff=backoff))
    for ti,track in enumerate(linked['tracks']):
        grace_times={(vi,n['string'],F(e['onset_q'])) for m in score['tracks'][ti]['measures'] for vi,v in enumerate(m['voices']) for e in v for n in e['notes'] if n.get('grace_type')}
        for pair in track['eligible_transitions']:
            family=pair['direction']+'_'+pair['context'];strength=freedom.get(family,0)
            if not strength or family not in FAMILIES:continue
            origin=pair['origin_terminal'];dest=pair['destination']
            if origin not in lookup or dest not in lookup:continue
            if not natural(lookup[origin]) or not natural(lookup[dest]):continue
            landing=lookup[dest]
            if (int(dest.split(':')[2]),landing['string'],F(landing['onset_q'])) in grace_times:continue
            p=probabilities[origin][family];rng=random.Random(f'{seed}:{family}:{origin}>{dest}')
            selected=p is not None and F(feature_support.get(family,'0'))>0 and rng.random()<p
            unlocked=released((family,origin,dest),strength)
            for ident,name in ((origin,'HopoOrigin'),(dest,'HopoDestination')):
                set_fields(lookup[ident]['note_id'],'property',{name},[enable_property(name)] if selected else [],unlocked)
            decisions.append(dict(family=family,origin=origin,destination=dest,eligible=True,probability=p,proposed_selected=bool(selected),released=unlocked))
    edits={key:[xml for name,xml in sorted(v.items()) if xml is not None] for key,v in values.items()}
    audit=transact(source,destination,edits,permissions)
    if freedom.get('finger_vibrato'):
        with sidecar.open('x',encoding='utf-8') as handle:json.dump(dict(noteSlightLength=360,noteSlightAmplitude=.25),handle)
    return dict(**audit,freedom=freedom,seed=seed,decisions=decisions,
        limitations=['Source-annotation probabilities, not performed-technique truth.','Bend shapes from development families; qualitative vibrato uses user-approved preview settings, not inferred source oscillation.',
            'Only eligible open-string HOPO pairs; unrelated/fretted articulation remains locked.','Physical execution and musical quality require listening/performance evidence.'])
