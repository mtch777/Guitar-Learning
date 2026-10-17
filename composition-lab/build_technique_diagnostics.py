"""Author reproducible engine diagnostics; not source-style generation/listening tests."""
import argparse
import json
from pathlib import Path
from gp_author import write_gp
from technique_edits import generate_hopo,generate_vibrato
from technique_analysis import analyze
from exact_score import extract_score


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    tuning=[40,45,50,55,59,64];pattern=[0,2,4,2,0,12,14,16,14,12,0,2,4,2,0,2]*2;measures=[]
    for bar in range(8):
        events=[dict(onset_q=str(bar*4+i),local_onset_q=str(i),duration_q='1',notes=[dict(midi=64+f,string=5,fret=f,tie=None,technique_tags=[])]) for i,f in enumerate(pattern[bar*4:bar*4+4])]
        measures.append(dict(number=bar+1,onset_q=str(bar*4),time_signature='4/4',voices=[events]))
    source=a.out/'authored-reference.gp'
    write_gp(dict(tracks=[dict(index=0,name='Authored technique diagnostic',program=25,tunings=[tuning],measures=measures)]),source)
    records=[]
    for family in ('hammer_on_fretted','pull_off_fretted','hammer_on_from_open','pull_off_to_open'):
        dest=a.out/(family+'.gp');audit=generate_hopo(source,dest,0,family)
        dest.with_suffix('.analysis.json').write_text(json.dumps(analyze(extract_score(dest))))
        records.append(dict(family=family,selected=audit['selected'],locks=audit['locked_xml_verified']))
    for width in ('Slight','Wide'):
        dest=a.out/('vibrato-'+width+'.gp');audit=generate_vibrato(source,dest,0,width=width)
        dest.with_suffix('.analysis.json').write_text(json.dumps(analyze(extract_score(dest))))
        records.append(dict(family='finger_vibrato',width=width,selected=audit['selected'],locks=audit['locked_xml_verified']))
    (a.out/'manifest.json').write_text(json.dumps(dict(cases=records,scope='Authored engine diagnostics; no source corpus or musical quality claim'),indent=2));print(json.dumps(records))


if __name__=='__main__':main()
