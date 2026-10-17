"""Deterministic reference release, not a probability or forced difference target."""
import hashlib


def released(key, strength):
    if not isinstance(strength, int) or not 0 <= strength <= 100:
        raise ValueError('Freedom must be an integer from 0 to 100')
    # A fixed ordering gives nested unlocked subsets as freedom increases.
    rank = int.from_bytes(hashlib.sha256(str(key).encode()).digest()[:8], 'big') / 2**64
    return strength == 100 or strength > 0 and rank < strength / 100


def choose(reference, proposal, key, strength):
    return proposal if released(key, strength) else reference
