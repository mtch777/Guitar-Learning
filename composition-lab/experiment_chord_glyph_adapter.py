"""Frozen lexical root/bass glyph experiment; no chord-quality rewriting."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import music21
from music21 import pitch
from diagnose_source_chord_annotations import parse_symbol,set_comparison


def glyph_map():
    result={}
    for name in ('flat','sharp','double-flat','double-sharp','natural'):
        accidental=pitch.Accidental(name);result[accidental.unicode]=accidental.modifier
    return result


def normalize_roots(text):
    """Only accidental tokens immediately after root/bass A..G letters."""
    if type(text) is not str:raise ValueError('Literal source chord string required')
    mapping=glyph_map();symbols=sorted(mapping,key=len,reverse=True);output='';trace=[];offset=0
    for si,segment in enumerate(text.split('/')):
        if si:output+='/'
        if not segment or segment[0] not in 'ABCDEFG':output+=segment;offset+=len(segment)+1;continue
        output+=segment[0];cursor=1
        while cursor<len(segment):
            symbol=next((s for s in symbols if segment.startswith(s,cursor)),None)
            if symbol is None:break
            modifier=mapping[symbol]
            trace.append(dict(scope='root' if si==0 else 'slash_bass',source_offset=offset+cursor,normalized_offset=len(output),source_glyph=symbol,library_modifier=modifier))
            output+=modifier;cursor+=len(symbol)
        output+=segment[cursor:];offset+=len(segment)+1
    return output,trace


def restore_roots(normalized,trace):
    result=normalized;mapping=glyph_map()
    for row in reversed(trace):
        at=row['normalized_offset'];modifier=row['library_modifier'];glyph=row['source_glyph']
        if mapping.get(glyph)!=modifier or result[at:at+len(modifier)]!=modifier:raise ValueError('Contradictory glyph relationship')
        result=result[:at]+glyph+result[at+len(modifier):]
    return result


def run(baseline,output):
    if music21.__version__!='9.9.2':raise ValueError('Pinned parser runtime required')
    output.mkdir(parents=True,exist_ok=False)
    freeze=json.loads((baseline/'freeze-before-predictions.json').read_text(encoding='utf-8'));baseline_script=Path(__file__).with_name('diagnose_source_chord_annotations.py').resolve()
    # Only parser-warning retention changed in that diagnostic script. First
    # prove its sealed original remains saved; model/source/library files must
    # be identical before reusing their predictions.
    snapshot=baseline/'diagnostic-source-snapshot.py'
    if hashlib.sha256(snapshot.read_bytes()).hexdigest()!=freeze['files'][str(baseline_script)]:raise ValueError('Original diagnostic implementation not preserved')
    checked={}
    for filename,digest in freeze['files'].items():
        if Path(filename)==baseline_script:continue
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest()!=digest:raise ValueError('Source/core/library changed; cached harmonies cannot be reused')
        checked[filename]=digest
    files=sorted(baseline.glob('[0-9]*-comparison.json'))
    sources=[json.loads(p.read_text(encoding='utf-8')) for p in files]
    frozen={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[Path(__file__),baseline_script,snapshot,baseline/'result.json']}
    (output/'plan-before-reparse.json').write_text(json.dumps(dict(only='Root/slash-bass Unicode accidentals to pinned library modifiers; chord quality untouched',glyphs=glyph_map(),all_declarations=sum(len(s['rows']) for s in sources),frozen=frozen,verified_cached_input_core_library=checked),indent=2),encoding='utf-8')
    rows=[]
    for source in sources:
        for old in source['rows']:
            raw=old['declaration']['literal_text'];without_adapter=parse_symbol(raw)
            if without_adapter!=old['parser_interpretation']:raise ValueError('Unexpected baseline parser change; retain and investigate')
            normalized,trace=normalize_roots(raw);parsed=parse_symbol(normalized)
            contexts=[]
            for context in old['scored_harmonic_contexts']:
                labels=context['all_clock_labels']
                comparisons=None if labels is None or parsed['status']!='PARSED_LIBRARY_INTERPRETATION' else [dict(label=l,root_agrees=l['root_pc']==parsed['root_pc'],pc_set_agrees={(l['root_pc']+d)%12 for d in l['formula']}==set(parsed['pitch_classes'])) for l in labels]
                contexts.append(dict(scope=context['scope'],request=context['request'],status=context['status'],all_clock_labels=labels,comparisons=comparisons))
            rows.append(dict(source=source['capture'],declaration=old['declaration'],parser_input=normalized,transformation_trace=trace,
                lexical_inverse_exact=restore_roots(normalized,trace)==raw,baseline_parser=old['parser_interpretation'],parser_interpretation=parsed,
                declaring_part_nominal_overlap=old['declaring_part_nominal_overlap'],ensemble_nominal_overlap=old['ensemble_nominal_overlap'],
                part_symbol_comparison=set_comparison(old['declaring_part_nominal_overlap'],parsed),ensemble_symbol_comparison=set_comparison(old['ensemble_nominal_overlap'],parsed),scored_harmonic_contexts=contexts))
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items()) and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in checked.items())
    report=dict(status='COMPLETED_FROZEN_ENCODING_EXPERIMENT' if unchanged and all(r['lexical_inverse_exact'] for r in rows) else 'FAIL',unchanged=unchanged,
        declarations=len(rows),changed_parser_inputs=sum(bool(r['transformation_trace']) for r in rows),parser_status_counts=dict(Counter(r['parser_interpretation']['status'] for r in rows)),
        part_pc_comparisons=dict(Counter(r['part_symbol_comparison']['status'] for r in rows)),
        scope='Lexical encoding inverse only; NOT new musical-tier inverse, chord accuracy or rewritten source')
    (output/'all-comparisons.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('baseline',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=run(a.baseline,a.output);print(json.dumps(r));raise SystemExit(0 if r['status']=='COMPLETED_FROZEN_ENCODING_EXPERIMENT' else 1)
