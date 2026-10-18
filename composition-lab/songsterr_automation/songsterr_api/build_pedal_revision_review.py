"""Revised-anchor review: corrections plus new source families, private only."""
import argparse
from difflib import SequenceMatcher
import hashlib
from fractions import Fraction as F
import json
from pathlib import Path
import re
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pedal_regions import detect_regions
from build_pedal_identification_review import build
from upgrade_pedal_review import upgrade


def create(report,corpus,previous,out,fresh_only=False):
    out.mkdir(exist_ok=False)
    old=json.loads((previous/'cases.json').read_text(encoding='utf-8'))
    families=[s['candidate_work_family'] for s in report['songs'] if s['song_id'] in {c['song_id'] for c in old}]
    fresh_report=dict(report,songs=[s for s in report['songs'] if not any(SequenceMatcher(None,s['candidate_work_family'],f).ratio()>.86 for f in families)])
    staging=out/'sampling';build(fresh_report,corpus,staging)
    fresh=json.loads((staging/'cases.json').read_text(encoding='utf-8'))
    # Prefer both positive and rejected revised hypotheses when available.
    fresh.sort(key=lambda c:bool(detect_regions(c['notes'])))
    if fresh_only:
        # Include no-detection probes from different sections of two new songs.
        # They are unjudged probes, not asserted negative ground truth.
        for index in range(min(2,len(fresh))):
            original=fresh[index];song=next(s for s in report['songs'] if s['song_id']==original['song_id'])
            part=int(original['notes'][0]['occurrence'].split(':')[0])
            track=next(t for t in song['tracks'] if t['part_id']==part)
            for start in range(1,len(song['shared_layout'])-1):
                end=start+2
                if not (end<original['start_bar'] or start>original['end_bar']):continue
                if any(sum(v['bar']==b for v in song['playback']['order'])!=1 for b in range(start,end+1)):continue
                base=F(song['shared_layout'][start-1]['start_q']);limit=F(song['shared_layout'][end-1]['start_q'])+F(song['shared_layout'][end-1]['span_q'])
                notes=[n for n in track['rows'] if n['midi'] is not None and base<=F(n['onset_q'])<limit]
                if len(notes)<12 or len({n['midi'] for n in notes})<3 or detect_regions(notes):continue
                fresh[index]=dict(original,start_bar=start,end_bar=end,base_q=str(base),end_q=str(limit),notes=notes,no_detection_probe=True)
                break
    chosen=([(staging,c,'new_source') for c in fresh] if fresh_only else
            [(previous,c,'previously_reviewed') for c in old]+[(staging,c,'new_source') for c in fresh[:3]])
    source_pages={root:(root/'index.before-note-annotation.html').read_text(encoding='utf-8') for root in (previous,staging)}
    articles=[];cases=[];jobs=[]
    for i,(root,original,cohort) in enumerate(chosen,1):
        case=dict(original);old_id=case['id'];ident=f'case-{i:02d}';case['id']=ident;case['cohort']=cohort
        predictions=detect_regions(case['notes']);targets={n for p in predictions for n in p['anchor_occurrences']}
        case['target_ids']=sorted(targets);case['revised_regions']=predictions
        source=root/(old_id+'.gp');shutil.copyfile(source,out/(ident+'.gp'))
        article=re.search(r'<article data-id="'+re.escape(old_id)+r'">.*?</article>',source_pages[root],re.S)[0].replace(old_id,ident)
        if case.get('no_detection_probe'):
            notes=case['notes'];high=max(n['midi'] for n in notes);low=min(n['midi'] for n in notes);base=F(case['base_q']);span=F(case['end_q'])-base
            rectangles=''.join(f'<rect x="{float((F(n["onset_q"])-base)/span*960)}" y="{(high-n["midi"])*7+5}" width="{max(1,float(min(F(n["duration_q"]),F(case["end_q"])-F(n["onset_q"]))/span*960))}" height="6" fill="#69a7c7"/>' for n in notes)
            article=re.sub(r'<svg\b.*?</svg>',f'<svg role="img" aria-label="Source track notes" viewBox="0 0 960 {(high-low+1)*7+10}">{rectangles}</svg>',article,flags=re.S)
            article=re.sub(r'source bars \d+–\d+',f'source bars {case["start_bar"]}–{case["end_bar"]}',article)
        iterator=iter(case['notes'])
        def color(match):
            note=next(iterator);return re.sub(r'fill="[^"]+"','fill="'+('#f6c85f' if note['occurrence'] in targets else '#69a7c7')+'"',match[0])
        article=re.sub(r'<rect\b[^>]*?/>',color,article)
        articles.append(article);cases.append(case)
        for mode in ('context','focused'):
            wave=root/(old_id+'.'+mode+'.wav')
            if wave.exists():shutil.copyfile(wave,out/(ident+'.'+mode+'.wav'))
            else:
                job=next(j for j in json.loads((root/'render-jobs.json').read_text(encoding='utf-8')) if j['case_id']==old_id and j['mode']==mode)
                jobs.append(dict(job,case_id=ident,file=str((out/(ident+'.gp')).resolve()),out=str((out/(ident+'.'+mode+'.wav')).resolve()),
                                 start_bar=case['start_bar'],end_bar=case['end_bar'],target_bar=case['start_bar'],target_offset_q='0'))
    fingerprint=hashlib.sha256(json.dumps([(c['source_sha256'],c['target_ids']) for c in cases]).encode()).hexdigest()[:16]
    prefix=source_pages[previous].split('<article')[0]
    study_prefix='pedal-fresh-' if fresh_only else 'pedal-revision-'
    page=prefix+''.join(articles)+"<script>const key='"+study_prefix+fingerprint+"';</script></html>"
    (out/'index.html').write_text(page,encoding='utf-8');(out/'cases.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
    (out/'render-jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8');upgrade(out,report)
    page=(out/'index.html').read_text(encoding='utf-8')
    page=page.replace('This checks analysis of six actual source passages. Nothing was composed, edited or varied. It does not ask which version sounds better.',
        ('Six new song families, excluded from the earlier studies. Detector results were frozen before your review. Mark what you hear, then reveal our detection.' if fresh_only else
         'Updated analysis of unchanged source music: six earlier passages and three new song families. First mark what you hear, then reveal our detection. Earlier feedback is preserved separately.'))
    page=page.replace('Gold marks the note the script identified as a repeating anchor; blue shows the surrounding notes on this track.',
        'Mark the note or interval that keeps returning while other notes provide contrast. You can mark several notes together. Use the selected-track audio if the full mix is hard to follow.')
    page=page.replace('Does the gold note act as a repeating anchor while the other notes provide contrast?',
        'Is there a repeating pedal anchor in this passage?')
    extra='''<p>How complete are your pink markings?</p><select class="marking-coverage" aria-label="Completeness of your markings"><option value="">Not specified</option><option value="examples">Some examples only</option><option value="all">All anchor notes in this excerpt</option><option value="none">There are no pedal anchors here</option></select>
<p><button class="reveal" type="button">Reveal the detector’s highlights</button></p>
<div class="after-reveal"><p>Gold fill or outline shows the revised detection; pink remains yours.</p>
<p>Did it choose the right note or interval?</p><select class="anchor-identity" aria-label="Detected anchor identity"><option value="">Not reviewed</option><option>Yes</option><option>Partly</option><option>No</option><option>Unclear</option></select>
<p>Did it mark the right extent of the pattern?</p><select class="anchor-extent" aria-label="Detected pattern extent"><option value="">Not reviewed</option><option>Complete</option><option>Missing anchor notes</option><option>Includes unrelated notes</option><option>Both missing and unrelated notes</option><option>Unclear</option></select></div>'''
    for case in cases:
        page=page.replace(f'<article data-id="{case["id"]}">',f'<article data-id="{case["id"]}" data-cohort="{case["cohort"]}">')
    page=page.replace('<p>Optional: where does that description stop fitting?</p>',extra+'<p>Optional: what did we miss?</p>')
    for case in cases:
        summary=(f'Detector marked {len(case["target_ids"])} anchor notes.' if case['target_ids'] else
                 'Detector found no repeating anchor here. If you hear one, mark it in pink.')
        pattern=r'(<article data-id="'+re.escape(case['id'])+r'".*?)(</article>)'
        page=re.sub(pattern,lambda m:m[1].replace('<div class="after-reveal">','<div class="after-reveal"><p><b>'+summary+'</b></p>')+m[2],page,flags=re.S)
    page=page.replace('</style>','article:not(.revealed) .source-note:not(.selected){fill:#69a7c7}article:not(.revealed) .after-reveal{display:none}</style>')
    page=page.replace('fill="#f6c85f"','fill="#f6c85f" data-detected="true"')
    page=page.replace('</style>','article.revealed .source-note[data-detected="true"]:not(.sounding){stroke:#f6c85f;stroke-width:2}</style>')
    cards=re.findall(r'<article\b.*?</article>',page,re.S)
    start=page.index('<article');end=page.rindex('</article>')+len('</article>')
    page=page[:start]+(''.join(cards) if fresh_only else '<h2>New source passages — start here</h2>'+''.join(cards[6:])+'<h2>Earlier passages — check the corrections</h2>'+''.join(cards[:6]))+page[end:]
    (out/'index.html').write_text(page,encoding='utf-8')
    manifest=dict(cases=len(cases),new_source_cases=len(cases) if fresh_only else 3,new_render_jobs=len(jobs),study=study_prefix+fingerprint,
                  detector_sha256=hashlib.sha256((Path(__file__).parents[2]/'pedal_regions.py').read_bytes()).hexdigest(),
                  excluded_prior_song_ids=[c['song_id'] for c in old],
                  selected_source_ids=[c['song_id'] for c in cases],
                  source_family_filter='exclude similarity > .86 to any earlier family; selective sample, not population accuracy')
    (out/'frozen-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);p.add_argument('corpus',type=Path);p.add_argument('previous',type=Path);p.add_argument('out',type=Path);p.add_argument('--fresh-only',action='store_true');a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Source review stays private')
    print(json.dumps(create(json.loads(a.report.read_text(encoding='utf-8')),a.corpus,a.previous,a.out,a.fresh_only)))
