"""Finite joint pitch/contact feasibility, without choosing musical intention.

The caller supplies already justified, physically admissible candidates for each
stable sustain-chain variable. Candidate order expresses the caller's declared
rank/intention; the first feasible result is not a musical preference claim or a
global rank optimum. Contact equality with the source is NOT restricted here.

All occurrences of a sustain chain must name the same variable. The caller owns
complete overlap coverage, degree realization, evidence and final-output QA.
"""
from collections import defaultdict
from copy import deepcopy


def _candidate(value):
    if (type(value) is not dict or set(value) != {'pitch', 'string', 'fret'}
            or value['pitch'] is not None and type(value['pitch']) is not int
            or type(value['string']) is not int or value['string'] < 0
            or value['fret'] is not None and (type(value['fret']) is not int or value['fret'] < 0)):
        raise ValueError('Closed exact pitch/string/fret candidate required; unknown pitch/fret may be null')
    return value['pitch'], value['string'], value['fret']


def _input(options, simultaneous_groups, same_string_groups, fret_directions, step_constraints, fixed, max_nodes):
    if (type(options) is not dict or any(type(ref) is not str or not ref for ref in options)
            or type(max_nodes) is not int or max_nodes < 0):
        raise ValueError('Stable variable mapping and nonnegative exact search budget required')
    choices = {}
    for ref, rows in options.items():
        if type(rows) is not list:
            raise ValueError('Explicit finite caller-ordered candidate list required')
        choices[ref] = tuple(_candidate(row) for row in rows)
        if len(set(choices[ref])) != len(choices[ref]):
            raise ValueError('Duplicate candidate choices are not separate alternatives')
    fixed = {} if fixed is None else fixed
    if type(fixed) is not dict or set(fixed) - set(choices):
        raise ValueError('Protected fixed choices must name existing variables')
    domains = {ref: tuple(range(len(values))) for ref, values in choices.items()}
    for ref, value in fixed.items():
        key = _candidate(value)
        if key not in choices[ref]:
            raise ValueError('Protected choice must be present in the supplied candidate domain')
        domains[ref] = (choices[ref].index(key),)
    if any(type(rows) not in (list, tuple) for rows in (simultaneous_groups, same_string_groups, fret_directions, step_constraints)):
        raise ValueError('Explicit simultaneous/same-string groups and step constraints required')
    pairs = defaultdict(list)
    neighbors = {ref: set() for ref in choices}

    def pair(left, right, clause):
        key = tuple(sorted((left, right)))
        if clause not in pairs[key]:
            pairs[key].append(clause)
        neighbors[left].add(right); neighbors[right].add(left)

    for kind, groups in (('distinct_string', simultaneous_groups), ('same_string', same_string_groups)):
        for group in groups:
            if (type(group) not in (list, tuple) or not group
                    or any(type(ref) is not str or ref not in choices for ref in group)
                    or len(set(group)) != len(group)):
                raise ValueError('Contact groups require distinct existing sustain-chain variables')
            for i, left in enumerate(group):
                for right in group[i+1:]:
                    pair(left, right, (kind,))
    for row in fret_directions:
        if (type(row) is not dict or set(row) != {'from_ref', 'to_ref', 'direction'}
                or type(row['from_ref']) is not str or type(row['to_ref']) is not str
                or row['from_ref'] not in choices or row['to_ref'] not in choices
                or row['direction'] not in ('ascending', 'descending')):
            raise ValueError('Closed existing-variable retained fret direction required')
        left, right = row['from_ref'], row['to_ref']
        if any(c[2] is None for ref in (left, right) for c in choices[ref]):
            raise ValueError('Retained fret direction requires known physical fret candidates')
        if left == right:
            domains[left] = ()
        else:
            pair(left, right, ('fret_direction', left, right, row['direction']))
    for row in step_constraints:
        if (type(row) is not dict
                or set(row) not in ({'from_ref', 'to_ref', 'baseline_step', 'change'},
                                    {'from_ref', 'to_ref', 'baseline_step', 'change', 'intention'})
                or type(row['from_ref']) is not str or type(row['to_ref']) is not str
                or row['from_ref'] not in choices or row['to_ref'] not in choices
                or type(row['baseline_step']) is not int or type(row['change']) is not bool
                or row.get('intention') not in (None, 'opposite_direction')):
            raise ValueError('Closed existing-variable signed-step constraint required')
        if row.get('intention') == 'opposite_direction' and row['baseline_step'] == 0:
            raise ValueError('A repeated pitch has no opposite direction; caller must declare its intention')
        left, right = row['from_ref'], row['to_ref']
        if any(c[0] is None for ref in (left, right) for c in choices[ref]):
            raise ValueError('Signed-step constraints require known pitched candidates')
        clause = ('step', left, right, row['baseline_step'], row['change'], row.get('intention'))
        if left == right:
            keep = (0 != row['baseline_step']) == row['change']
            if row.get('intention') == 'opposite_direction': keep = False
            if not keep: domains[left] = ()
        else:
            pair(left, right, clause)
    return choices, domains, dict(pairs), neighbors


