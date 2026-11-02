"""Bounded diagnosis only: no production source edits, no source notation in logs."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
import types

EXPECTED = {1817932: 9885745, 993568: 1320385, 1511882: 4540687,
            6028811: 8322146, 4248474: 5561199, 3165226: 4189601}
EXPECTED_EXPANDER_BLOB = 'dbd90c8e280df81001e3120f66860306e07d7bc9'


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def cycle_mismatches(regions):
    result = []
    for r in regions:
        for c in r['added_cycles']:
            for key, expected in [('call_members', 'call'), ('response_members', 'response')]:
                for occurrence in c[key]:
                    actual = r['roles'].get(occurrence)
                    if actual != expected:
                        result.append(dict(occurrence=occurrence, expected=expected, actual=actual,
                                           call_start_q=c['call_start_q'], return_q=c['return_q']))
    return result


def merge_overwrites(regions):
    """Observe exactly the chronological overlap/last-writer rule, without editing inputs."""
    merged = []
    changes = []
    for r in sorted(regions, key=lambda v: (F(v['start_q']), F(v['end_q']))):
        if merged and F(r['start_q']) < F(merged[-1]['end_q']):
            previous = merged[-1]
            for occurrence, role in r['roles'].items():
                old = previous['roles'].get(occurrence)
                if old is not None and old != role:
                    changes.append(dict(occurrence=occurrence, before=old, after=role,
                        left_seed_ids=previous['seed_ids'][:], right_seed_ids=r['seed_ids'][:],
                        overlap_start_q=r['start_q'],
                        overlap_end_q=str(min(F(previous['end_q']), F(r['end_q'])))))
            previous['roles'].update(r['roles'])
            previous['end_q'] = str(max(F(previous['end_q']), F(r['end_q'])))
            previous['seed_ids'] = sorted(set(previous['seed_ids'] + r['seed_ids']))
        else:
            merged.append(deepcopy(r))
    return changes


def inspect_track(production, evaluator, single_report, analyses):
    traces = []
    original_merge = production._merge
    original_expand = evaluator.expand_phrases
    def observed_expand(rows, seeds, **kwargs):
        snapshots = []
        def observe(regions):
            snapshots.append(deepcopy(regions))
            return original_merge(regions)
        production._merge = observe
        try:
            phrases = production.expand_phrases(rows, seeds, **kwargs)
        finally:
            production._merge = original_merge
        premerge = snapshots[1] if len(snapshots) > 1 else []
        before = cycle_mismatches(premerge)
        after = cycle_mismatches(phrases)
        overwrites = merge_overwrites(premerge)
        overwritten = {r['occurrence'] for r in overwrites}
        traces.append(dict(input_seeds=len(seeds), merge_passes=len(snapshots),
            initial_merge_role_overwrites=len(merge_overwrites(snapshots[0])) if snapshots else 0,
            premerge_added_cycle_mismatches=len(before), final_added_cycle_mismatches=len(after),
            merge_role_overwrites=len(overwrites),
            every_final_mismatch_was_overwritten=all(r['occurrence'] in overwritten for r in after),
            mismatch_examples=after[:12], overwrite_examples=overwrites[:12]))
        return phrases
    evaluator.expand_phrases = observed_expand
    try:
        evaluator.evaluate(single_report, analyses)
        result = dict(status='pass')
    except Exception as exc:
        frames = traceback.extract_tb(exc.__traceback__)
        result = dict(status='failed', error_type=type(exc).__name__, error=str(exc),
                      failure_file=Path(frames[-1].filename).name, failure_line=frames[-1].lineno)
    finally:
        evaluator.expand_phrases = original_expand
        production._merge = original_merge
    return dict(result, traces=traces)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--song-id', type=int, choices=sorted(EXPECTED), required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    if 'local-artifacts' not in out.parts or out.exists():
        p.error('Use a fresh private local-artifacts directory')
    out.mkdir(parents=True)
    summary = dict(song_id=args.song_id, expected_revision=EXPECTED[args.song_id],
                   mode='diagnosis_only', started_utc=datetime.now(timezone.utc).isoformat())
    try:
        root = Path(__file__).resolve().parents[2] / 'composition-lab'
        sys.path.insert(0, str(root))
        sys.path.insert(0, os.environ.get('SONGSTERR_CLIENT_ROOT', '/tmp/songsterr-dl'))
        from songsterr_dl.client import SongsterrClient
        import run_tiered_catalog as runner
        import build_tiered_song as builder
        import pedal_expansion as production
        import evaluate_pedal_expansion as evaluator
        capture = out / 'capture'
        with SongsterrClient(timeout=30) as client:
            metadata = client.meta(args.song_id)
            write(capture / 'metadata.json', metadata)
            runner.resolve_catalog_identity(args.song_id, metadata, client)
            if metadata['revisionId'] != EXPECTED[args.song_id]:
                raise ValueError('Upstream revision changed; no historical replay claim permitted')
            for part in range(len(metadata['tracks'])):
                write(capture / f'track-{part}.json', client.track(args.song_id,
                      metadata['revisionId'], metadata['image'], part))
        summary.update(revision_id=metadata['revisionId'], artist=metadata['artist'], title=metadata['title'])
        before_hashes = {v.name: hashlib.sha256(v.read_bytes()).hexdigest() for v in capture.iterdir()}
        code_path = root / 'pedal_expansion.py'
        code = code_path.read_bytes()
        blob = hashlib.sha1(f'blob {len(code)}\0'.encode() + code).hexdigest()
        if blob != EXPECTED_EXPANDER_BLOB:
            raise ValueError('Expander source changed; stop rather than test an unreviewed candidate')
        summary['expander_blob'] = blob
        documents = builder.source_capture(capture)
        report = builder.analyze_capture(documents)
        song = report['songs'][0]
        seeds = []
        # Same evidence construction as build_tiered_song.existing_outputs.
        for track in song['tracks']:
            if not track['guitar_or_bass'] or not track['temporal_relationships_eligible']:
                continue
            for section in sorted({r['section_start'] for r in track['rows']}):
                rows = [r for r in track['rows'] if r['section_start'] == section]
                result = builder.analyze_evidence(rows)
                seeds.append(dict(song_id=song['song_id'], part_id=track['part_id'], section_start=section,
                    **{k: result[k] for k in ('accepted', 'anchor_pitches', 'roles', 'cycles', 'reason')}))
        tracks = []
        for track in song['tracks']:
            single = dict(report, songs=[dict(song, tracks=[track])])
            tracks.append(dict(part_id=track['part_id'], **inspect_track(production, evaluator, single, seeds)))
        summary['baseline_tracks'] = tracks
        failing = [t for t in tracks if t['status'] == 'failed']
        summary['baseline_failed_tracks'] = len(failing)
        summary['all_failures_at_original_response_assertion'] = bool(failing) and all(
            t['error_type'] == 'AssertionError' and t['failure_file'] == 'evaluate_pedal_expansion.py'
            and t['failure_line'] == 42 for t in failing)
        summary['overlap_root_confirmed_on_every_failed_track'] = bool(failing) and all(
            t['traces'] and all(s['initial_merge_role_overwrites'] == 0
                and s['premerge_added_cycle_mismatches'] == 0 and s['final_added_cycle_mismatches'] > 0
                and s['merge_role_overwrites'] > 0 and s['every_final_mismatch_was_overwritten']
                for s in t['traces']) for t in failing)
        text = code.decode('utf-8')
        old = 'preceding=original[i-1] if i else None'
        if text.count(old) != 1:
            raise ValueError('Expected candidate substitution does not match exactly once')
        candidate = types.ModuleType('diagnostic_candidate')
        exec(compile(text.replace(old, 'preceding=phrases[i-1] if i else None'),
                     'diagnostic_candidate', 'exec'), candidate.__dict__)
        original_expand = evaluator.expand_phrases
        evaluator.expand_phrases = candidate.expand_phrases
        try:
            checked = evaluator.evaluate(report, seeds)
            summary['candidate_expansion_validation'] = dict(status='pass', counts=checked['counts'])
        except Exception as exc:
            summary['candidate_expansion_validation'] = dict(status='failed', error_type=type(exc).__name__, error=str(exc))
        finally:
            evaluator.expand_phrases = original_expand
        summary['capture_bytes_unchanged'] = before_hashes == {
            v.name: hashlib.sha256(v.read_bytes()).hexdigest() for v in capture.iterdir()}
        summary['production_expander_bytes_unchanged'] = code_path.read_bytes() == code
        summary['full_tiered_pipeline_retested'] = False
        summary['status'] = 'diagnosed' if (summary['all_failures_at_original_response_assertion']
            and summary['overlap_root_confirmed_on_every_failed_track']
            and summary['candidate_expansion_validation']['status'] == 'pass'
            and summary['capture_bytes_unchanged'] and summary['production_expander_bytes_unchanged']) else 'needs_review'
    except Exception as exc:
        summary.update(status='investigation_error', error_type=type(exc).__name__, error=str(exc))
        (out / 'private-traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
    summary['completed_utc'] = datetime.now(timezone.utc).isoformat()
    write(out / 'diagnosis.json', summary)
    print('DIAGNOSIS_JSON ' + json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary['status'] == 'diagnosed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
