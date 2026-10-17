"""Apply user corrections to the existing private probes; no new listening study."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
from exact_score import extract_score
from pattern_edits import generate
from build_technique_review import roll

LABELS={
 'short_intervals':'Short fret movements (up to 2 frets)',
 'long_arrivals':'Longer destination notes (up to 5 frets)',
 'compact':'Lower/compact voicings', 'upper':'Higher voicings',
}


def main():
    p=argparse.ArgumentParser();p.add_argument('previous',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    data=json.loads((a.previous/'cases.json').read_text());keys={k['id']:k for k in json.loads((a.previous/'review-key.json').read_text())}
    data['cases']=[g for g in data['cases'] if g['id'] not in ('hammer_on_fretted','pull_off_fretted')]
    source=a.previous/'diagnostic-reference.gp';corrections=[]
    for group in data['cases']:
        # Keep only full-freedom diagnostics; this exercise is retired, not expanded.
        pair=group['variants']['100'];group['variants']={'100':pair}
        family=group['id']
        if family=='finger_vibrato':
            pair[:]=[next(v for v in pair if keys[v['id']]['method']=='Slight')]
        for v in pair:
            method=keys[v['id']]['method'];dest=a.out/v['gp']
            if family=='close_interval_texture':
                generate(source,dest,0,family,method=method,pitch_unlocked=True,voicing_unlocked=True)
                restored=extract_score(dest)
                intervals=[abs(e['notes'][1]['midi']-e['notes'][0]['midi']) for m in restored['tracks'][0]['measures'] for e in m['voices'][0]]
                if set(intervals)!={1}:raise AssertionError('Close texture must be exactly one semitone')
                corrections.append(dict(family=family,method=method,events=len(intervals),semitones=1))
            else:shutil.copyfile(a.previous/v['gp'],dest)
            if family=='finger_vibrato':
                profile=dict(noteSlightLength=360,noteSlightAmplitude=.25)
                dest.with_suffix('.playback.json').write_text(json.dumps(profile))
                v['label']='Preferred speed, half the previous range'
                v['description']='Same cycle length as previous vibrato A (360 MIDI ticks); amplitude 0.25 instead of 0.5 semitones. This is an explicit preview setting; the GP Slight marker alone cannot encode that exact depth.'
                corrections.append(dict(family=family,**profile,previousAmplitude=.5))
            else:
                v['label']=LABELS[method]
                if family=='pedal_notes':v['label']='Five anchor attacks then three answers' if method=='compact' else 'Three anchor attacks then five answers'
                v['description']=('Existing notes involving open strings; technique marking/dynamics change, not a realistic legato sound model.' if family in ('hammer_on_from_open','pull_off_to_open') else 'Pitch and voicing construction on the same authored rhythm; not derived from an artist.' )
            v['notes']=roll(extract_score(dest))
        if family=='finger_vibrato':group['title']='Vibrato — corrected preferred setting'
        if family=='close_interval_texture':group['title']='Half-step texture — exactly 1 semitone'
    data['version']=hashlib.sha256(json.dumps(data['cases'],sort_keys=True).encode()).hexdigest()[:16]
    data['purpose']='Corrected engineering diagnostics only; previous blind listening study retired'
    data.pop('audio_gate',None)
    (a.out/'cases.json').write_text(json.dumps(data))
    (a.out/'corrections.json').write_text(json.dumps(corrections,indent=2))
    html=Path(__file__).with_name('technique_review.html').read_text(encoding='utf-8')
    html=html.replace('<title>Guitar technique controls</title>','<title>Corrected technique diagnostics</title>').replace('<h1>Guitar technique controls</h1>','<h1>Corrected technique diagnostics</h1>')
    html=html.replace('Compare two generated methods while other dimensions stay locked. These are short authored test phrases, not artist-style compositions. No original or no-technique baseline is offered.','This is the previous authored acoustic-guitar test pattern, corrected and labeled. It comes from none of your source songs. It tests code behavior, not musical style. The blind listening exercise is retired; no more ratings are requested here.')
    html=html.replace("h.textContent=v.label;", "h.textContent=v.label;const explanation=document.createElement('p');explanation.textContent=v.description||'';")
    html=html.replace('card.append(h,audio,canvas,bar)', 'card.append(h,explanation,audio,canvas,bar)')
    html=re.sub(r'<small>0%.*?</small>','<small>Methods are named explicitly below. This page is retained only to document the requested corrections.</small>',html)
    html=html.replace('let saved;',"document.querySelector('.questions').remove();document.querySelector('#download').hidden=true;document.querySelector('#strength').closest('label').hidden=true;let saved;")
    html=html.replace('Feedback saves in this browser for this bundle version. Download it when ready.','No further review is requested. Previous feedback is preserved separately.')
    html=html.replace('</style>','.pair:has(>.card:only-child){grid-template-columns:1fr}</style>').replace('switch A/B at the same timestamp','switch named methods at the same timestamp').replace("button.textContent='Switch to '+v.label+' here';","button.textContent=group.variants[strength.value].length===1?'Play corrected vibrato':'Switch to '+v.label;")
    (a.out/'index.html').write_text(html,encoding='utf-8');print(json.dumps(dict(groups=len(data['cases']),clips=sum(len(g['variants']['100']) for g in data['cases']),corrections=corrections)))


if __name__=='__main__':main()
