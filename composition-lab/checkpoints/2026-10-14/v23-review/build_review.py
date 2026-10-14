"""Create an offline, one-at-a-time audio + note-context annotation UI for V22."""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
from fractions import Fraction
ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/data')
CSV=BASE/'V22_Reference_Validation/V21_human_review.csv'
try:
    from extract import extract_score
except ModuleNotFoundError:
    sys.path.insert(0,str(BASE/'v20_work'))
    from extract import extract_score

def frac(value):return float(Fraction(str(value)))
def collect():
    with CSV.open(newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
    scores={}
    for filename in sorted({r['source_file'] for r in rows}):
        sc=extract_score(BASE/filename)
        voices=[]
        for track in sc['tracks']:
            for measure in track['measures']:
                for vi,voice in enumerate(measure['voices']):
                    for event in voice:
                        notes=sorted({n['midi'] for n in event['notes'] if n['midi'] is not None})
                        if notes:
                            voices.append({'t':frac(event['onset_q']),'d':frac(event['duration_q']),
                                           'p':notes,'track':track['index'],'voice':vi,'bar':measure['number']})
        scores[filename]={'tracks':[t['name'] for t in sc['tracks']],'notes':voices,
                          'bars':[{'n':m['number'],'start':frac(m['onset_q']),'meter':m['time_signature'],
                                   'section':m.get('section')} for m in sc['tracks'][0]['measures']]}
    return {'rows':rows,'scores':scores,'fields':list(rows[0])}

def build():
    payload=json.dumps(collect(),ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    template=(ROOT/'player_template.html').read_text(encoding='utf-8')
    result=template.replace('/*__PAYLOAD__*/',payload)
    out=ROOT/'V23_Music_Review_Player.html';out.write_text(result,encoding='utf-8');return out
if __name__=='__main__':
    p=argparse.ArgumentParser(description='Build standalone audio review app from original .gp files')
    p.add_argument('--source-dir',type=Path,default=BASE,help='Directory containing the source .gp files')
    p.add_argument('--review-csv',type=Path,default=CSV,help='V21/V22 review cases CSV')
    p.add_argument('--output-dir',type=Path,default=ROOT,help='Output folder')
    args=p.parse_args()
    BASE=args.source_dir;CSV=args.review_csv;ROOT=args.output_dir
    ROOT.mkdir(parents=True,exist_ok=True)
    # Keep the template beside the script even when writing output elsewhere.
    original=Path(__file__).resolve().parent/'player_template.html'
    if ROOT!=original.parent:
        (ROOT/'player_template.html').write_text(original.read_text(encoding='utf-8'),encoding='utf-8')
    print(build())