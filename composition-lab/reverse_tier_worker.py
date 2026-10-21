"""Isolated reverse worker: only upper representation, shared equations, stdlib."""
import json
from pathlib import Path
import sys


def install_guard(permitted,runtime,access):
    def audit(event,args):
        if event=="open":
            raw=args[0];mode=args[1];flags=args[2]
            path=Path(raw).resolve() if not isinstance(raw,int) else None
            writing=(isinstance(mode,str) and any(c in mode for c in "wax+")) or bool(flags & 3)
            role=permitted.get(path)
            allowed=role=="write" if writing else role in {"read","write"} or path is not None and path.is_relative_to(runtime)
            access.append(dict(path=str(path) if path is not None else "file_descriptor",mode=mode,flags=flags,operation="write" if writing else "read",allowed=allowed))
            if not allowed:raise PermissionError("Outside inverse read/write allowlist: "+str(path))
        elif event in {"subprocess.Popen","os.system"} or event.startswith("socket."):raise PermissionError("No source/network/subprocess fallback")
    sys.addaudithook(audit)


def main():
    source,destination,trace=map(lambda p:Path(p).resolve(),sys.argv[1:4])
    code=Path(__file__).resolve().parent
    if destination.exists() or trace.exists():raise ValueError("Fresh outputs required")
    permitted={source:"read",destination:"write",trace:"write",Path(__file__).resolve():"read",code/"reversible_relationships.py":"read",code/"reversible_topology.py":"read",code/"reversible_positions.py":"read",code/"reversible_annotations.py":"read",code/"reversible_ties.py":"read",code/"reversible_voicings.py":"read",code/"reversible_temporal.py":"read",code/"reversible_song.py":"read"}
    runtime=Path(sys.base_prefix).resolve();access=[]
    sys.dont_write_bytecode=True;install_guard(permitted,runtime,access);sys.path.insert(0,str(code))
    value=json.loads(source.read_text(encoding="utf-8"));schema=value.get("schema")
    if schema=="owned-song-stages/1":
        from reversible_song import decode
        owned=decode(value);annotations=owned["music"];positions=annotations["physical"]
        output=dict(owned_song=owned,temporal=owned["temporal"],annotations=annotations,physical=positions)
    elif schema in {"voicing-constrained-song/1","tie-constrained-song/1","relative-annotated-topology/1"}:
        if schema=="voicing-constrained-song/1":from reversible_voicings import decode
        elif schema=="tie-constrained-song/1":from reversible_ties import decode
        else:from reversible_annotations import decode
        annotations=decode(value);positions=annotations["physical"]
        output=dict(annotations=annotations,physical=positions)
    elif schema=="positioned-relative-topology/1":
        from reversible_positions import decode
        positions=decode(value);output=dict(physical=positions)
    else:positions=None
    if positions is not None:
        from reversible_positions import event_view
        restored=event_view(positions);event_pitches={r["id"]:r["pitch"] for r in restored}
        structural=positions["topology"]
        output["topology"]=dict(structural,notes=[dict(n,base_pitch=event_pitches[n["id"]]) for n in structural["notes"]])
        output.update(scope=schema,events=restored)
    elif schema=="relative-beat-topology/1":
        from reversible_topology import decode,event_view
        structural=decode(value);restored=event_view(structural)
        output=dict(scope=schema,topology=structural,events=restored)
    else:
        from reversible_relationships import decode
        restored=decode(value);output=dict(scope=value["scope"],events=restored)
    destination.write_text(json.dumps(output,indent=2),encoding="utf-8")
    trace.write_text(json.dumps(dict(policy="Enforced Python I/O allowlist, not an OS security sandbox",open_events=access,permitted_files={str(k):v for k,v in permitted.items()},runtime_root=str(runtime)),indent=2),encoding="utf-8")
    print(json.dumps(dict(events=len(restored),status="reconstructed_declared_fields")))


if __name__=="__main__":main()