def _compatible(left, left_value, right, right_value, clauses):
    for clause in clauses:
        if clause[0] == 'distinct_string':
            if left_value[1] == right_value[1]: return False
        elif clause[0] == 'same_string':
            if left_value[1] != right_value[1]: return False
        elif clause[0] == 'fret_direction':
            _, source, destination, direction = clause
            difference = right_value[2] - left_value[2] if source == left else left_value[2] - right_value[2]
            if direction == 'ascending' and difference <= 0: return False
            if direction == 'descending' and difference >= 0: return False
        else:
            _, source, destination, baseline, change, intention = clause
            step = right_value[0] - left_value[0] if source == left else left_value[0] - right_value[0]
            if (step != baseline) != change: return False
            if intention == 'opposite_direction' and step * baseline >= 0: return False
    return True


def _components(neighbors, order):
    pending = set(neighbors)
    result = []
    for start in order:
        if start not in pending: continue
        component = []; queue = [start]; pending.remove(start)
        while queue:
            ref = queue.pop(); component.append(ref)
            for other in sorted(neighbors[ref], key=order.__getitem__, reverse=True):
                if other in pending:
                    pending.remove(other); queue.append(other)
        result.append(sorted(component, key=order.__getitem__))
    return result


def _search(component, choices, domains, pairs, neighbors, order, budget):
    """Iterative forward checking; trail restores only changed domains."""
    if any(not domains[ref] for ref in component):
        return 'INFEASIBLE', None, 0
    assigned = {}; trail = []; frames = []; examined = 0

    def next_ref():
        return min((ref for ref in component if ref not in assigned),
                   key=lambda ref: (len(domains[ref]), order[ref]))

    first = next_ref()
    frames.append([first, domains[first], 0, 0])
    while frames:
        ref, candidates, position, mark = frames[-1]
        while len(trail) > mark:
            other, old = trail.pop(); domains[other] = old
        assigned.pop(ref, None)
        if position == len(candidates):
            frames.pop(); continue
        if examined >= budget:
            return 'SEARCH_BUDGET_EXHAUSTED', None, examined
        selected = candidates[position]; frames[-1][2] += 1
        examined += 1; assigned[ref] = selected
        valid = True
        for other in sorted(neighbors[ref], key=order.__getitem__):
            clauses = pairs[tuple(sorted((ref, other)))]
            if other in assigned:
                if not _compatible(ref, choices[ref][selected], other, choices[other][assigned[other]], clauses):
                    valid = False; break
            else:
                old = domains[other]
                filtered = tuple(index for index in old if _compatible(
                    ref, choices[ref][selected], other, choices[other][index], clauses))
                if filtered != old:
                    trail.append((other, old)); domains[other] = filtered
                if not filtered:
                    valid = False; break
        if not valid: continue
        if len(assigned) == len(component):
            return 'FEASIBLE', assigned, examined
        other = next_ref()
        frames.append([other, domains[other], 0, len(trail)])
    return 'INFEASIBLE', None, examined


