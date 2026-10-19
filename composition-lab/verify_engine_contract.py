"""Read-only stage verification; write source-located reports only outside Git."""
import argparse
import json
from pathlib import Path

from engine_contract import audit_existing_edit, sha


def verify(directory, performance_model, palm_model, artist):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    reports = []
    for stage, key, model_path, source, output, code in (
        ('performance', 'performance', performance_model, '01-core.gp', '02-performance.gp', 'learned_performance.py'),
        ('palm_mute', 'palm', palm_model, '02-performance.gp', '03-palm.gp', 'palm_mute_method.py'),
    ):
        seal = sha(model_path)
        if seal != manifest['model_sha256'][key]:raise ValueError('Model differs from recorded run')
        model = json.loads(Path(model_path).read_text(encoding='utf-8'))
        tables = [t for t in model['tables'] if t['artist'] == artist and t['context'] == '*']
        if len(tables) != 1:raise ValueError('Unique artist/global support required')
        audit = next(s['audit'] for s in manifest['stages'] if s['stage'] == stage)
        features = sorted({d.get('family', 'palm_mute') for d in audit['decisions']})
        supports = {f:dict(known=True, eligible_mass_q=tables[0]['known'][f],
                          denominator_unit='family_weighted_eligible_mass', model_sha256=seal)
                    for f in features}
        result = audit_existing_edit(directory/source, directory/output, audit,
            {f:manifest['controls'][f] for f in features}, supports,
            method=Path(code).stem+'.apply', method_source=Path(__file__).with_name(code))
        result['recorded_manifest_sha256'] = sha(directory/'manifest.json')
        reports.append(result)
    return reports


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--performance-model',type=Path,required=True)
    parser.add_argument('--palm-model',type=Path,required=True)
    parser.add_argument('--artist',required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    reports=verify(args.directory,args.performance_model,args.palm_model,args.artist)
    with args.report.open('x',encoding='utf-8') as handle:json.dump(reports,handle,indent=2)
    print(json.dumps({r['method']:len(r['decisions']) for r in reports}))
