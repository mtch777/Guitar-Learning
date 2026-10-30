"""One new random Songsterr capture for both independent lever tests."""
import argparse,json
from pathlib import Path
from freeze_local_dynamics import freeze,capture

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='action',required=True)
    f=s.add_parser('freeze');f.add_argument('output',type=Path);f.add_argument('backend',type=Path);f.add_argument('module',type=Path);f.add_argument('font',type=Path)
    c=s.add_parser('capture');c.add_argument('output',type=Path);a=p.parse_args()
    result=freeze(a.output,a.backend,a.module,a.font,'parallel_rhythm_melody')if a.action=='freeze'else capture(a.output)
    print(json.dumps({k:v for k,v in result.items()if k in('seed','case_count','status','selected_song_id','title','artist','tracks','capture_error')}))
