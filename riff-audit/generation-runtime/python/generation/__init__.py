"""Selection-scoped exploratory whole-span rhythm API, separate from frozen models."""
from .engine import generate, generate_batch, LAW_VERSION
from .evidence import build_selection_model, digest
from .assessment import assess
__all__=['build_selection_model','generate','generate_batch','assess','digest','LAW_VERSION']

from .player_adapter import to_reference_payload
__all__.append('to_reference_payload')
