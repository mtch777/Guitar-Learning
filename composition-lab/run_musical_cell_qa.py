"""Bundle the actual T3 relation and existing T2 inverse for denied-source QA."""
import hashlib
from run_connected_tier2_qa import bundle as tier2_bundle


def bundle(root, *, boundary='source'):
    if boundary not in ('source','tier2'):
        raise ValueError('Explicit source or preceding-tier boundary required')
    code,hashes=tier2_bundle(root)
    name='musical_cell_development'
    source=(root/(name+'.py')).read_text(encoding='utf-8-sig')
    hashes[name]=hashlib.sha256(source.encode()).hexdigest()
    code+=f"_m=types.ModuleType({name!r});sys.modules[{name!r}]=_m\nexec(compile({source!r},{name!r},'exec'),_m.__dict__)\n"
    if boundary=='source':
        code+="reconstruct=sys.modules['musical_cell_development'].reconstruct\n"
    else:
        # The individual tier boundary calls the SAME production expansion.
        # It does not realize T1 or accept a hidden preceding-tier payload.
        code+="def reconstruct(upper, controls):\n if controls != {'variation': 0}: raise ValueError('Exact current tier boundary only')\n return sys.modules['musical_cell_development'].expand(upper)\n"
    return code,hashes
