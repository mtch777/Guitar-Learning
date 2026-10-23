"""Pinned-library diagnostic only; annotations/model labels are NOT truth."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import warnings
import sys
import music21
from music21 import harmony
from source_tie_tier1 import extract_documents
import musical_tier2 as music


def annotation_inventory(documents):
    sys.path.insert(0,str(Path(__file__).resolve().parent/'songsterr_automation/songsterr_api'))
    from source_semantics import layout,whole_measure_rest
    parts=sorted((d for name,d in documents.items() if name.startswith('track-')),key=lambda d:d['partId'])
    headers,problems=layout(parts);rows=[]
    for part in parts:
        pid=part['partId']
        for mi,measure in enumerate(part.get('measures',[])):
            header=headers[mi]
            for vi,voice in enumerate(measure.get('voices',[])):
                local=F(0)
                for bi,beat in enumerate(voice.get('beats',[])):
                    if 'chord' in beat and isinstance(beat['chord'],dict) and 'text' in beat['chord']:
                        rows.append(dict(source_fact_ref=f'track-{pid}.json#/measures/{mi}/voices/{vi}/beats/{bi}/chord/text',literal_text=beat['chord']['text'],part_id=pid,bar=mi+1,voice=vi,beat=bi,
                            at_q=str(F(header['start_q'])+local),annotation_duration_q=None,scope='Declaration on this part/voice/beat ONLY; no inferred duration',
                            source_measure_span_q=[header['start_q'],str(F(header['start_q'])+F(header['span_q']))],capo_declaration=part.get('capo'),label_pitch_convention='not_declared',
                            declaration_note_slots=[ni for ni,n in enumerate(beat.get('notes',[])) if not n.get('rest')]))
                    if beat.get('graceNote'):continue
                    if whole_measure_rest(measure,voice):local+=F(header['span_q'])
                    elif isinstance(beat.get('duration'),list) and len(beat['duration'])==2:local+=4*F(*beat['duration'])
                    else:raise ValueError('Missing/unsupported source beat duration; no guessed label clock')
    return rows,problems


def parse_symbol(text):
    observed=[];caught=[]
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');chord=harmony.ChordSymbol(text)
            root=chord.root();bass=chord.bass()
            if root is None or bass is None or not chord.pitches:raise ValueError('Parser supplied no definite symbolic chord')
            result=dict(status='PARSED_LIBRARY_INTERPRETATION',root_letter_name=root.name,root_pc=root.pitchClass,bass_letter_name=bass.name,bass_pc=bass.pitchClass,
                chord_kind=chord.chordKind,pitch_classes=sorted({p.pitchClass for p in chord.pitches}),root_intervals_pc=sorted({(p.pitchClass-root.pitchClass)%12 for p in chord.pitches}))
    except Exception as exc:result=dict(status='UNPARSED_RETAINED',error=type(exc).__name__+': '+str(exc))
    observed=[dict(category=w.category.__name__,message=str(w.message)) for w in caught]
    return dict(**result,warnings=observed,meaning='Library expansion of literal chord symbol, not measured harmony')


def pitch_evidence(upper,clock,part_id=None,starts_only=False):
    at=F(clock);domain={r['occurrence_ref']:r['domain'] for r in music.occurrence_pitch_domains(upper)};known=[];unknown=[];nonpitched=[]
    for group in upper['coattacks']:
        if part_id is not None and group['part_id']!=part_id:continue
        a=F(group['onset_q'])
        for member in group['members']:
            if not (a==at if starts_only else a<=at<a+F(member['duration_q'])):continue
            if domain[member['id']]=='explicit_nonpitched':nonpitched.append(member['id']);continue
            p=music.member_pitch(group,member)
            if p is None or F(p).denominator!=1:unknown.append(dict(occurrence_ref=member['id'],written_pitch=p));continue
            known.append(dict(occurrence_ref=member['id'],written_pitch=p,pitch_class=int(F(p)%12)))
    return dict(known_occurrences=known,pitch_classes=sorted({n['pitch_class'] for n in known}),unknown_or_noninteger_pitch=unknown,explicit_nonpitched_refs=nonpitched,
        lowest_known_pc=None if not known else int(min(F(n['written_pitch']) for n in known)%12),scope='Written base pitch at nominal source clock; not acoustic execution')


def set_comparison(observed,parsed):
    if parsed['status']!='PARSED_LIBRARY_INTERPRETATION':return dict(status='UNPARSED_SYMBOL')
    a=set(observed['pitch_classes']);b=set(parsed['pitch_classes'])
    status='NO_KNOWN_PITCHED_EVIDENCE' if not a else 'EXACT_PC_SET' if a==b else 'OBSERVED_SUBSET_OF_SYMBOL' if a<b else 'SYMBOL_SUBSET_OF_OBSERVED' if b<a else 'OVERLAPPING_DIFFERENT_SETS' if a&b else 'DISJOINT_PC_SETS'
    return dict(status=status,observed_outside_symbol=sorted(a-b),symbol_tones_not_observed=sorted(b-a),partial_known_pitch_evidence=bool(observed['unknown_or_noninteger_pitch']),
        lowest_known_pc_matches_declared_bass=None if observed['lowest_known_pc'] is None else observed['lowest_known_pc']==parsed['bass_pc'])


def run(captures,output):
    if music21.__version__!='9.9.2':raise ValueError('Frozen diagnostic parser version9.9.2 required')
    output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
    library=Path(music21.__file__).resolve().parent
    files=list(library.rglob('*.py'))+[Path(__file__),root/'musical_tier2.py',root/'source_tie_tier1.py',root/'source_key_tier1.py',root/'songsterr_automation/songsterr_api/source_semantics.py']
    studies=[]
    for capture in captures:
        paths=[capture/'metadata.json']+sorted(capture.glob('track-*.json'));files+=paths
        documents={p.name:json.loads(p.read_text(encoding='utf-8-sig')) for p in paths};inventory,problems=annotation_inventory(documents)
        studies.append((capture,documents,inventory,problems))
    frozen={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (output/'freeze-before-predictions.json').write_text(json.dumps(dict(parser='music21',version=music21.__version__,files=frozen,license='Library source/runtime separate from private captured scores'),indent=2),encoding='utf-8')
    (output/'declarations-before-predictions.json').write_text(json.dumps([dict(capture=str(p),declarations=inv,source_layout_warnings=w) for p,docs,inv,w in studies],indent=2),encoding='utf-8')
    results=[]
    for si,(capture,documents,inventory,problems) in enumerate(studies):
        upper=music.strip_lower(music.analyze(extract_documents(documents)));cache={};rows=[]
        index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']}
        for declaration in inventory:
            text=declaration['literal_text'];parsed=parse_symbol(text);clock=declaration['at_q'];pid=declaration['part_id']
            starts=pitch_evidence(upper,clock,pid,True);part=pitch_evidence(upper,clock,pid);ensemble=pitch_evidence(upper,clock)
            expected_refs=[f"event:{documents['metadata.json']['songId']}:{pid}:{declaration['bar']}:{declaration['voice']}:{declaration['beat']}:{ni}" for ni in declaration['declaration_note_slots']]
            time_issues=[ref for ref in expected_refs if ref not in index or index[ref][0]['onset_q']!=clock]
            contexts=[]
            for scope in (pid,None):
                a,b=declaration['source_measure_span_q'];key=(scope,a,b)
                if key not in cache:cache[key]=music.harmonic_span_evidence(upper,a,b,part_id=scope,max_edges=2048)
                evidence=cache[key];labels=None
                if evidence['status']=='SCORED_NOT_MUSICAL_TRUTH':
                    cell=next((c for c in evidence['all_optimal_path_cell_consensus'] if F(c['start_q'])<=F(clock)<F(c['end_q'])),None)
                    labels=None if cell is None else cell['candidate_labels']
                comparisons=None if labels is None or parsed['status']!='PARSED_LIBRARY_INTERPRETATION' else [dict(label=l,root_agrees=l['root_pc']==parsed['root_pc'],pc_set_agrees={(l['root_pc']+d)%12 for d in l['formula']}==set(parsed['pitch_classes'])) for l in labels]
                contexts.append(dict(scope='declaring_part' if scope is not None else 'ensemble',request=evidence['request'],status=evidence['status'],all_clock_labels=labels,comparisons=comparisons))
            row=dict(declaration=declaration,parser_interpretation=parsed,source_time_join_issues=time_issues,declaring_part_starts=starts,declaring_part_nominal_overlap=part,ensemble_nominal_overlap=ensemble,
                part_symbol_comparison=set_comparison(part,parsed),ensemble_symbol_comparison=set_comparison(ensemble,parsed),scored_harmonic_contexts=contexts)
            rows.append(row)
            print(json.dumps(dict(source=si,declaration=len(rows),total=len(inventory),parser=parsed['status'],part=row['part_symbol_comparison']['status'])),flush=True)
        result=dict(capture=str(capture),source_declarations=len(inventory),accounted_declarations=len(rows),source_layout_warnings=problems,rows=rows)
        (output/(str(si)+'-comparison.json')).write_text(json.dumps(result,indent=2),encoding='utf-8');results.append(result)
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
    report=dict(status='COMPLETED_DIAGNOSTIC' if unchanged else 'FAIL_MUTATED_INPUT_OR_CODE',unchanged=unchanged,parser_version=music21.__version__,declarations=sum(len(r['rows']) for r in results),
        parser_status_counts=dict(Counter(row['parser_interpretation']['status'] for r in results for row in r['rows'])),
        source_time_join_issue_count=sum(len(row['source_time_join_issues']) for r in results for row in r['rows']),
        part_pc_comparisons=dict(Counter(row['part_symbol_comparison']['status'] for r in results for row in r['rows'])),
        scope='Diagnostic only, not a new reversible tier, chord accuracy score, annotation truth, sounding-pitch or mode inference')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('captures',nargs='+',type=Path);a=p.parse_args();r=run(a.captures,a.output)
    print(json.dumps(r));raise SystemExit(0 if r['status']=='COMPLETED_DIAGNOSTIC' else 1)
