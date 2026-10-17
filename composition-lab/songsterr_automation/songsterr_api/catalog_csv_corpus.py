"""Catalog private reconstructed scores and emit source-free aggregate evidence."""
from collections import Counter
import argparse,csv,hashlib,json,re,shutil
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--summary',type=Path,required=True);a=p.parse_args()
    songs=a.root/'songs';destination=a.root/'gp-files';destination.mkdir(exist_ok=True);rows=[];reports=[];captures=[]
    for folder in sorted(songs.iterdir()):
        if not folder.is_dir() or not (folder/'capture.json').exists():continue
        capture=json.loads((folder/'capture.json').read_text(encoding='utf-8'));captures.append(capture)
        report=json.loads((folder/'gp7-validation.json').read_text(encoding='utf-8'));reports.append(report)
        meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
        name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','',f"{capture['song_id']} - {meta.get('title','Untitled')}").strip(' .')[:140]+'.gp'
        target=destination/name;source=folder/'score.gp'
        if not source.exists():raise ValueError(f"Missing GP: {capture['song_id']}")
        if target.exists() and target.read_bytes()!=source.read_bytes():raise FileExistsError(f'Existing catalog copy differs: {target}')
        if not target.exists():shutil.copyfile(source,target)
        for selected in capture['csv_rows']:
            rows.append(dict(csv_row=selected['csv_row'],song=selected['Song'],artist=meta.get('artist'),song_id=capture['song_id'],revision=capture.get('revision_id'),gp_file=str(target.resolve()),
                             gp7_roundtrip_pass=report.get('roundtripPass',False),regular_source_differences=report.get('directSource',{}).get('differences'),
                             source_gp5_comparator_errors=sum('error' in t for t in capture.get('serialized_source_comparison',[])),
                             source_gp5_comparator_differences=sum(t.get('differences') or 0 for t in capture.get('serialized_source_comparison',[])),
                             converter_warnings=json.dumps(capture.get('converter_warnings',{})),raw_source_folder=str(folder.resolve())))
    with (a.root/'catalog.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(sorted(rows,key=lambda r:r['csv_row']))
    inventory=json.loads((a.root/'source-techniques.json').read_text());tracks=[t for s in inventory['songs'] for t in s['tracks'] if t['guitar_or_bass']];counts=Counter();groups=Counter()
    for t in tracks:counts.update(t['counts']);groups.update(t['coattack_groups'])
    source_checks=[t for c in captures for t in c.get('serialized_source_comparison',[])]
    summary=dict(schema='csv-source-corpus-acquisition-v1',csv_rows=len(rows),unique_tab_ids=len(captures),captured_tabs=sum(c.get('capture_complete',False) for c in captures),
                 gp7_files=len(list(destination.glob('*.gp'))),gp7_detailed_roundtrip_pass=sum(r.get('roundtripPass',False) for r in reports),
                 gp7_regular_source_zero_differences=sum(r.get('directSource',{}).get('differences')==0 for r in reports),
                 serialized_source_tracks_checked=len(source_checks),serialized_source_tracks_pass=sum(t.get('differences')==0 for t in source_checks),serialized_source_comparator_errors=sum('error' in t for t in source_checks),
                 all_tracks=sum(len(s['tracks']) for s in inventory['songs']),guitar_bass_tracks=len(tracks),guitar_bass_notation_counts=dict(counts),guitar_bass_coattack_groups=dict(groups),
                 converter_commits=sorted({c['converter_commit'] for c in captures}),alphatab_version='1.8.4',
                 limitations=['Reconstructed GP7, not original uploader binaries','Detailed GP7 comparison includes notes/rhythm/selected effects, not every possible source field','Conversion warnings and failures remain in private catalog; do not treat losses as absent techniques','Raw-source inventory is independent of conversion','Different versions, collaborations and AI-labeled entries are not independent verified artist examples','No recreation or artist-feel validation claimed'])
    a.summary.parent.mkdir(parents=True,exist_ok=True);a.summary.write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in ('guitar_bass_notation_counts','guitar_bass_coattack_groups','limitations')}))


if __name__=='__main__':main()
