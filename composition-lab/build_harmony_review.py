"""Build a private, labelled two-version review; no source-song publication."""
import argparse,json,hashlib,shutil,wave
from pathlib import Path
from fractions import Fraction as F
from build_continuity_review import TEMPLATE
from playback_review import read_midi_notes
from compose_controlled import plain_core


def build(pair,output):
    pair,output=Path(pair),Path(output)
    if 'local-artifacts' not in output.resolve().parts:raise ValueError('Private output required')
    if output.exists():raise FileExistsError('Preserve existing review')
    cases=[]
    for method,stem in (('baseline','baseline'),('candidate','rejected-candidate')):
        gp=pair/(stem+'.gp');audio=pair/(stem+'.instrument.wav');score=json.loads(gp.with_suffix('.expected.json').read_text(encoding='utf-8'));plain_core(gp,score)
        meta=json.loads(Path(str(audio)+'.json').read_text(encoding='utf-8'))
        if hashlib.sha256(audio.read_bytes()).hexdigest()!=meta['audioSha256']:raise ValueError('Rendered audio changed')
        with wave.open(str(audio),'rb') as wav:seconds=wav.getnframes()/wav.getframerate()
        _,notes=read_midi_notes(gp.with_suffix('.mid'))
        cases.append(dict(core=1,method=method,gp='assets/'+gp.name,audio='assets/'+audio.name,seconds=seconds,notes=notes,
            bars=[dict(seconds=float(F(m['onset_q'])*60/F(score['tempo_bpm'])),number=m['number']) for m in score['tracks'][0]['measures']]))
    if cases[0]['seconds']!=cases[1]['seconds']:raise ValueError('Matched durations required')
    data=json.dumps(dict(cases=cases,version='current-harmony-review-v1'),separators=(',',':')).replace('<','\\u003c')
    s=TEMPLATE.replace('__DATA__',data)
    s=s.replace('Melody across bars — controlled comparison','Latest harmony experiment — where we are').replace('Does the melody connect across bars?','What changed in the latest experiment?')
    s=s.replace('Compare three versions of the same generated piece. Only melody pitches/fingering change; harmony, bass, rhythm, form, instruments and performance stay locked.','Compare two versions of the same generated piece. Only harmony pitches/fingering change. Melody, bass, rhythm, form, instruments and performance stay locked. Neither version is an original artist recording or a faithful recreation of a source song.')
    s=s.replace('<b>Research result: neither change passed the full gate.</b>','<b>Status: the new candidate was rejected. This is a diagnostic comparison.</b>')
    s=s.replace('Carry improved interval behavior but shifted register. Register carry corrected register but slightly worsened the written harmony-offset measurement. Existing defaults remain unchanged. Listening remains unjudged.','Harmony register moved closer to the measured source distribution, but melody–harmony alignment worsened and octave repairs increased (47 → 66). The candidate is not an accepted improvement. Most recent work concerns analysis and validation; it has no additional new audio yet. No listening judgment has been assigned.')
    s=s.replace("const labels={bar_reset:'Reset each bar',carry:'Carry previous melody',register_carry:'Carry + source register'};","const labels={baseline:'Earlier generated baseline',candidate:'New harmony — rejected experiment'};")
    start=s.index('const descriptions=');end=s.index('\nlet active=',start)
    s=s[:start]+"const descriptions={baseline:'Original generated arrangement: historical step sampler. This is our earlier generated output, not the original source song.',candidate:'Same piece, new source-conditioned harmony sampler with a mechanical feasibility filter. Harmony only changes; the melody and bass you hear are identical. Failed the frozen overall gate.'};"+s[end:]
    s=s.replace("choose(Number($('core').value),'bar_reset')","choose(Number($('core').value),'baseline')")
    s=s.replace('Melody connects across bars','Parts work together').replace('Register suits accompaniment','Harmony sits in a useful range').replace('Harmony fits','New harmony helps the piece')
    s=s.replace('<div class="box"><label>Generated piece','<div class="box"><b>Start here — about 2 minutes</b><p>Play the baseline for 20–30 seconds. Pause, choose “New harmony”, then play from the same time. Filter the roll to Harmony to see the changed part; audio still includes all parts. Repeat at a later section. Both full versions are 4½ minutes.</p></div><div class="box"><label>Generated piece')
    status='''<div class="box"><h2>Where the project stands</h2><p><b>Working:</b> source extraction, approved pedal identification, generated GP output and bounded controls.</p><p><b>Still unresolved:</b> convincing artist feel, musical development and how the parts move together. Aligned rhythms do not yet mean coordinated pitch movement.</p><p><b>Built, not yet generating:</b> a validator for exact inter-part interval-change locks and hidden targets. This comparison does not demonstrate that future feature.</p></div>'''
    s=s.replace('<div class="box"><h2>Optional notes for later review</h2>',status+'<div class="box"><h2>Optional notes for later review</h2>')
    output.mkdir();assets=output/'assets';assets.mkdir()
    for stem in ('baseline','rejected-candidate'):
        for suffix in ('.gp','.instrument.wav'):shutil.copy2(pair/(stem+suffix),assets/(stem+suffix))
    (output/'index.html').write_text(s,encoding='utf-8')
    return dict(output=str(output),cases=2,private=True,musical_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pair',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(build(a.pair,a.output)))
