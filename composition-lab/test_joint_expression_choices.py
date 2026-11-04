"""Authored primitive playback tables, never source/style or native-audio evidence."""
from copy import deepcopy
from itertools import product
import json
import unittest

from joint_expression_choices import solve,FEATURES
from output_change_targets import target_count


def fixture(weights=(1,1),baseline_ranks=None,current_ranks=None,baseline_accents=None,
            current_accents=None,candidate_ranks=(0,1,2,3),descendant_count=1):
    baseline_ranks=[0]*len(weights)if baseline_ranks is None else baseline_ranks
    current_ranks=baseline_ranks if current_ranks is None else current_ranks
    total=sum(weights)
    baseline_accents=[0]*total if baseline_accents is None else baseline_accents
    current_accents=baseline_accents if current_accents is None else current_accents
    regions={};attacks={};edges={};ordinal=0
    for i,weight in enumerate(weights):
        region='r'+str(i);members=[]
        for _ in range(weight):
            ref='a'+str(ordinal);members.append(ref)
            # Explicit authored values make cancellation visible; production
            # never contains this fixture's arithmetic or dynamic scale.
            performance=lambda rank,accent:[30+10*rank+10*accent+j for j in range(descendant_count)]
            attacks[ref]=dict(region_ref=region,descendant_ids=[ref+':written:'+str(j)for j in range(descendant_count)],
                baseline=dict(rank=baseline_ranks[i],accent=baseline_accents[ordinal],
                              performed=performance(baseline_ranks[i],baseline_accents[ordinal])),
                current=dict(rank=current_ranks[i],accent=current_accents[ordinal],
                             performed=performance(current_ranks[i],current_accents[ordinal])),
                performed_table=[dict(rank=rank,accent=accent,performed=performance(rank,accent))
                    for rank in set(candidate_ranks)|set(current_ranks)for accent in (0,1,2)])
            ordinal+=1
        regions[region]=[dict(id=f'{region}:{rank}:{mode}',marking='authored-rank-'+str(rank),rank=rank,
             accents={ref:(attacks[ref]['current']['accent']if mode=='current'else
                           1-attacks[ref]['baseline']['accent'])for ref in members})
             for rank in candidate_ranks for mode in ('current','flip')]
        unique=[];seen=set()
        for candidate in regions[region]:
            identity=(candidate['rank'],tuple(candidate['accents'].values()))
            if identity not in seen:unique.append(candidate);seen.add(identity)
        regions[region]=unique
        if i:
            edges['e'+str(i)]=dict(from_region='r'+str(i-1),to_region=region,
                baseline_difference=baseline_ranks[i]-baseline_ranks[i-1],
                current_difference=current_ranks[i]-current_ranks[i-1])
    return regions,attacks,edges


def request(percent=100,**changes):return dict(dict.fromkeys(FEATURES,percent),**changes)


def oracle(regions,attacks,edges,requests):
    """Independent exhaustive measurement: no solver helper or pruning reused."""
    for values in product(*(regions[ref]for ref in regions)):
        chosen=dict(zip(regions,values));valid=True
        metrics={name:[]for name in FEATURES}
        for ref,attack in attacks.items():
            choice=chosen[attack['region_ref']]
            table={(row['rank'],row['accent']):row['performed']for row in attack['performed_table']}
            final=dict(rank=choice['rank'],accent=choice['accents'][ref],
                       performed=table[choice['rank'],choice['accents'][ref]])
            for name,field in zip(FEATURES,('rank','accent','performed')):
                reference=attack['current'if requests[name]==0 else'baseline'][field]
                metrics[name].append(final[field]!=reference)
            if requests['performed']==100 and any(a==b for a,b in zip(final['performed'],attack['baseline']['performed'])):
                valid=False
        for edge in edges.values():
            delta=chosen[edge['to_region']]['rank']-chosen[edge['from_region']]['rank']
            reference=edge['current_difference'if requests[FEATURES[3]]==0 else'baseline_difference']
            metrics[FEATURES[3]].append(delta!=reference)
        if valid and all(sum(bits)==target_count(len(bits),requests[name])for name,bits in metrics.items()):
            return True
    return False


