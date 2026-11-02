"""Local capture analysis, synthetic demos and source-preservation checks."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from .engine import analyze, NAMES
from .examples import example_scores
from .songsterr import load_capture


def _write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write('\n')


def _hashes(capture):
    paths = [capture/'metadata.json'] + sorted(capture.glob('track-*.json'))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _code_hashes():
    root = Path(__file__).resolve().parent
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.py'))}


def _output(value, capture=None):
    path = Path(value).resolve()
    if path.exists():
        raise ValueError('Output directory already exists; choose a fresh destination')
    if capture is not None:
        if path == capture or capture in path.parents:
            raise ValueError('Output cannot be inside the source capture')
        if not any(p.name.lower() in ('.local', 'local-artifacts') for p in path.parents):
            raise ValueError('Source-derived output requires a .local or local-artifacts ancestor')
    return path


def verify_capture(capture, score):
    """Independent source traversal: exact occurrence/pitch/witness checks.

    This checks source extraction, not whether the inferred key is correct.
    Timing checks use the adapter's declared bar geometry as their reference;
    they independently check beat accumulation within each source voice.
    """
    rows = {e['id']: e for e in score['events']}
    observed, failures = set(), []
    for path in sorted(capture.glob('track-*.json')):
        part = json.loads(path.read_text(encoding='utf-8-sig'))
        for mi, measure in enumerate(part['measures']):
            for vi, voice in enumerate(measure.get('voices', [])):
                local = F(0)
                for bi, beat in enumerate(voice.get('beats', [])):
                    for ni, note in enumerate(beat.get('notes', [])):
                        if note.get('rest') is True:
                            continue
                        ident = f"track:{part['partId']}:bar:{mi+1}:voice:{vi}:beat:{bi}:note:{ni}"
                        observed.add(ident)
                        row = rows.get(ident)
                        if row is None or row['raw_note'] != note or row['raw_beat'] != {k:v for k,v in beat.items() if k != 'notes'}:
                            failures.append(dict(id=ident, reason='missing_or_changed_source_witness'))
                            continue
                        if row['eligible']:
                            pitch = part['tuning'][note['string']]+note['fret']+part.get('capo', 0)
                            if pitch != row['midi']:
                                failures.append(dict(id=ident, reason='pitch_differs'))
                            if local is not None and F(row['onset_q']) != F(score['bars'][mi]['start_q'])+local:
                                failures.append(dict(id=ident, reason='onset_differs'))
                            if F(row['duration_q']) != F(*beat['duration'])*4:
                                failures.append(dict(id=ident, reason='duration_differs'))
                    value = beat.get('duration')
                    grace = beat.get('graceNote')
                    valid = isinstance(value, list) and len(value) == 2 and all(type(v) is int and v > 0 for v in value)
                    if not valid or grace not in (None, False, True, 'beforeBeat', 'onBeat'):
                        local = None
                    elif local is not None and not grace:
                        whole = measure.get('rest') is True and voice.get('rest') is True and len(voice.get('beats', [])) == 1 and beat.get('rest') is True and beat.get('type') == 1 and value == [1,1] and beat.get('notes') and all(n.get('rest') is True for n in beat['notes'])
                        local += F(score['bars'][mi]['duration_q']) if whole else F(*value)*4
    if observed != set(rows):
        failures.append(dict(reason='occurrence_identity_set_differs', raw=len(observed), normalized=len(rows)))
    return dict(status='pass' if not failures else 'fail', source_nonrest_occurrences=len(observed),
                normalized_occurrences=len(rows), eligible_occurrences=sum(e['eligible'] for e in rows.values()),
                failures=failures, key_accuracy='not_evaluated',
                timing_scope='Independent within-voice accumulation, adapter-declared shared bar geometry')


def _summary(report):
    g = report['global']
    return dict(status=g['status'], center=NAMES[g['center']] if g['center'] is not None else None,
                mode=g['mode'], leading_candidates=[dict(tonic=c['tonic_name'], mode=c['mode'], score=c['score']) for c in g['candidates'][:3]],
                source_occurrences=report['coverage']['source_occurrences'],
                eligible_occurrences=report['coverage']['eligible_occurrences'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('analyze', 'examples', 'check-capture'):
        p = sub.add_parser(command)
        if command != 'examples':
            p.add_argument('capture', type=Path)
        p.add_argument('--output', required=True, type=Path)
        if command != 'check-capture':
            p.add_argument('--window-bars', type=int, default=4)
            p.add_argument('--top', type=int, default=8)
    args = parser.parse_args(argv)
    try:
        if args.command != 'check-capture' and (args.window_bars < 1 or not 1 <= args.top <= 108):
            raise ValueError('window-bars must be positive and top must be in 1..108')
        capture = args.capture.resolve() if args.command != 'examples' else None
        output = _output(args.output, capture)
        code = _code_hashes()
        if args.command == 'examples':
            results = {name: (score, analyze(score, args.window_bars, args.top)) for name, score in example_scores().items()}
            output.mkdir(parents=True)
            summaries = {}
            for name, (score, report) in results.items():
                target = output/name
                target.mkdir()
                _write(target/'events.json', score)
                _write(target/'report.json', report)
                _write(target/'manifest.json', dict(source='original_synthetic', code_sha256=code, configuration=report['configuration']))
                summaries[name] = _summary(report)
            _write(output/'summary.json', summaries)
            print(json.dumps(dict(output=str(output), examples=summaries), allow_nan=False))
            return 0
        before = _hashes(capture)
        score = load_capture(capture)
        verification = verify_capture(capture, score)
        report = analyze(score, args.window_bars, args.top) if args.command == 'analyze' else None
        unchanged = before == _hashes(capture)
        if not unchanged:
            raise ValueError('Source files changed during execution; analysis not saved')
        if code != _code_hashes():
            raise ValueError('Analysis code changed during execution; rerun with a stable version')
        output.mkdir(parents=True)
        _write(output/'verification.json', dict(verification, source_bytes_unchanged=unchanged))
        _write(output/'manifest.json', dict(source_file_sha256=before, code_sha256=code,
                                           configuration=report['configuration'] if report else None,
                                           source_bytes_unchanged=unchanged, source_selection='explicit_local_capture'))
        if report:
            _write(output/'events.json', score)
            _write(output/'report.json', report)
        print(json.dumps(dict(output=str(output), verification=verification,
                              summary=_summary(report) if report else None), allow_nan=False))
        return 0 if verification['status'] == 'pass' else 1
    except (ValueError, OSError, KeyError, TypeError, ZeroDivisionError) as error:
        parser.error(str(error))
