"""Reproduce private GP conversion evidence without publishing score content."""
import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from exact_score import extract_score, validate_events
from musicxml_bridge import export_musicxml, occurrence_rows
from relational_graph import build_graph


def validate_partitura(score, path):
    import partitura as pt
    parsed=pt.load_musicxml(str(path))
    expected=occurrence_rows(score); actual={}
    for ti,part in enumerate(parsed.parts):
        for note in part.notes:
            # Global divisions are constant by construction.
            div=int(part.quarter_duration_map(note.start.t))
            actual[note.id]=(Fraction(int(note.start.t),div),Fraction(int(note.end.t-note.start.t),div),note.midi_pitch,note.voice-1)
    bad=[nid for nid,row in expected.items() if actual.get(nid)!=(row[3],row[4],row[5],row[2])]
    return dict(written_notes=len(actual),note_array_rows=len(parsed.note_array()),
                mismatched_occurrences=len(bad),first_mismatch_ids=bad[:10],
                note_array_semantics='Partitura merges tied continuations; written-note audit uses unmerged part.notes')


def main():
    p=argparse.ArgumentParser();p.add_argument('sources',nargs='+',type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--partitura',action='store_true');p.add_argument('--pitched-only',action='store_true')
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    reports=[]
    for source in args.sources:
        score=extract_score(source); stem=source.stem; xml=args.out/(stem+'.musicxml')
        old_discrepancies=[]
        for track in score['tracks']:
            for m in track['measures']:
                n,d=map(int,m['time_signature'].split('/')); meter=Fraction(4*n,d)
                for vi,voice in enumerate(m['voices']):
                    if not voice:continue
                    old_total=sum((Fraction(e.get('notated_duration_q',e['duration_q'])) for e in voice),Fraction(0))
                    if old_total!=meter:
                        old_discrepancies.append(dict(track=track['index'],measure=m['number'],voice=vi,
                            naive_total_q=str(old_total),meter_q=str(meter),
                            grace_notated_q=str(sum((Fraction(e['notated_duration_q']) for e in voice if e.get('grace_type')),Fraction(0))),
                            corrected_total_q=str(sum((Fraction(e['duration_q']) for e in voice),Fraction(0)))))
        report=dict(source=source.name,sha256=score['source_sha256'],tracks=len(score['tracks']),bars=score['measure_count'],
                    corrected_discrepancies=validate_events(score),naive_discrepancies=old_discrepancies,
                    grace_beats=sum(bool(e.get('grace_type')) for t in score['tracks'] for m in t['measures'] for v in m['voices'] for e in v),
                    conversion=export_musicxml(score,xml))
        if args.partitura: report['partitura']=validate_partitura(score,xml)
        if args.pitched_only:
            view={**score,'tracks':[t for t in score['tracks'] if not t.get('is_percussion')]}
            path=args.out/(stem+'.pitched-only.musicxml')
            report['pitched_only']=dict(track_indices=[t['index'] for t in view['tracks']],
                conversion=export_musicxml(view,path),purpose='Explicit harmonic inference view; full original remains canonical')
        graph=build_graph(score)
        report['graph']=dict(nodes=len(graph['nodes']),edges=len(graph['edges']),
            relations=dict(Counter(e['relation'] for e in graph['edges'])),unresolved_ties=len(graph['warnings']))
        (args.out/(stem+'.graph.json')).write_text(json.dumps(graph),encoding='utf-8')
        (args.out/(stem+'.canonical.json')).write_text(json.dumps(score),encoding='utf-8')
        reports.append(report)
    (args.out/'source-fidelity-report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k not in ('naive_discrepancies','corrected_discrepancies')} for r in reports],indent=2))
    if any(r['corrected_discrepancies'] or not r['conversion']['exact_note_timing_pitch_voice'] or
           r.get('partitura',{}).get('mismatched_occurrences',0) for r in reports): raise SystemExit(1)


if __name__=='__main__':main()
