"""Source-resource provenance QA only; no musical inference or time alignment."""
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs)


def audit(capture, baseline_path, supplemental_metadata=None, supplemental_text=None, claims=None):
    """Compare actual bytes against an independently retained baseline.

    Baseline authenticity is an external obligation; its path/hash is recorded.
    Supplemental timing is UNKNOWN: this guard implements no alignment verifier.
    """
    capture = Path(capture)
    issues = []
    result = dict(scope='Source-resource provenance only; NOT harmonic interpretation or inverse',
                  status='FAIL', issues=issues, alignment='UNKNOWN', timed_truth_accepted=False,
                  supplement_status='UNAVAILABLE', baseline_authenticity='EXTERNAL_OBLIGATION')
    try:
        baseline_path = Path(baseline_path)
        result['baseline_sha256'] = digest(baseline_path)
        baseline = load(baseline_path)
        expected = baseline['original_hashes']
        if not isinstance(expected, dict) or 'metadata.json' not in expected or not any(k.startswith('track-') for k in expected):
            raise ValueError('Incomplete original baseline inventory')
        if any(Path(k).name != k or not isinstance(v, str) or len(v) != 64 for k, v in expected.items()):
            raise ValueError('Invalid baseline file/hash')
        actual_files = {p.name for p in capture.iterdir() if p.is_file()}
        if actual_files != set(expected):
            issues.append('Original file set differs from baseline')
        hashes = {name: digest(capture / name) for name in expected if (capture / name).is_file()}
        result['original_hashes'] = hashes
        if hashes != expected:
            issues.append('Original source bytes differ from baseline')
        source = load(capture / 'metadata.json')
        for key in ('songId', 'artistId', 'revisionId'):
            if type(source.get(key)) is not int or source[key] < 0:
                issues.append('Invalid notation identity: ' + key)
        for key in ('artist', 'title'):
            if type(source.get(key)) is not str or not source[key]:
                issues.append('Invalid notation identity: ' + key)
        result['notation_revision'] = source.get('revisionId')
        result['source_has_chords'] = source.get('hasChords')
        if 'hasChords' in source and type(source['hasChords']) is not bool:
            issues.append('Invalid hasChords availability flag')
        claims = {} if claims is None else claims
        allowed = {'availability_as_timed_truth', 'supplement_as_timed_truth', 'automatic_time_alignment'}
        if not isinstance(claims, dict) or set(claims) - allowed:
            raise ValueError('Unsupported claim fields')
        for key, value in claims.items():
            if type(value) is not bool:
                issues.append('Invalid claim type: ' + key)
            elif value:
                issues.append('Unsupported timed-truth/alignment claim: ' + key)
        if (supplemental_metadata is None) != (supplemental_text is None):
            issues.append('Incomplete supplemental resource pair')
        elif supplemental_metadata is not None:
            paths = [Path(supplemental_metadata).resolve(), Path(supplemental_text).resolve()]
            if paths[0] == paths[1] or paths[0].name == paths[1].name:
                raise ValueError('Supplemental resources require distinct canonical paths and baseline identities')
            if any(not p.is_file() for p in paths):
                raise FileNotFoundError('Supplemental resource unavailable')
            result['supplement_status'] = 'AVAILABLE_UNALIGNED'
            seals = baseline.get('separate_resource_hashes', {})
            supplemental_hashes = {p.name: digest(p) for p in paths}
            result['supplemental_hashes'] = supplemental_hashes
            for name, actual in supplemental_hashes.items():
                if name not in seals or seals[name] != actual:
                    issues.append('Supplement bytes unsealed/differ: ' + name)
            supplement = load(paths[0])
            for key in ('songId', 'artistId', 'artist', 'title'):
                if key not in source or key not in supplement or type(source[key]) is not type(supplement[key]) or source[key] != supplement[key]:
                    issues.append('Supplement identity differs: ' + key)
            revision = supplement.get('chordsRevisionId')
            if type(revision) is not int or revision < 0:
                issues.append('Invalid independent chord revision')
            result['chord_revision'] = revision
            # Different revision values are valid; no equality/alignment inferred.
            result['supplement_text_bytes'] = paths[1].stat().st_size
        if digest(baseline_path) != result['baseline_sha256']:
            issues.append('Baseline changed during audit')
        if {p.name for p in capture.iterdir() if p.is_file()} != actual_files or any(not (capture/name).is_file() or digest(capture/name) != value for name,value in hashes.items()):
            issues.append('Source changed during audit')
        if supplemental_metadata is not None and supplemental_text is not None and any(not p.is_file() or digest(p) != supplemental_hashes[p.name] for p in paths):
            issues.append('Supplement changed during audit')
        result['status'] = 'FAIL' if issues else 'PASS_PROVENANCE_ONLY'
    except Exception as exc:
        issues.append(type(exc).__name__ + ': ' + str(exc))
    return result