def solve(options, *, simultaneous_groups=(), same_string_groups=(), fret_directions=(),
          step_constraints=(), fixed=None, max_nodes=100000, output_targets=None,
          max_seconds=60):
    """Return FEASIBLE, INFEASIBLE, or SEARCH_BUDGET_EXHAUSTED atomically.

    ``options`` maps stable chain IDs to ordered {pitch, string, fret} lists.
    ``fixed`` restricts protected variables to one already-present candidate.
    Each simultaneous group requires distinct strings. Retained gesture groups
    require the same string without merging their independent pitch variables.
    Retained fret directions {from_ref, to_ref, direction} require a strictly
    ascending/descending fret difference. The caller separately supplies their
    same-string groups, open/fretted context and successor/occupancy obligations.
    Each step constraint
    {from_ref, to_ref, baseline_step, change} compares final signed semitones to
    its declared baseline. Optional intention='opposite_direction' additionally
    requires the opposite sign; a zero baseline cannot imply that intention.

    max_nodes counts attempted candidate assignments, not seconds. A finite
    exhaustive contradiction is distinct from an incomplete budget-limited
    search. No partial assignment is returned on either kind of failure.
    """
    choices, domains, pairs, neighbors = _input(
        options, simultaneous_groups, same_string_groups, fret_directions, step_constraints, fixed, max_nodes)
    if output_targets is not None:
        return _solve_output_targets(options, choices, domains, pairs, output_targets,
                                     max_nodes=max_nodes, max_seconds=max_seconds)
    order = {ref: i for i, ref in enumerate(choices)}
    components = _components(neighbors, order)
    assignment = {}; counts = []; examined = 0; status = 'FEASIBLE'
    for index, component in enumerate(components):
        status, current, count = _search(component, choices, domains, pairs, neighbors, order, max_nodes-examined)
        examined += count
        counts.append(dict(first_variable=component[0], variable_count=len(component),
            pair_count=sum(len(neighbors[ref]) for ref in component)//2,
            status=status, examined_choices=count))
        if status != 'FEASIBLE':
            break
        assignment.update(current)
    return dict(status=status,
        assignment={ref:deepcopy(options[ref][assignment[ref]]) for ref in options} if status == 'FEASIBLE' else None,
        examined_choices=examined, max_nodes=max_nodes, components=counts,
        pending_components=len(components)-len(counts),
        decision_complete=status != 'SEARCH_BUDGET_EXHAUSTED',
        exhaustive_contradiction=status == 'INFEASIBLE',
        selection='First feasible caller-ordered choices with fewest-remaining-options search; not musical preference or rank optimum')


