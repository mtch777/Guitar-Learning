"""One preregistered unseen Songsterr input for component-conditioned speed."""
import argparse,json
from pathlib import Path
from freeze_local_dynamics import freeze,capture

if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');f.add_argument('output',type=Path);f.add_argument('backend',type=Path);f.add_argument('module',type=Path);f.add_argument('font',type=Path)
    c=sub.add_parser('capture');c.add_argument('output',type=Path);args=parser.parse_args()
    result=freeze(args.output,args.backend,args.module,args.font,'source_rhythmic_component_tempo')if args.action=='freeze'else capture(args.output)
    print(json.dumps({k:v for k,v in result.items()if k in('seed','status','selected_song_id','title','artist','tracks','capture_error')}))
