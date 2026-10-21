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
    permitted={source:"read",destination:"write",trace:"write",Path(__file__).resolve():"read",code/"reversible_relationships.py":"read",code/"reversible_topology.py":"read"}
    runtime=Path(sys.base_prefix).resolve();access=[]
    sys.dont_write_bytecode=True;install_guard(permitted,runtime,access);sys.path.insert(0,str(code))
    from reversible_relationships import decode
    value=json.loads(source.read_text(encoding="utf-8"))
    if value.get("schema")=="relative-beat-topology/1":
        from reversible_topology import decode as decode_topology,event_view
        topology=decode_topology(value);restored=event_view(topology)
        output=dict(scope="normalized_beat_voice_rest_grace_topology_and_base_pitch",topology=topology,events=restored)
    else:
        restored=decode(value);output=dict(scope=value["scope"],events=restored)
    destination.write_text(json.dumps(output,indent=2),encoding="utf-8")
    trace.write_text(json.dumps(dict(policy="Enforced Python I/O allowlist, not an OS security sandbox",open_events=access,permitted_files={str(k):v for k,v in permitted.items()},runtime_root=str(runtime)),indent=2),encoding="utf-8")
    print(json.dumps(dict(events=len(restored),status="reconstructed_declared_fields")))


if __name__=="__main__":main()
