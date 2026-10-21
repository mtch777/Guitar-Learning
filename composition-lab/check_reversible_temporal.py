"""Independent raw declaration oracle. Producer decode only; no extraction/encode."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from reversible_temporal import decode


def typed(value):
    kind = type(value).__name__
    if value is None:
        return {"type": kind, "value": None}
    if type(value) in (int, float):
        return {"type": kind, "value": str(Fraction(str(value)))}
    return {"type": kind, "value": value}


def expected(capture):
    metadata = json.loads((capture / "metadata.json").read_text(encoding="utf-8-sig"))
    records, unsupported = [], []

    def scalar_fields(obj, owner):
        fields = {}
        for key, value in obj.items():
            if type(value) in (int, float, bool, str, type(None)):
                fields[key] = typed(value)
            else:
                unsupported.append({"owner": owner, "field": key, "source_type": type(value).__name__})
        return fields

    for path in sorted(capture.glob("track-*.json")):
        track = json.loads(path.read_text(encoding="utf-8-sig"))
        part = f"part:{metadata['songId']}:{track['partId']}"
        for bar, measure in enumerate(track.get("measures", []), 1):
            owner = f"measure:{metadata['songId']}:{track['partId']}:{bar}"
            if "signature" in measure:
                signature = measure["signature"]
                if type(signature) is list and len(signature) == 2 and all(type(x) in (int, float) for x in signature):
                    records.append({"id": "meter:" + owner, "owner": owner, "kind": "meter", "fields": {"numerator": typed(signature[0]), "denominator": typed(signature[1])}})
                else:
                    unsupported.append({"owner": owner, "field": "signature", "source_type": type(signature).__name__})
            for voice, data in enumerate(measure.get("voices", [])):
                for beat, data in enumerate(data.get("beats", [])):
                    if "tempo" not in data:
                        continue
                    owner = f"beat:{metadata['songId']}:{track['partId']}:{bar}:{voice}:{beat}"
                    if type(data["tempo"]) is dict:
                        records.append({"id": "tempo:" + owner, "owner": owner, "kind": "beat_tempo", "fields": scalar_fields(data["tempo"], owner)})
                    else:
                        unsupported.append({"owner": owner, "field": "tempo", "source_type": type(data["tempo"]).__name__})
        for ordinal, entry in enumerate((track.get("automations") or {}).get("tempo", [])):
            ident = f"tempo:{part}:{ordinal}"
            if type(entry) is dict:
                records.append({"id": ident, "owner": part, "kind": "automation_tempo", "fields": scalar_fields(entry, ident)})
            else:
                unsupported.append({"owner": ident, "field": "tempo", "source_type": type(entry).__name__})
    return {"schema": "temporal-source-observations/1", "records": records, "unsupported": unsupported}


def check(capture, upper):
    raw = expected(capture)
    reconstructed = decode(json.loads(upper.read_text(encoding="utf-8-sig")))
    if reconstructed != raw:
        raise ValueError("Independent raw temporal declarations differ")
    return {"capture": str(capture), "upper": str(upper), "upper_sha256": hashlib.sha256(upper.read_bytes()).hexdigest(), "counts": dict(Counter(r["kind"] for r in raw["records"])), "unsupported": len(raw["unsupported"]), "status": "pass"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("upper", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.capture, args.upper)))

