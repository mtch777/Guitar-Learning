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
          step_constraints=(), fixed=None, max_nodes=100000):
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
