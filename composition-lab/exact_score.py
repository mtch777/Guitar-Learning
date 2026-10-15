"""Access the checkpoint rational extractor without legacy-module name collisions."""
from importlib import import_module

_extract = import_module('checkpoints.2026-10-14.extract')
_events = import_module('checkpoints.2026-10-14.music_events')
extract_score = _extract.extract_score
validate_events = _events.validate_events
meter_length = _events.meter_length
