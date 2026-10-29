"""Use the same preregistered random capture gate for local accents."""
import argparse,json
from pathlib import Path
from freeze_local_dynamics import freeze,capture

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('freeze');a.add_argument('output',type=Path);a.add_argument('backend',type=Path);a.add_argument('module',type=Path);a.add_argument('font',type=Path)
    a=s.add_parser('capture');a.add_argument('output',type=Path);a=p.parse_args()
    r=freeze(a.output,a.backend,a.module,a.font,'source_local_note_accent')if a.action=='freeze'else capture(a.output)
    print(json.dumps({k:v for k,v in r.items()if k in('seed','case_count','status','selected_song_id','title','artist','tracks','capture_error')}))
