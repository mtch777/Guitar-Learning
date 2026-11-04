"""Existing audited worker, actual T4/T3 relations, no alternate inverse."""
import hashlib
from run_musical_support_qa import bundle as material_bundle


def bundle(root,*,boundary='source'):
    if boundary not in ('source','tier3','tier2'):raise ValueError('Declared source/T3/T2 boundary required')
    code,hashes=material_bundle(root)
    for name in ('material_rhythm_displacement','material_slot_clock','material_entry_rest','material_entry_carry','derived_sustain_projection','entry_contact_continuity','material_use_entry_clock','bend_choice_constraints','material_bend_excursions','current_use_allocation','support_material_uses','support_arrangement'):
        source=(root/(name+'.py')).read_text(encoding='utf-8-sig');hashes[name]=hashlib.sha256(source.encode()).hexdigest()
        code+=f"_m=types.ModuleType({name!r});sys.modules[{name!r}]=_m\nexec(compile({source!r},{name!r},'exec'),_m.__dict__)\n"
    code+="def reconstruct(upper, controls):\n if controls != {'variation': 0}: raise ValueError('Exact current boundary required')\n"
    if boundary=='source':code+=" return sys.modules['support_arrangement'].reconstruct(upper, controls)\n"
    elif boundary=='tier3':code+=" return sys.modules['support_arrangement'].expand(upper)\n"
    else:code+=" return sys.modules['support_material_uses'].expand(upper)\n"
    return code,hashes
