"""Upgrade private source review in place; never alters source/audio or feedback."""
import argparse
from fractions import Fraction as F
import html
import json
from pathlib import Path
import re
import shutil
from source_semantics import seconds_between


def upgrade(out, report):
    page=(out/'index.html').read_text(encoding='utf-8')
    backup=out/'index.before-note-annotation.html'
    if not backup.exists():backup.write_text(page,encoding='utf-8')
    else:page=backup.read_text(encoding='utf-8')
    cases=json.loads((out/'cases.json').read_text(encoding='utf-8'))
    songs={s['song_id']:s for s in report['songs']}
    for case in cases:
        base=F(case['base_q']);end=F(case['end_q']);timeline=songs[case['song_id']]['timeline']
        points={base,end}
        points.update(F(t['onset_q']) for t in timeline['tempo'] if base<F(t['onset_q'])<end)
        mapping=[dict(x=float((q-base)/(end-base)*960),seconds=seconds_between(base,q,timeline)) for q in sorted(points)]
        if any(p['seconds'] is None for p in mapping):raise ValueError('Unresolved tempo')
        pattern=r'(<article data-id="'+re.escape(case['id'])+r'">)(.*?)(</article>)'
        def article(match):
            body=match[2];iterator=iter(case['notes'])
            def note(rect):
                n=next(iterator);start=max(base,F(n['onset_q']));stop=min(end,F(n['onset_q'])+F(n['duration_q']))
                title=f"Bar {n['bar']}, string {n.get('string', '?')}, fret {n.get('fret', '?')}, pitch {n['midi']}. Toggle pedal anchor."
                return rect[0][:-2]+f' class="source-note" role="button" tabindex="0" aria-pressed="false" aria-label="{html.escape(title,quote=True)}" data-note="{html.escape(n["occurrence"],quote=True)}" data-pitch="{n["midi"]}" data-bar="{n["bar"]}" data-start="{seconds_between(base,start,timeline)}" data-end="{seconds_between(base,stop,timeline)}"/>'
            body=re.sub(r'<rect\b[^>]*?/>',note,body)
            body=body.replace('</svg>','<line class="playhead" x1="0" x2="0" y1="0" y2="100%" stroke="#fff" stroke-width="2" pointer-events="none"/></svg>')
            body=body.replace('<svg role="img"','<svg role="group" data-time-map="'+html.escape(json.dumps(mapping),quote=True)+'"')
            body=body.replace('<p>Full arrangement</p>','<p>Click notes to mark the actual pedal anchors. Your choices appear in pink. Click again to undo.</p><p class="selection-summary" aria-live="polite">No notes marked by you.</p><button type="button" class="clear-notes">Clear my note selections</button><p>Full arrangement</p>')
            return match[1]+body+match[3]
        page=re.sub(pattern,article,page,flags=re.S)
    page=page[:page.index('<script>')]+ '<script src="pedal-review.js"></script></html>'
    page=page.replace('</style>','.source-note{cursor:pointer;stroke:transparent;stroke-width:2}.source-note:hover,.source-note:focus{stroke:white;outline:none}.source-note.selected{fill:#ff65bb;stroke:white}.source-note.sounding{stroke:#a7ff83;stroke-width:3}.playhead{filter:drop-shadow(0 0 2px black)}</style>')
    # Retain the original study key so existing ratings/notes survive the upgrade.
    old=backup.read_text(encoding='utf-8');key=re.search(r"const key='([^']+)'",old)[1]
    page=page.replace('<script src=',f'<meta name="study-key" content="{html.escape(key,quote=True)}"><script src=')
    (out/'index.html').write_text(page,encoding='utf-8')
    shutil.copyfile(Path(__file__).parents[2]/'pedal-review.js',out/'pedal-review.js')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('report',type=Path);a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private review only')
    upgrade(a.out,json.loads(a.report.read_text(encoding='utf-8')))
