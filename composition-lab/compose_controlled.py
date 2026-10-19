"""Compose supported controls on a plain generated core, with auditable stages.

This bounded integration deliberately rejects existing performed scores and
unsupported controls. Form, track count, tuning and event topology stay
fixed. It does not promise independent perceptual effects between dimensions.
"""
import argparse,hashlib,json,shutil,tempfile,zipfile
from pathlib import Path
from copy import deepcopy
from fractions import Fraction as F
from xml.etree import ElementTree as ET
from generation_freedom import validate,mix
from exact_score import extract_score
from rhythm_controls import apply as rhythm
from role_pitch_transfer import propose,locked_context
from profile_controls import propose as harmony_proposal,locked_context as harmony_context
from metadata_controls import apply as metadata
from learned_performance import apply as performance,FAMILIES
from palm_mute_method import apply as palm
from gp_author import write_gp
from technique_analysis import analyze,enabled
from bend_analysis import bend_shape
from form_returns import apply as preserve_returns,plan_returns,DIMENSIONS as RETURN_DIMENSIONS

CONTROLS=('harmony','melody','bass','rhythm','tempo','programs',*FAMILIES,'palm_mute')


def amounts(controls):
    if set(controls)-set(CONTROLS):raise ValueError('Unsupported controls: '+str(sorted(set(controls)-set(CONTROLS))))
    result={k:controls.get(k,0) for k in CONTROLS}
    if any(isinstance(v,bool) or not isinstance(v,int) or not 0<=v<=100 for v in result.values()):
        raise ValueError('Integer freedom0–100 required')
    return result


def plain_core(path,reference):
    validate(reference)
    if reference.get('source_file')!='development-only empirical corpus generation':
        raise ValueError('Plain empirical generated core required')
    score=extract_score(path)
    for t in score['tracks']:
        for m in t['measures']:
            for v in m['voices']:
                for e in v:
                    for n in e['notes']:
                        if n.get('tie') or n.get('grace_type') or set(n['property_names'])-{'Midi','String','Fret','ConcertPitch','TransposedPitch'} or set(n.get('technique_tags',[]))-{'InstrumentArticulation'}:
                            raise ValueError('Existing performance/unsupported notation cannot be reconstructed under a lock')
                        if ET.fromstring(n['note_xml']).findtext('InstrumentArticulation') not in (None,'0'):
                            raise ValueError('Nondefault articulation cannot be reconstructed')
    def identity(s):
        return [(t['program'],t['tunings'],[(F(m['onset_q']),m['time_signature'],[
            [(F(e['onset_q']),F(e['duration_q']),[(n['midi'],n['string'],n['fret']) for n in e['notes']]) for e in v]
            for v in m['voices']]) for m in t['measures']]) for t in s['tracks']]
    if identity(score)!=identity(reference):raise ValueError('GP and canonical core disagree')
    # Fail closed on beat effects, tempo maps, repeat layout or other metadata
    # omitted from the bounded canonical core, rather than silently erasing it.
    def canonical_gpif(p):
        with zipfile.ZipFile(p) as archive:
            names=archive.namelist()
            if len(names)!=len(set(names)):raise ValueError('Duplicate archive members')
            root=ET.fromstring(archive.read('Content/score.gpif'))
            members=tuple((name,archive.read(name)) for name in sorted(names) if name!='Content/score.gpif')
        summary=root.find('Score')
        if summary is not None:root.remove(summary)
        return members,ET.tostring(root,encoding='unicode')
    with tempfile.TemporaryDirectory() as tmp:
        expected=Path(tmp)/'expected.gp';write_gp(reference,expected)
        if canonical_gpif(path)!=canonical_gpif(expected):
            raise ValueError('GP contains data outside its plain canonical encoding')
    return score


