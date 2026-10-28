"""Source-independent execution of the bounded frame-to-degree relationship."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from qa_isolation_harness import execute
from voicing_frames import relationship


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(case,output,freeze):
    output.mkdir(parents=True,exist_ok=False);frozen=json.loads(freeze.read_text());hashes=frozen['code_hashes'];root=Path(__file__).parent
    try:
        if any(sha(p)!=h for p,h in hashes.items()):raise ValueError('Code changed after freeze')
        catalog=json.loads((case/'catalog.json').read_text());oracle=json.loads((case/'independent-inventory.json').read_text())
        native={u['id']:u for u in oracle['units']};groups=[];expected=[];patterns=defaultdict(list)
        for unit in catalog['units']:
            if unit['base_reasons']:continue
            other=native[unit['id']]
            if unit['roles']!=other['roles'] or unit['family']!=other['family'] or unit['strings']!=other['strings']:raise ValueError('Independent source degree disagreement')
            frame=relationship(*unit['family'][1:],roles=unit['roles'])
            groups.append(dict(id=unit['id'],root_pc=unit['family'][1],kind=unit['family'][2],framed=frame))
            expected.append(dict(id=unit['id'],roles=other['roles']))
            key=json.dumps([unit['part_id'],unit['family'][2],unit['strings'],frame['components']],sort_keys=True)
            patterns[key].append(dict(id=unit['id'],root_pc=unit['family'][1],frame_octave=frame['frame_octave']))
        code='import sys,types\n'
        for name in ('musical_tier2','chord_degree_definitions','chord_degree_relations','voicing_frames'):
            source=(root/(name+'.py')).read_text(encoding='utf-8-sig')
            code+=f"_m=types.ModuleType({name!r});sys.modules[{name!r}]=_m\nexec(compile({source!r},{name!r},'exec'),_m.__dict__)\n"
        code+="\ndef reconstruct(upper,controls):\n return [{'id':r['id'],'roles':sys.modules['voicing_frames'].relationship(r['root_pc'],r['kind'],framed=r['framed'])} for r in upper['groups']]\n"
        isolated=execute(code,dict(groups=groups),dict(voicing=0,register=0),expected,output/'isolated',timeout=120)
        if isolated['status']!='PASS':raise ValueError(isolated)
        actual=json.loads((output/'isolated/worker/output.json').read_text())
        if actual!=expected:raise ValueError('Actual worker differs from independent source degrees')
        support=[dict(part_id=json.loads(k)[0],kind=json.loads(k)[1],strings=json.loads(k)[2],components=json.loads(k)[3],occurrences=v,distinct_roots=sorted({r['root_pc'] for r in v})) for k,v in sorted(patterns.items())]
        (output/'source-support.json').write_text(json.dumps(support,indent=2),encoding='utf-8')
        if any(sha(p)!=h for p,h in hashes.items()):raise ValueError('Code drift during QA')
        result=dict(status='PASS_BOUNDED_FRAME_QA' if groups else 'NO_COVERED_DEGREE_GROUPS',groups=len(groups),degree_members=sum(len(r['roles']) for r in actual),patterns=len(patterns),patterns_across_roots=sum(len(r['distinct_roots'])>1 for r in support),isolated_status=isolated['status'],
            scope='Degree/register vectors for existing base-eligible declared-chord groups; not the whole song or a creative change',
            removed=['Source capture','Tier0 and Tier1','Original degree vectors','Absolute note pitches','Expected output','Source/cache access'],
            retained=['Declared chord root and kind','Canonical group frame','Degree token and octave offset per member','Group identity and member order'],
            qa3='Same degree/register patterns across roots are identified where present. No inferred key, melodic identity, preferred voicing, human playability or artist fit.')
    except Exception as error:result=dict(status='FAIL_RETAINED',error=str(error))
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


def main():
    p=argparse.ArgumentParser();p.add_argument('case',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args();r=run(a.case,a.output,a.freeze);print(json.dumps(r,indent=2));return int(r['status']=='FAIL_RETAINED')


if __name__=='__main__':raise SystemExit(main())
