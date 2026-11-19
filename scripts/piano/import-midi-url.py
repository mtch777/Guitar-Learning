#!/usr/bin/env python3
"""Import a user-provided, directly downloadable MIDI file into the piano library.

This does not access MuseScore's internal API or generate authentication tokens.
"""
import argparse
import hashlib
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 12 * 1024 * 1024
ALLOWED_HOSTS = {"s3w.musescore.com", "raw.githubusercontent.com"}


def validate_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Use a direct HTTPS MIDI download URL from an allowed host.")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("The download URL is invalid.")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("Redirected downloads are not supported.")


def download_midi(value):
    request = urllib.request.Request(validate_url(value), headers={"User-Agent": "Guitar-Learning-MIDI-Importer/1.0"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        if int(response.headers.get("Content-Length", "0")) > MAX_BYTES:
            raise ValueError("MIDI file exceeds 12 MB.")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or not data.startswith(b"MThd"):
        raise ValueError("The URL did not return a supported MIDI file (12 MB maximum).")
    return data


def import_bytes(data, directory):
    from music21 import converter
    if not data.startswith(b"MThd") or len(data) > MAX_BYTES:
        raise ValueError("Invalid MIDI file.")
    digest = hashlib.sha256(data).hexdigest()
    stem = f"midi-{digest}"
    uploads = directory / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    midi_path = uploads / f"{stem}.mid"
    if not midi_path.exists():
        midi_path.write_bytes(data)
    xml_path = uploads / f"{stem}.musicxml"
    if not xml_path.exists():
        with tempfile.TemporaryDirectory(prefix="piano-midi-") as temporary:
            score = converter.parse(str(midi_path))
            score.write("musicxml", fp=str(xml_path))
    print(f"Imported {stem}.musicxml ({len(data)} MIDI bytes)")
    return xml_path


def import_midi(url, directory):
    return import_bytes(download_midi(url), directory)


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--file", type=Path)
    parser.add_argument("--library", type=Path, default=Path("public/piano/learning-songs"))
    args = parser.parse_args()
    if args.file:
        import_bytes(args.file.read_bytes(), args.library)
    else:
        import_midi(args.url, args.library)


if __name__ == "__main__":
    main()
