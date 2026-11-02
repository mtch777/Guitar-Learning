"""Bundle the actual material inverse through the existing denied-source runner."""
import hashlib
from run_musical_cell_qa import bundle as cell_bundle


def bundle(root, *, boundary='source'):
    if boundary not in ('source','tier3'):
        raise ValueError('Explicit source or preceding T3-profile boundary required')
    code,hashes=cell_bundle(root)
    name='musical_support_material'
    source=(root/(name+'.py')).read_text(encoding='utf-8-sig')
    hashes[name]=hashlib.sha256(source.encode()).hexdigest()
    code+=f"_m=types.ModuleType({name!r});sys.modules[{name!r}]=_m\nexec(compile({source!r},{name!r},'exec'),_m.__dict__)\n"
    code+="def reconstruct(upper, controls):\n if controls != {'variation': 0}: raise ValueError('Exact current material boundary only')\n result=sys.modules['musical_support_material'].expand_t3(upper)\n"
    code+=(" return result\n"if boundary=='tier3'else" return sys.modules['musical_cell_development'].reconstruct(result, controls)\n")
    return code,hashes
