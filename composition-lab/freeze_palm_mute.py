"""One preregistered unseen Songsterr input for the palm-muting control."""
import argparse,json
from pathlib import Path
from freeze_local_dynamics import freeze,capture

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');f.add_argument('output',type=Path);f.add_argument('backend',type=Path);f.add_argument('module',type=Path);f.add_argument('font',type=Path)
    c=sub.add_parser('capture');c.add_argument('output',type=Path);a=p.parse_args()
    result=freeze(a.output,a.backend,a.module,a.font,'source_local_palm_mute')if a.action=='freeze'else capture(a.output)
    print(json.dumps({k:v for k,v in result.items()if k in('seed','status','selected_song_id','title','artist','tracks','capture_error')}))
