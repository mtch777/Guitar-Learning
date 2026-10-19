"""Build a sealed private relationship profile from existing accepted analysis.

No score download, detector execution, inference, model tuning or listening.
Optional program JSON is a list of {song_id, part_id, program} records.
"""
import argparse
import hashlib
import json
from pathlib import Path

import artist_profiles
import artist_relationship_profiles
import relationship_profile_evaluation


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    def reject_constant(value):
        raise ValueError('Nonfinite JSON constant: '+value)
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON object key: '+key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_pairs,
                      parse_constant=reject_constant)


def run(report_path, pedal_path, output, artist, program_path=None):
    output = Path(output).resolve()
    if 'local-artifacts' not in output.parts or output.exists():
        raise ValueError('Fresh private local-artifacts directory required')
    inputs = [Path(report_path).resolve(), Path(pedal_path).resolve()]
    if program_path is not None:
        inputs.append(Path(program_path).resolve())
    code = [Path(__file__).resolve()] + [Path(m.__file__).resolve() for m in
        (artist_profiles, artist_relationship_profiles, relationship_profile_evaluation)]
    paths = list(dict.fromkeys(inputs + code))
    frozen = {str(p): sha(p) for p in paths}
    report = read_json(inputs[0])
    accepted = read_json(inputs[1])
    programs = {}
    if program_path is not None:
        records = read_json(inputs[2])
        if not isinstance(records, list):
            raise ValueError('Program record list required')
        for row in records:
            key = row['song_id'], row['part_id']
            if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in key):
                raise ValueError('Nonnegative integer program identities required')
            program = row['program']
            if key in programs or isinstance(program, bool) or not isinstance(program, int) or not 0 <= program <= 127:
                raise ValueError('Unique track identities and MIDI programs 0–127 required')
            programs[key] = program
        source_tracks = {(s['song_id'], t['part_id']) for s in report['songs'] for t in s['tracks']}
        if set(programs)-source_tracks:
            raise ValueError('Program identity outside source report')
    model = artist_relationship_profiles.build_relationship_profile(report, accepted, artist, programs)
    held = artist_relationship_profiles.build_relationship_profile(report, accepted, artist, programs, partition='held_out')
    if not model['training_songs'] or not held['observed_songs']:
        raise ValueError('Nonempty development and held-out partitions required')
    if any(not p['coverage'].get('attack_groups') or not p['tables'] for p in (model, held)):
        raise ValueError('No eligible observations in development or held-out partition')
    support = artist_relationship_profiles.heldout_support(model, held)
    prediction = relationship_profile_evaluation.evaluate_boolean_relationships(model, held)
    if not any(r['weighted_eligible_mass'] > 0 for r in prediction['results']):
        raise ValueError('No supported Boolean prediction opportunities')
    if frozen != {str(p): sha(p) for p in paths}:
        raise ValueError('Input or implementation changed during profile build')
    # Preserve partial failures; completion exists only after all writes/checks.
    output.mkdir(parents=True, exist_ok=False)
    products = {'model.json': model, 'heldout-descriptive.json': held,
                'heldout-support.json': support, 'prediction-diagnostic.json': prediction}
    for name, value in products.items():
        (output / name).write_text(json.dumps(value, separators=(',', ':')), encoding='utf-8')
    if frozen != {str(p): sha(p) for p in paths}:
        raise ValueError('Input or implementation changed before completion')
    manifest = dict(schema='sealed-written-relationship-build-v1', complete=True,
        artist=artist, frozen_inputs_and_code=frozen,
        products={name: sha(output/name) for name in products},
        development_scores=len(model['training_songs']),
        development_families=len(model['training_families']),
        heldout_scores=len(held['observed_songs']), heldout_families=len(held['observed_families']),
        coverage=model['coverage'], musical_acceptance=False,
        limitations=['Accepted input files are hashed, not independently authenticated source revisions',
                     'Previously examined held-out split; no musical or artist-feel acceptance'])
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('accepted_pedals', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--artist', required=True)
    parser.add_argument('--programs', type=Path)
    args = parser.parse_args()
    result = run(args.report, args.accepted_pedals, args.output, args.artist, args.programs)
    print(json.dumps({k:v for k,v in result.items() if k not in ('frozen_inputs_and_code','products')}))
