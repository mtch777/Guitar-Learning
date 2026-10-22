"""Reproduce the versioned theory vocabulary; no song data is read."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def definitions():
    import music21
    from music21 import harmony
    forms = tuple((kind, tuple(sorted({p.pitchClass for p in harmony.ChordSymbol(root="C", kind=kind).pitches})))
                  for kind in harmony.CHORD_TYPES)
    provenance = dict(source="music21.harmony.CHORD_TYPES", version=music21.__version__,
                      forms_sha256=hashlib.sha256(json.dumps(forms, separators=(",", ":")).encode()).hexdigest(),
                      vocabulary_scope="Published Western chord-kind definitions; not exhaustive musical harmony",
                      candidate_rule="Exact observed pitch-class set; all twelve roots; singleton excluded")
    return forms, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    path = Path(__file__).with_name("musical_tier2.py")
    text = path.read_text(encoding="utf-8")
    forms, provenance = definitions()
    if args.write:
        lines = text.splitlines()
        lines = ["THEORY_FORMS = " + repr(forms) if line.startswith("THEORY_FORMS = ") else
                 "THEORY_PROVENANCE = " + repr(provenance) if line.startswith("THEORY_PROVENANCE = ") else line for line in lines]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        assignments = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(text).body
                       if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                       and n.targets[0].id in {"THEORY_FORMS", "THEORY_PROVENANCE"}}
        assert assignments["THEORY_FORMS"] == forms and assignments["THEORY_PROVENANCE"] == provenance
    print(json.dumps(dict(theory_kinds=len(forms), source_version=provenance["version"], verified=True)))


if __name__ == "__main__":
    main()
