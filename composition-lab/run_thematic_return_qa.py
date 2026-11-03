"""Actual T5 and existing inverse code, using the audited isolated worker."""
import hashlib
from run_support_arrangement_qa import bundle as arrangement_bundle


def bundle(root,*,boundary='source'):
    if boundary not in('source','tier4','tier3'):raise ValueError('Declared source/T4/T3 boundary required')
    code,hashes=arrangement_bundle(root)
    for name in('section_arrangements','thematic_return'):
        source=(root/(name+'.py')).read_text(encoding='utf-8-sig');hashes[name]=hashlib.sha256(source.encode()).hexdigest()
        code+=f"_m=types.ModuleType({name!r});sys.modules[{name!r}]=_m\nexec(compile({source!r},{name!r},'exec'),_m.__dict__)\n"
    code+="def reconstruct(upper, controls):\n if controls != {'variation': 0}: raise ValueError('Exact current boundary required')\n"
    if boundary=='source':code+=" return sys.modules['thematic_return'].reconstruct(upper, controls)\n"
    elif boundary=='tier4':code+=" return sys.modules['thematic_return'].expand(upper)\n"
    else:code+=" return sys.modules['section_arrangements'].expand(upper)\n"
    return code,hashes
