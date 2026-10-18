"""Measure anchor/contrast exchanges across the private source corpus."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pedal_dialogue import analyze_dialogue


def write_examples(private,path):
    lines=['# Source-located pedal exchanges','',
           'Exact notation measurements. Call/response are operational labels; no emotional interpretation.','']
    seen=set()
    for item in private:
        if item['song_id'] in seen:continue
        region=next((r for r in item['dialogues'] if len(r['cycles'])>=3),None)
        if region is None:continue
        seen.add(item['song_id'])
        lines.extend([f"## {item['title']} — {item['track']}",
                      f"Source {item['song_id']}, part {item['part_id']}, section instance {region['section_start']}; anchor {region['anchor_pitches']}; quarter-time scope {region['scope_start_q']}–{region['scope_end_q']}.",'',
                      '| Exchange | Call attacks / durations | Response pitches | Intervals above anchor | Response durations | IOIs | Gap / overlap |',
                      '|---|---|---|---|---|---|---|'])
        for i,c in enumerate(region['cycles'][:6],1):
            call,response=c['call'],c['response']
            lines.append(f"| {i} | {call['attack_groups']} / {call['notated_duration_histogram']} | {response['pitches']} | {response['intervals_from_lowest_anchor']} | {response['notated_duration_histogram']} | {response['ioi_q']} | {c['call_to_response_gap_q']} / {c['call_sustain_into_response_q']} |")
        lines.extend(['','Adjacent consistency (numerator / comparable pairs): '+json.dumps(region['consistency']),
                      'Same-call families: '+json.dumps([{k:v for k,v in f.items() if k in ('observed','distinct_responses','response_textures')} for f in region['call_response_families']]),''])
        if len(seen)>=6:break
    path.write_text('\n'.join(lines),encoding='utf-8')


def run(report,regions):
    index={(r['song_id'],r['part_id']):r['regions'] for r in regions}
    totals=Counter();kinds=Counter();consistency=Counter();private=[];audit=Counter();response_shapes=Counter()
    for song in report['songs']:
        for track in song['tracks']:
            candidates=index.get((song['song_id'],track['part_id']),[])
            if not track['guitar_or_bass'] or not track['temporal_relationships_eligible']:continue
            measured=[]
            for candidate in candidates:
                region=dict(candidate)
                later=[F(r['start_q']) for r in candidates if r['section_start']==region['section_start'] and F(r['start_q'])>F(region['start_q'])]
                if later:region['scope_end_q']=str(min(later))
                result=analyze_dialogue(track,region);measured.append(result)
                expected={n['occurrence'] for n in track['rows'] if n['section_start']==region['section_start'] and not n['tie_destination'] and F(result['scope_start_q'])<=F(n['onset_q'])<F(result['scope_end_q'])}
                identifiers=[n['occurrence'] for e in result['events'] for n in e['notes']]
                if len(identifiers)!=len(set(identifiers)) or set(identifiers)!=expected:raise ValueError('Dialogue occurrence coverage mismatch')
                audit['regions_checked']+=1;audit['attack_occurrences_checked']+=len(identifiers)
                assigned=[]
                for c in result['cycles']:
                    if F(c['call']['start_q'])>=F(c['response']['start_q']):raise ValueError('Invalid call/response order')
                    assigned.extend(c['call_members']+c['response_members']);audit['cycles_checked']+=1
                    response_shapes[c['response']['note_texture']]+=1
                if len(assigned)!=len(set(assigned)):raise ValueError('Cycle occurrences assigned more than once')
                totals['regions']+=1;totals['cycles']+=len(result['cycles'])
                totals['closed_cycles']+=sum(c['closed_by_anchor_return'] for c in result['cycles'])
                totals['censored_cycles']+=sum(c['right_censored'] for c in result['cycles'])
                totals['calls_sustaining_into_response']+=sum(F(c['call_sustain_into_response_q'])>0 for c in result['cycles'])
                kinds.update(result['event_kind_counts'])
                for name,c in result['consistency'].items():
                    consistency[name+'_numerator']+=c.get('equal',c.get('count',0));consistency[name+'_denominator']+=c['compared']
            if measured:private.append(dict(song_id=song['song_id'],part_id=track['part_id'],title=song['title'],track=track['name'],dialogues=measured))
    public=dict(schema='pedal-dialogue-v1',counts=dict(totals),attack_group_kinds=dict(kinds),response_textures=dict(response_shapes),integrity_audit=dict(audit),adjacent_cycle_consistency=dict(consistency),
                limitations=['Anchor-only call / non-anchor response are explicit analytical conventions, not intent labels.',
                             'Notated source rhythms/pitches, not live performance or emotional interpretation.',
                             'Regions are bounded by source section/next anchor region; not validated phrase boundaries.',
                             'Counts pool source entries including candidate duplicates; not artist-balanced estimates.'])
    return public,private


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);p.add_argument('regions',type=Path);p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--examples',type=Path);a=p.parse_args()
    if 'local-artifacts' not in a.private.resolve().parts:p.error('Occurrence-level analysis stays private')
    if a.examples and 'local-artifacts' not in a.examples.resolve().parts:p.error('Source examples stay private')
    public,private=run(json.loads(a.report.read_text(encoding='utf-8')),json.loads(a.regions.read_text(encoding='utf-8')))
    public['source_report_sha256']=hashlib.sha256(a.report.read_bytes()).hexdigest();public['regions_sha256']=hashlib.sha256(a.regions.read_bytes()).hexdigest()
    a.public.write_text(json.dumps(public,indent=2),encoding='utf-8');a.private.write_text(json.dumps(private,separators=(',',':')),encoding='utf-8');print(json.dumps(public))
    if a.examples:write_examples(private,a.examples)
