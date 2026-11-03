"""Actual material-use inverse in the existing audited source-denied worker."""
from run_support_arrangement_qa import bundle as arrangement_bundle


def bundle(root, *, boundary='source'):
    if boundary not in ('source', 'tier2'):
        raise ValueError('Declared source or preceding T2 boundary required')
    code, hashes = arrangement_bundle(root, boundary='tier2')
    if boundary == 'source':
        code += "def reconstruct(upper, controls):\n return sys.modules['support_material_uses'].reconstruct(upper, controls)\n"
    return code, hashes