class JointExpressionChoiceTests(unittest.TestCase):
    def test_zero_locks_current_instead_of_restoring_original(self):
        regions,attacks,edges=fixture((2,1),current_ranks=[1,2],current_accents=[1,1,1])
        before=deepcopy((regions,attacks,edges))
        result=solve(regions,attacks,edges,request(0))
        self.assertEqual(result['status'],'FEASIBLE')
        self.assertEqual([result['assignment'][r]['rank']for r in regions],[1,2])
        self.assertTrue(all(m['comparison']=='current'and m['changed_count']==0 for m in result['measurements'].values()))
        self.assertEqual((regions,attacks,edges),before)

    def test_half_changes_half_of_original_attack_units_not_half_of_regions(self):
        data=fixture((1,3),candidate_ranks=(0,2))
        result=solve(*data,request(50))
        self.assertEqual(result['status'],'INFEASIBLE')
        self.assertEqual(result['target_counts']['base_dynamic'],2)
        self.assertEqual(result['region_attack_counts'],{'r0':1,'r1':3})
        result=solve(*fixture((2,2),candidate_ranks=(0,2)),request(50))
        self.assertEqual(result['status'],'FEASIBLE')
        self.assertEqual(result['measurements']['base_dynamic']['changed_count'],2)
        self.assertEqual(result['measurements']['accent']['changed_count'],2)
        self.assertEqual(result['measurements']['performed']['changed_count'],2)
        self.assertEqual(result['measurements']['adjacent_dynamic_difference']['changed_count'],1)

    def test_half_rounds_with_existing_target_semantics(self):
        result=solve(*fixture((1,2),candidate_ranks=(0,2)),request(50))
        self.assertEqual(result['status'],'FEASIBLE')
        self.assertEqual(result['target_counts']['base_dynamic'],2)
        self.assertEqual(result['measurements']['base_dynamic']['changed_ids'],['a1','a2'])

    def test_uniform_swap_does_not_change_six_original_zero_difference_edges(self):
        ranks=[0,0,1,1,0,0,1,1,0,0,0]
        regions,attacks,edges=fixture((1,)*11,baseline_ranks=ranks)
        self.assertEqual(sum(edge['baseline_difference']==0 for edge in edges.values()),6)
        swap={r:[c for c in rows if c['rank']==1-ranks[i]and c['id'].endswith(':flip')]
              for i,(r,rows)in enumerate(regions.items())}
        result=solve(swap,attacks,edges,request(100))
        self.assertEqual(result['status'],'INFEASIBLE')
        alternatives={r:[c for c in rows if c['rank']in(2,3)and c['id'].endswith(':flip')]
                      for r,rows in regions.items()}
        result=solve(alternatives,attacks,edges,request(100))
        self.assertEqual(result['status'],'FEASIBLE')
        self.assertEqual(result['measurements']['adjacent_dynamic_difference']['changed_count'],10)

    def test_base_plus_one_and_accent_flip_cancellation_is_measured_after_both(self):
        regions,attacks,edges=fixture((2,1),baseline_accents=[0,1,0])
        first={r:[c for c in rows if c['rank']==1 and c['id'].endswith(':flip')]
               for r,rows in regions.items()}
        result=solve(first,attacks,edges,request(100,adjacent_dynamic_difference=0))
        self.assertEqual(result['status'],'INFEASIBLE')
        self.assertTrue(any(r['reason']=='UNCHANGED_DESCENDANT_AT_100'for r in result['rejected_candidates']))
        alternatives={r:[c for c in rows if c['rank']==2 and c['id'].endswith(':flip')]
                      for r,rows in regions.items()}
        result=solve(alternatives,attacks,edges,request(100,adjacent_dynamic_difference=0))
        self.assertEqual(result['status'],'FEASIBLE')
        self.assertEqual(result['measurements']['performed']['changed_count'],3)

    def test_clamp_ghost_and_hopo_context_are_explicit_tables_not_guessed_deltas(self):
        regions,attacks,edges=fixture((1,1),candidate_ranks=(0,1))
        for attack in attacks.values():
            # This authored context clamps all changed choices to the original
            # performed value. Its rank/marking differences earn no audio credit.
            for row in attack['performed_table']:row['performed']=[42]
            attack['baseline']['performed']=[42];attack['current']['performed']=[42]
        result=solve(regions,attacks,edges,request(100))
        self.assertEqual(result['status'],'INFEASIBLE')
        self.assertEqual(result['total_counts']['performed'],2)

    def test_every_descendant_must_change_at_100_but_half_compares_whole_vectors(self):
        regions,attacks,edges=fixture((1,1),candidate_ranks=(0,2),descendant_count=2)
        for attack in attacks.values():
            for row in attack['performed_table']:
                if row['rank']==2:row['performed'][1]=attack['baseline']['performed'][1]
        self.assertEqual(solve(regions,attacks,edges,request(100))['status'],'INFEASIBLE')
        half=solve(regions,attacks,edges,request(50))
        self.assertEqual(half['status'],'FEASIBLE')
        self.assertEqual(half['measurements']['performed']['changed_count'],1)
        self.assertEqual(half['measurements']['performed']['all_descendants_changed_ids'],[])
        self.assertEqual(half['descendant_count'],4)
        self.assertEqual(half['total_counts']['performed'],2)

    def test_performed_zero_can_intentionally_require_compensating_parameter_changes(self):
        data=fixture((1,1),baseline_accents=[1,1],candidate_ranks=(0,1))
        result=solve(*data,request(100,performed=0,adjacent_dynamic_difference=0))
        self.assertEqual(result['status'],'FEASIBLE')
        self.assertEqual(result['measurements']['base_dynamic']['changed_count'],2)
        self.assertEqual(result['measurements']['accent']['changed_count'],2)
        self.assertEqual(result['measurements']['performed']['changed_count'],0)

    def test_unknown_measurements_never_reduce_population_or_manufacture_a_pass(self):
        regions,attacks,edges=fixture()
        attacks['a0']['baseline']['performed']=[None]
        result=solve(regions,attacks,edges,request(100))
        self.assertEqual(result['status'],'UNKNOWN_MEASUREMENTS')
        self.assertEqual(result['total_counts']['performed'],2)
        self.assertEqual(result['unknown_measurements']['performed'],['a0'])
        self.assertIsNone(result['assignment'])
        regions,attacks,edges=fixture(candidate_ranks=(0,2))
        for attack in attacks.values():
            for row in attack['performed_table']:
                if row['rank']==2:row['performed']=[None]
        result=solve(regions,attacks,edges,request(100))
        self.assertEqual(result['status'],'UNKNOWN_MEASUREMENTS')
        self.assertFalse(result['exhaustive_contradiction'])

    def test_explicit_performed_measure_only_diagnostic_retains_unknowns_and_never_claims_full_pass(self):
        regions,attacks,edges=fixture()
        attacks['a0']['baseline']['performed']=[None]
        attacks['a0']['current']['performed']=[None]
        for row in attacks['a0']['performed_table']:row['performed']=[None]
        before=deepcopy((regions,attacks,edges))
        strict=solve(regions,attacks,edges,request(100))
        self.assertEqual(strict['status'],'UNKNOWN_MEASUREMENTS');self.assertIsNone(strict['assignment'])
        self.assertEqual(solve(regions,attacks,edges,request(0))['status'],'UNKNOWN_MEASUREMENTS')
        result=solve(regions,attacks,edges,request(100,performed=None))
        self.assertEqual(result['status'],'FEASIBLE_UNVERIFIED_PERFORMANCE')
        self.assertFalse(result['combined_targets_verified'])
        self.assertIsNotNone(result['assignment'])
        self.assertTrue(all(result['measurements'][name]['satisfied']for name in FEATURES if name!='performed'))
        measured=result['measurements']['performed']
        self.assertEqual(measured['total_count'],2)
        self.assertEqual(measured['unknown_ids'],['a0'])
        self.assertIsNone(measured['satisfied']);self.assertIsNone(measured['target_count'])
        self.assertEqual(measured['status'],'MEASURE_ONLY_UNVERIFIED')
        self.assertEqual((regions,attacks,edges),before)

    def test_budget_exhaustion_and_exhaustive_contradiction_are_atomic_and_distinct(self):
        data=fixture();before=deepcopy(data)
        result=solve(*data,request(100),max_nodes=0)
        self.assertEqual(result['status'],'SEARCH_BUDGET_EXHAUSTED')
        self.assertFalse(result['decision_complete']);self.assertIsNone(result['assignment'])
        regions,attacks,edges=data;regions['r0']=[]
        result=solve(regions,attacks,edges,request(100),max_nodes=0)
        self.assertEqual(result['status'],'INFEASIBLE')
        self.assertTrue(result['exhaustive_contradiction']);self.assertIsNone(result['assignment'])
        self.assertEqual(attacks,before[1])

    def test_empty_positive_edge_scope_is_not_a_100_percent_pass(self):
        result=solve(*fixture((1,)),request(100))
        self.assertEqual(result['status'],'NOT_APPLICABLE')
        self.assertIsNone(result['assignment'])

    def test_saved_inputs_are_deterministic_and_unchanged(self):
        data=fixture((2,2));before=deepcopy(data)
        original=solve(*data,request(100))
        restored=solve(*json.loads(json.dumps(data)),request(100))
        self.assertEqual(original,restored);self.assertEqual(data,before)

    def test_forged_counts_missing_members_or_false_context_refuse(self):
        for problem in ('count','member','current','edge','duplicate_callback','missing_tuple'):
            with self.subTest(problem=problem):
                regions,attacks,edges=fixture()
                if problem=='count':regions['r0'][0]['changed_base_attack_count']=1
                elif problem=='member':regions['r0'][0]['accents']={}
                elif problem=='current':attacks['a0']['current']['performed']=[99]
                elif problem=='edge':edges['e1']['baseline_difference']=9
                elif problem=='duplicate_callback':attacks['a1']['descendant_ids']=attacks['a0']['descendant_ids']
                else:attacks['a0']['performed_table']=[]
                before=deepcopy((regions,attacks,edges))
                with self.assertRaises(ValueError):solve(regions,attacks,edges,request(100))
                self.assertEqual((regions,attacks,edges),before)

    def test_small_domains_match_an_independent_exhaustive_oracle_for_all_percent_combinations(self):
        for weights in ((1,1),(1,2),(2,2)):
            data=fixture(weights,candidate_ranks=(0,1,2))
            for values in product((0,50,100),repeat=4):
                controls=dict(zip(FEATURES,values))
                with self.subTest(weights=weights,controls=controls):
                    expected=oracle(*data,controls)
                    result=solve(*data,controls,max_nodes=10000)
                    self.assertEqual(result['status']=='FEASIBLE',expected)
                    self.assertIn(result['status'],('FEASIBLE','INFEASIBLE'))


if __name__=='__main__':unittest.main()