def run(source,model_paths,controls,out,seed=17,artist=None,form_plan=None):
    controls=amounts(controls)
    if isinstance(seed,bool) or not isinstance(seed,int):raise ValueError('Integer seed required')
    if artist is not None and (not isinstance(artist,str) or not artist.strip()):raise ValueError('Nonempty artist required')
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    expected_hash=hashlib.sha256(source.with_suffix('.expected.json').read_bytes()).hexdigest()
    root=Path(__file__).parent
    paths=[*root.glob('*.py'),*(root/'songsterr_automation/songsterr_api').glob('*.py')]
    modules={str(p.relative_to(root)):p for p in paths if not p.name.startswith('test_')}
    code={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in modules.items()}
    reference=json.loads(source.with_suffix('.expected.json').read_text(encoding='utf-8'))
    plain_core(source,reference)
    roles=[t['name'] for t in reference['tracks']]
    if roles!=['harmony','melody','bass']:raise ValueError('Three explicit ordered roles required')
    sections=None;plan_hash=None
    if form_plan is not None:
        form_plan=Path(form_plan);raw=form_plan.read_bytes();sections=json.loads(raw);plan_hash=hashlib.sha256(raw).hexdigest()
        if plan_returns(reference,sections) and any(controls[d] not in (0,100) for d in RETURN_DIMENSIONS):
            raise ValueError('Explicit return preservation requires pitch/rhythm controls at0or100')
    required=set()
    if any(controls[k] for k in ('harmony','rhythm','melody','bass','tempo','programs')):required.add('composer')
    if controls['melody'] or controls['bass']:required.add('role_pitch')
    if any(controls[f] for f in FAMILIES):required.update(('performance','shapes'))
    if controls['palm_mute']:required.add('palm')
    if required-set(model_paths):raise ValueError('Missing required model paths: '+str(sorted(required-set(model_paths))))
    models={k:json.loads(Path(model_paths[k]).read_text(encoding='utf-8')) for k in required}
    hashes={k:hashlib.sha256(Path(model_paths[k]).read_bytes()).hexdigest() for k in required}
    inferred={models[k]['artist'] for k in ('composer','shapes') if k in models}
    if len(inferred)>1 or artist is not None and inferred and inferred!={artist}:raise ValueError('Artist model mismatch')
    artist=artist or next(iter(inferred),None)
    if controls['palm_mute'] and not artist:
        artists={t['artist'] for t in models['palm']['tables']}
        if len(artists)!=1:raise ValueError('Explicit artist required for multiartist palm model')
        artist=next(iter(artists))
    out.mkdir(parents=True,exist_ok=False)
    score=deepcopy(reference);stages=[]
    if controls['rhythm']:
        score,audit=rhythm(score,models['composer'],roles,controls['rhythm'],seed);stages.append(dict(stage='rhythm',audit=audit))
    if controls['harmony']:
        context=harmony_context(score);context['tracks']=[context['tracks'][0]]
        harmony=harmony_proposal(models['composer'],context,['harmony'],seed)
        proposal=deepcopy(score);proposal['tracks'][0]=harmony['tracks'][0]
        score,audit=mix(score,proposal,{'harmony':controls['harmony']},roles)
        stages.append(dict(stage='harmony',audit=audit))
    if controls['melody'] or controls['bass']:
        proposal,decisions=propose(locked_context(score,roles),roles,models['composer'],models['role_pitch'],seed)
        score,audit=mix(score,proposal,{k:controls[k] for k in ('melody','bass')},roles)
        stages.append(dict(stage='role_pitch',audit=audit,decisions=decisions))
    if controls['tempo'] or controls['programs']:
        score,audit=metadata(score,roles,models['composer'],{k:controls[k] for k in ('tempo','programs')},seed)
        stages.append(dict(stage='metadata',audit=audit))
    if sections is not None:
        score,audit=preserve_returns(score,sections,roles,controls)
        stages.append(dict(stage='form_returns',audit=audit))
    current=out/'01-core.gp'
    if score==reference:shutil.copyfile(source,current)
    else:write_gp(score,current,title='Controlled empirical composition')
    current.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8')
    if any(controls[f] for f in FAMILIES):
        target=out/'02-performance.gp'
        audit=performance(current,target,models['performance'],models['shapes'],artist,{f:controls[f] for f in FAMILIES},seed)
        stages.append(dict(stage='performance',audit=audit));current=target
    if controls['palm_mute']:
        target=out/'03-palm.gp';audit=palm(current,target,models['palm'],artist,controls['palm_mute'],seed)
        if current.with_suffix('.playback.json').exists():shutil.copyfile(current.with_suffix('.playback.json'),target.with_suffix('.playback.json'))
        stages.append(dict(stage='palm_mute',audit=audit));current=target
    final=out/'composition.gp';shutil.copyfile(current,final)
    if current.with_suffix('.playback.json').exists():shutil.copyfile(current.with_suffix('.playback.json'),final.with_suffix('.playback.json'))
    final.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8')
    actual=extract_score(final)
    final.with_suffix('.techniques.json').write_text(json.dumps(analyze(actual)),encoding='utf-8')
    curves=dict(tracks=[[[[[bend_shape(n['note_xml']) for n in e['notes']] for e in v] for v in m['voices']]
        for m in t['measures']] for t in actual['tracks']])
    final.with_suffix('.curves.json').write_text(json.dumps(curves),encoding='utf-8')
    flags={f'{ti}:{m["number"]}:{vi}:{ei}:{ni}':dict(palmMute=enabled(n['note_xml'],'PalmMuted'))
        for ti,t in enumerate(actual['tracks']) for m in t['measures'] for vi,v in enumerate(m['voices'])
        for ei,e in enumerate(v) for ni,n in enumerate(e['notes'])}
    final.with_suffix('.flags.json').write_text(json.dumps(flags),encoding='utf-8')
    if source_hash!=hashlib.sha256(source.read_bytes()).hexdigest() or expected_hash!=hashlib.sha256(source.with_suffix('.expected.json').read_bytes()).hexdigest():
        raise AssertionError('Input changed during composition')
    if hashes!={k:hashlib.sha256(Path(model_paths[k]).read_bytes()).hexdigest() for k in required}:raise AssertionError('Model changed during composition')
    if form_plan is not None and plan_hash!=hashlib.sha256(form_plan.read_bytes()).hexdigest():raise AssertionError('Form plan changed during composition')
    if code!={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in modules.items()}:raise AssertionError('Code changed during composition')
    result=dict(schema='controlled-empirical-pipeline-v1',controls=controls,seed=seed,stages=stages,
        source_sha256=source_hash,source_expected_sha256=expected_hash,form_plan_sha256=plan_hash,model_sha256=hashes,code_sha256=code,
        output_sha256=hashlib.sha256(final.read_bytes()).hexdigest(),artist=artist,
        byte_identity=final.read_bytes()==source.read_bytes(),all_zero_byte_identity=final.read_bytes()==source.read_bytes() if not any(controls.values()) else None,
        limitations=['Plain generated cores only; existing performance scores rejected.',
            'Bar count/section labels/tuning/track count/event topology fixed; unsupported controls fail.',
            'Thematic returns preserved only when an explicit form plan is supplied; labels alone do not preserve themes.',
            'Harmony means written track pitches/fingering; no inferred functional chord progression or emotional intent.',
            'Rhythm changes intertrack alignment and technique eligibility. Pitch changes eligibility too.',
            'Freedom releases decisions, not required difference or perceptual strength. Musical quality unverified.'])
    (out/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','config','out'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    config=json.loads(a.config.read_text(encoding='utf-8'))
    print(json.dumps(run(a.source,config.get('models',{}),config.get('controls',{}),a.out,config.get('seed',17),config.get('artist'),config.get('form_plan')),indent=2))