def _solve_output_targets(options, choices, domains, pairs, targets, *, max_nodes, max_seconds):
    """Coordinate final-output counts across components without defining music.

    Each target has ``kind``, ``percent`` and ``units``. Unary kinds are
    pitch_class, octave and contact; units map existing variables to original
    values (contact is [string, fret]). Step units map stable metric IDs to
    {from_ref, to_ref, baseline_step}. Separate named step targets can measure
    melodic movement and chord spacing without conflating their denominators.

    Candidate admission and ordering remain the caller's responsibility. This
    optional finite constraint backend never creates a pitch or musical rule.
    It returns no partial assignment on missing dependency, budget or failure.
    """
    from output_change_targets import target_count
    if (type(targets) is not dict or not targets or type(max_seconds) not in (int, float)
            or isinstance(max_seconds, bool) or max_seconds <= 0):
        raise ValueError('Explicit final-output targets and positive time budget required')
    prepared = {}
    for name, target in targets.items():
        if (type(name) is not str or not name or type(target) is not dict
                or set(target) != {'kind', 'percent', 'units'}
                or target['kind'] not in ('pitch_class', 'octave', 'contact', 'step')
                or type(target['units']) is not dict or not target['units']):
            raise ValueError('Closed named final-output feature and nonempty frozen units required')
        count = target_count(len(target['units']), target['percent'])
        for ref, baseline in target['units'].items():
            if type(ref) is not str or not ref:
                raise ValueError('Stable output unit identity required')
            if target['kind'] == 'step':
                if (type(baseline) is not dict or set(baseline) != {'from_ref', 'to_ref', 'baseline_step'}
                        or type(baseline['baseline_step']) is not int
                        or any(baseline[k] not in choices for k in ('from_ref', 'to_ref'))
                        or any(c[0] is None for k in ('from_ref', 'to_ref') for c in choices[baseline[k]])):
                    raise ValueError('Known original signed step between existing pitched variables required')
            elif ref not in choices:
                raise ValueError('Output quota references an absent variable')
            elif target['kind'] == 'contact':
                if (type(baseline) not in (list, tuple) or len(baseline) != 2
                        or type(baseline[0]) is not int
                        or baseline[1] is not None and type(baseline[1]) is not int):
                    raise ValueError('Original physical contact required')
            elif (type(baseline) is not int or any(c[0] is None for c in choices[ref])
                    or target['kind'] == 'pitch_class' and not 0 <= baseline < 12):
                raise ValueError('Known original pitch-class/octave required')
        prepared[name] = dict(target, target_count=count)
    common = dict(assignment=None, max_nodes=max_nodes, output_features={},
                  selection='Finite caller-admitted choices coordinated by final-output quotas; no musical preference claim')
    if any(not domain for domain in domains.values()):
        return dict(common, status='INFEASIBLE', exhaustive_contradiction=True, decision_complete=True)
    try:
        import numpy as np
        from scipy.optimize import milp, Bounds, LinearConstraint
        from scipy.sparse import coo_matrix
    except ImportError as error:
        return dict(common, status='DEPENDENCY_UNAVAILABLE', exhaustive_contradiction=False,
                    decision_complete=False, error=str(error))
    costs = []; lower = []; upper = []; rows = []; lo = []; hi = []
    def variable(cost=0, low=0, high=1):
        index=len(costs); costs.append(cost); lower.append(low); upper.append(high); return index
    def constraint(values, low=-np.inf, high=np.inf):
        rows.append({i:v for i,v in values.items() if v}); lo.append(low); hi.append(high)
    def plus(*items):
        result=defaultdict(float)
        for values, scale in items:
            for i,value in values.items(): result[i] += scale*value
        return dict(result)
    selected={}; values={}
    for ref, domain in domains.items():
        selected[ref]={index:variable(index/max(1,len(choices[ref]))) for index in domain}
        constraint({index:1 for index in selected[ref].values()},1,1)
        values[ref]=[{selected[ref][index]:choices[ref][index][column] for index in domain
                      if choices[ref][index][column] is not None} for column in range(3)]
    step_flags={}
    def changed_step(left,right,baseline):
        key=(left,right,baseline)
        if key in step_flags:return step_flags[key]
        # q+ / q- distinguish positive / negative deviations; both zero means
        # exact equality. Their sum is the observable changed-step indicator.
        pos=variable(); neg=variable(); flags={pos:1,neg:1}
        constraint(flags,high=1)
        delta=plus((values[right][0],1),(values[left][0],-1))
        left_p=[choices[left][i][0] for i in domains[left]]
        right_p=[choices[right][i][0] for i in domains[right]]
        bound=max(abs(min(right_p)-max(left_p)-baseline),
                  abs(max(right_p)-min(left_p)-baseline),1)
        constraint(plus((delta,1),({pos:-1,neg:bound},1)),low=baseline)
        constraint(plus((delta,1),({pos:-bound,neg:1},1)),high=baseline)
        step_flags[key]=flags;return flags
    for (left,right), clauses in pairs.items():
        for clause in clauses:
            if clause[0] in ('same_string','distinct_string'):
                delta=plus((values[right][1],1),(values[left][1],-1))
                if clause[0]=='same_string':constraint(delta,0,0)
                else:
                    order=variable()
                    bound=max(c[1] for c in choices[left]+choices[right])+1
                    constraint(plus((delta,1),({order:-bound},1)),1-bound,-1)
            elif clause[0]=='fret_direction':
                _, source,destination,direction=clause
                delta=plus((values[destination][2],1),(values[source][2],-1))
                constraint(delta,low=1) if direction=='ascending' else constraint(delta,high=-1)
            else:
                _, source,destination,baseline,change,intention=clause
                flags=changed_step(source,destination,baseline)
                constraint(flags,int(change),int(change))
                if intention=='opposite_direction':
                    delta=plus((values[destination][0],1),(values[source][0],-1))
                    constraint(delta,high=-1) if baseline>0 else constraint(delta,low=1)
    for name,target in prepared.items():
        count_terms={}
        for ref,baseline in target['units'].items():
            if target['kind']=='step':
                terms=changed_step(baseline['from_ref'],baseline['to_ref'],baseline['baseline_step'])
            else:
                terms={}
                for index,var in selected[ref].items():
                    c=choices[ref][index]
                    value=(c[0]%12 if target['kind']=='pitch_class' else
                           c[0]//12-1 if target['kind']=='octave' else list(c[1:]))
                    if value != (list(baseline) if target['kind']=='contact' else baseline):terms[var]=1
            count_terms=plus((count_terms,1),(terms,1))
        constraint(count_terms,target['target_count'],target['target_count'])
    rr=[];cc=[];dd=[]
    for r,row in enumerate(rows):
        for c,value in row.items():rr.append(r);cc.append(c);dd.append(value)
    matrix=coo_matrix((dd,(rr,cc)),shape=(len(rows),len(costs))).tocsc()
    result=milp(np.array(costs),integrality=np.ones(len(costs)),bounds=Bounds(lower,upper),
                constraints=LinearConstraint(matrix,lo,hi),
                options={'node_limit':max_nodes,'time_limit':float(max_seconds),'mip_rel_gap':1.0})
    common.update(examined_choices=int(getattr(result,'mip_node_count',0) or 0),
                  solver_status=int(result.status),solver_message=str(result.message))
    if result.x is None:
        status=('INFEASIBLE' if result.status==2 else
                'SEARCH_BUDGET_EXHAUSTED' if result.status==1 else 'SOLVER_FAILURE')
        return dict(common,status=status,exhaustive_contradiction=status=='INFEASIBLE',
                    decision_complete=status=='INFEASIBLE')
    assignment={}
    for ref, indices in selected.items():
        chosen=[i for i,var in indices.items() if result.x[var]>.5]
        if len(chosen)!=1:raise ValueError('Quota backend returned a nonintegral choice')
        assignment[ref]=deepcopy(options[ref][chosen[0]])
    # Independently reuse the original exact predicates and count realized
    # values. Solver tolerances cannot silently weaken the musical contract.
    for (left,right),clauses in pairs.items():
        if not _compatible(left,_candidate(assignment[left]),right,_candidate(assignment[right]),clauses):
            raise ValueError('Quota assignment violates an original relationship constraint')
    actual={}
    for name,target in prepared.items():
        changed=[]
        for ref,baseline in target['units'].items():
            if target['kind']=='step':
                value=assignment[baseline['to_ref']]['pitch']-assignment[baseline['from_ref']]['pitch']
                original=baseline['baseline_step']
            else:
                c=assignment[ref]
                value=(c['pitch']%12 if target['kind']=='pitch_class' else
                       c['pitch']//12-1 if target['kind']=='octave' else [c['string'],c['fret']])
                original=list(baseline) if target['kind']=='contact' else baseline
            if value!=original:changed.append(ref)
        if len(changed)!=target['target_count']:raise ValueError('Final quota assignment failed exact output count')
        actual[name]=dict(changed_count=len(changed),total_count=len(target['units']),
                          target_count=target['target_count'],changed_ids=changed)
    return dict(common,status='FEASIBLE',assignment=assignment,output_features=actual,
                exhaustive_contradiction=False,decision_complete=True)
