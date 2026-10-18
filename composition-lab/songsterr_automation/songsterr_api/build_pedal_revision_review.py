"""Revised-anchor review: corrections plus new source families, private only."""
import argparse
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pedal_regions import detect_regions
from build_pedal_identification_review import build
from upgrade_pedal_review import upgrade


def create(report,corpus,previous,out):
    out.mkdir(exist_ok=False)
    old=json.loads((previous/'cases.json').read_text(encoding='utf-8'))
    families=[s['candidate_work_family'] for s in report['songs'] if s['song_id'] in {c['song_id'] for c in old}]
    fresh_report=dict(report,songs=[s for s in report['songs'] if not any(SequenceMatcher(None,s['candidate_work_family'],f).ratio()>.86 for f in families)])
    staging=out/'sampling';build(fresh_report,corpus,staging)
    fresh=json.loads((staging/'cases.json').read_text(encoding='utf-8'))
    # Prefer both positive and rejected revised hypotheses when available.
    fresh.sort(key=lambda c:bool(detect_regions(c['notes'])))
    chosen=[(previous,c,'previously_reviewed') for c in old]+[(staging,c,'new_source') for c in fresh[:3]]
    source_pages={root:(root/'index.before-note-annotation.html').read_text(encoding='utf-8') for root in (previous,staging)}
    articles=[];cases=[];jobs=[]
    for i,(root,original,cohort) in enumerate(chosen,1):
        case=dict(original);old_id=case['id'];ident=f'case-{i:02d}';case['id']=ident;case['cohort']=cohort
        predictions=detect_regions(case['notes']);targets={n for p in predictions for n in p['anchor_occurrences']}
        case['target_ids']=sorted(targets);case['revised_regions']=predictions
        source=root/(old_id+'.gp');shutil.copyfile(source,out/(ident+'.gp'))
        article=re.search(r'<article data-id="'+re.escape(old_id)+r'">.*?</article>',source_pages[root],re.S)[0].replace(old_id,ident)
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
                jobs.append(dict(job,case_id=ident,file=str((out/(ident+'.gp')).resolve()),out=str((out/(ident+'.'+mode+'.wav')).resolve())))
    fingerprint=hashlib.sha256(json.dumps([(c['source_sha256'],c['target_ids']) for c in cases]).encode()).hexdigest()[:16]
    prefix=source_pages[previous].split('<article')[0]
    page=prefix+''.join(articles)+"<script>const key='pedal-revision-"+fingerprint+"';</script></html>"
    (out/'index.html').write_text(page,encoding='utf-8');(out/'cases.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
    (out/'render-jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8');upgrade(out,report)
    page=(out/'index.html').read_text(encoding='utf-8')
    page=page.replace('This checks analysis of six actual source passages. Nothing was composed, edited or varied. It does not ask which version sounds better.',
        'Updated analysis of unchanged source music: six earlier passages and three new song families. First mark what you hear, then reveal our detection. Earlier feedback is preserved separately.')
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
    page=page.replace('</style>','article:not(.revealed) .source-note:not(.selected){fill:#69a7c7}article:not(.revealed) .after-reveal{display:none}</style>')
    page=page.replace('fill="#f6c85f"','fill="#f6c85f" data-detected="true"')
    page=page.replace('</style>','article.revealed .source-note[data-detected="true"]:not(.sounding){stroke:#f6c85f;stroke-width:2}</style>')
    cards=re.findall(r'<article\b.*?</article>',page,re.S)
    start=page.index('<article');end=page.rindex('</article>')+len('</article>')
    page=page[:start]+'<h2>New source passages — start here</h2>'+''.join(cards[6:])+'<h2>Earlier passages — check the corrections</h2>'+''.join(cards[:6])+page[end:]
    (out/'index.html').write_text(page,encoding='utf-8')
    return dict(cases=len(cases),new_source_cases=3,new_render_jobs=len(jobs),study='pedal-revision-'+fingerprint)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);p.add_argument('corpus',type=Path);p.add_argument('previous',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Source review stays private')
    print(json.dumps(create(json.loads(a.report.read_text(encoding='utf-8')),a.corpus,a.previous,a.out)))
