"""Generate a tiny original melody for the GitHub Actions MIDI importer test."""
from pathlib import Path


def variable_length(value):
    chunks = [value & 0x7F]
    while value >> 7:
        value >>= 7
        chunks.insert(0, (value & 0x7F) | 0x80)
    return bytes(chunks)


def make_midi():
    notes = (60, 64, 67)
    track = bytearray(b"\x00\xff\x51\x03\x07\xa1\x20")
    for note in notes:
        track += bytes([0x00, 0x90, note, 96])
        track += variable_length(480) + bytes([0x80, note, 0])
    track += b"\x00\xff\x2f\x00"
    return b"MThd" + (6).to_bytes(4, "big") + bytes.fromhex("0000000101e0") + b"MTrk" + len(track).to_bytes(4, "big") + track


if __name__ == "__main__":
    Path("/tmp/piano-import-smoke.mid").write_bytes(make_midi())
