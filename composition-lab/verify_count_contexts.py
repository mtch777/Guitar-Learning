"""Independent input-population and selected formula checks for count evidence."""
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json


def signature(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def verify_contexts(package,outputs,nodes,forward,checks):
    song=outputs["core"]["songs"][0];sid=song["song_id"]
    tracks={t["part_id"]:t for t in song["tracks"]}
    track_indices={t["part_id"]:i for i,t in enumerate(song["tracks"])}
    rows={r["occurrence"]:r for t in tracks.values() for r in t["rows"]}
    headers={h["bar"]:h for h in song["shared_layout"]}
    pedals={t["part_id"]:t for t in outputs["approved_pedals"]["tracks"]}
    pedal_indices={t["part_id"]:i for i,t in enumerate(outputs["approved_pedals"]["tracks"])}
    eligible={pid:[r for r in t["rows"] if not r["tie_destination"] and F(r["duration_q"])>0] for pid,t in tracks.items()}
    def event(occurrence):return f"event:{sid}:{occurrence}"
    def targets(ident,relation):return {e["to_id"] for e in forward[ident] if e["type"]==relation}
    def groups(population):
        grouped=defaultdict(list)
        for row in population:grouped[F(row["onset_q"])].append(row)
        return sorted(grouped.items())
    def pattern(population,kind):
        grouped=groups(population)
        base=min(F(r["onset_q"])-F(r.get("bar_offset_q","0")) for r in population)
        bar=population[0]["bar"];header=headers[bar]
        if kind=="rhythm":
            span=dict(span_q=header.get("span_q",population[0].get("bar_span_q")),signature=header.get("signature"))
            return signature((span,[(str(q-base),sorted((r["voice"],str(F(r["duration_q"]))) for r in members)) for q,members in grouped]))
        if any(r["midi"] is None for r in population):return None
        anchor=min(r["midi"] for r in grouped[0][1])
        return signature([[p-anchor for p in sorted(r["midi"] for r in members)] for _,members in grouped])
    histories={}
    for pid,population in eligible.items():
        bars=defaultdict(list)
        for row in population:bars[row["bar"]].append(row)
        histories[pid]={bar:{kind:pattern(rs,kind) for kind in ("rhythm","relative_pitch")} for bar,rs in bars.items()}
    for node in nodes.values():
        if node["kind"] not in {"conditional_calculation_input","conditional_absence_check"}:continue
        d=node["values"];scope=d["source_scope"];pid=d.get("part_id");ident=node["id"]
        parts=[pid] if pid is not None else d.get("parts",[])
        for part in parts:
            ti=next(i for i,t in enumerate(song["tracks"]) if t["part_id"]==part)
            assert targets(ident,"track_eligibility_input")=={f"r:core:/songs/0/tracks/{i}/{field}" for i,t in enumerate(song["tracks"]) if t["part_id"] in parts for field in ("guitar_or_bass","temporal_relationships_eligible")},"Track eligibility evidence differs"
        if scope in {"core_track_rows","eligible_attack_groups","prior_eligible_bar_patterns"}:
            population=[r for r in tracks[pid]["rows"] if r["midi"] is not None] if scope=="core_track_rows" else eligible[pid]
            relation="calculation_search_population"
            if scope=="prior_eligible_bar_patterns":
                population=[r for r in population if r["bar"]<d["before_bar"]];relation="prior_pattern_search_population"
            assert targets(ident,relation)=={event(r["occurrence"]) for r in population},"Calculation search population differs"
            assert node["query"]["population_size"]==len(population),"Calculation population size differs"
            if d.get("predicate")=="no_eligible_attack_at":assert not any(F(r["onset_q"])==F(d["onset_q"]) for r in population),"False attack absence"
            if d.get("predicate")=="no_next_attack_in_same_section":
                origins=[rows[m] for m in d["after_members"]];origin=origins[0];sections={r["section_start"] for r in origins}
                later=groups([r for r in population if F(r["onset_q"])>F(origin["onset_q"])])
                assert not later or len(sections)!=1 or None in sections or {r["section_start"] for r in later[0][1]}!=sections,"False next-in-section absence"
            if scope=="prior_eligible_bar_patterns":
                matches=[bar for bar,kinds in histories[pid].items() if bar<d["before_bar"] and kinds[d["pattern_kind"]]==d["signature"]]
                actual=[r["occurrence"] for _,members in groups([r for r in eligible[pid] if matches and r["bar"]==max(matches)]) for r in members]
                if d.get("predicate")=="no_previous_pattern_match":assert not matches,"False prior-pattern absence"
                else:assert d["matched_members"]==actual,"Previous pattern occurrence differs"
            checks["verified_calculation_populations"]+=1
        if scope=="accepted_pedal_tracks":assert pid not in pedals,"False pedal coverage absence"
        if scope=="accepted_pedal_track":
            expected={f"r:approved_pedals:/tracks/{pedal_indices[pid]}"} if pid in pedals else set()
            assert targets(ident,"accepted_role_coverage_input")==expected,"Accepted coverage input differs"
            expected_phrases={f"r:approved_pedals:/tracks/{pedal_indices[pid]}/phrases/{i}" for i in d.get("phrase_indices",[])}
            assert targets(ident,"accepted_role_phrase_input")==expected_phrases,"Accepted phrase input link differs"
            if d.get("predicate")=="no_accepted_role_for_members":assert all(not(set(d["members"])&set(p["roles"])) for p in pedals[pid]["phrases"]),"False accepted-role absence"
            elif d.get("coverage")=="not_supplied":assert pid not in pedals,"False missing pedal coverage"
            elif "phrase_indices" in d:
                indices=[i for i,p in enumerate(pedals[pid]["phrases"]) if set(d["members"])&set(p["roles"])]
                assert d["phrase_indices"]==indices,"Accepted role phrase input differs"
        if scope=="core_track_events":assert targets(ident,"calculation_input_member")=={event(m) for m in d["members"]},"Exact calculation members differ"
        if scope in {"core_technique_values","core_hopo_candidates","core_coattack_groups"}:
            field={"core_technique_values":"technique_values","core_hopo_candidates":"hopo_transition_candidates","core_coattack_groups":"coattack_groups"}[scope]
            values=tracks[pid][field];ti=track_indices[pid]
            if scope=="core_technique_values":indices=[d["detail_index"]]
            elif scope=="core_hopo_candidates":indices=[d["pair_index"]] if "pair_index" in d else [i for i,p in enumerate(values) if p["origin"] in d["origin_members"]]
            else:indices=[i for i,g in enumerate(values) if F(g["onset_q"]) in {F(q) for q in d["onsets_q"]}]
            assert all(0<=i<len(values) for i in indices),"Invalid classifier/detail locator"
            assert targets(ident,"existing_classifier_or_mechanic_input")=={f"r:core:/songs/0/tracks/{ti}/{field}/{i}" for i in indices},"Exact classifier/mechanical input link differs"
            assert targets(ident,"classifier_lookup_scope")=={f"r:core:/songs/0/tracks/{ti}/{field}"},"Classifier search scope differs"
        if scope=="accepted_pedal_cycle":
            pi,ci=d["phrase_index"],d["cycle_index"]
            assert 0<=ci<len(pedals[pid]["phrases"][pi]["cycles"]),"Invalid accepted cycle locator"
            assert targets(ident,"accepted_cycle_input")=={f"r:approved_pedals:/tracks/{pedal_indices[pid]}/phrases/{pi}/cycles/{ci}"},"Accepted cycle link differs"
        if scope in {"supplied_track_programs","captured_track_programs"}:
            expected={(f"source:track-{p}.json","/instrumentId") for p in d["parts"] if "instrumentId" in next(doc["payload"] for doc in _documents(package) if doc["id"]==f"source:track-{p}.json")}
            actual={(e["to_source"]["document"],e["to_source"]["pointer"]) for e in forward[ident] if e["type"]=="source_program_input"}
            assert actual==expected,"Program source input pointers differ"
        checks["verified_calculation_descriptors"]+=1
    # Selected formulas are checked from source rows and exact descriptor inputs,
    # not by asking the original profile builder to validate its own output.
    for unit in outputs["profile_support"]:
        descriptors=unit["calculation_inputs"];byrole={d["role"]:d for d in descriptors}
        if unit["kind"]=="mechanical_shape_given_context":
            origin=[rows[m] for m in byrole["origin_group"]["members"]]
            pid=byrole["origin_group"]["part_id"];q=F(origin[0]["onset_q"])
            assert {r["occurrence"] for r in origin}=={r["occurrence"] for r in eligible[pid] if F(r["onset_q"])==q},"Mechanical origin group incomplete"
            later=groups([r for r in eligible[pid] if F(r["onset_q"])>q])
            sections={r["section_start"] for r in origin}
            next_rows=later[0][1] if later and len(sections)==1 and None not in sections and {r["section_start"] for r in later[0][1]}==sections else []
            assert set(byrole.get("next_group",{}).get("members",[]))=={r["occurrence"] for r in next_rows},"Mechanical next group is wrong occurrence"
            member_rows=[rows[m] for m in unit["support"]["members"]]
            detail=tracks[pid]["technique_values"][byrole["curve_parameters"]["detail_index"]]
            mechanism=unit["condition"]["mechanism"]
            assert byrole["curve_parameters"]["mechanism"]==mechanism and detail.get(mechanism,{}).get("valid"),"Mechanical curve locator differs"
            curve_row=rows[detail["occurrence"]]
            expected_unit={detail["occurrence"]} if mechanism=="bend" else {r["occurrence"] for r in origin if (r["bar"],r["voice"],r["beat"])==(curve_row["bar"],curve_row["voice"],curve_row["beat"])}
            assert {r["occurrence"] for r in member_rows}==expected_unit,"Mechanical counted unit does not match curve occurrence"
            pitch=min(r["midi"] for r in member_rows) if all(r["midi"] is not None for r in member_rows) else None
            interval=min(r["midi"] for r in next_rows)-pitch if next_rows and all(r["midi"] is not None for r in next_rows) and pitch is not None else None
            assert unit["outcome"]["next_attack_written_minimum_interval"]==interval,"Mechanical interval formula differs"
            checks["verified_mechanical_input_formulas"]+=1
        if unit["kind"]=="adjacent_bar_variation":
            pid=unit["support"]["part_id"];bars=unit["support"]["bars"]
            assert set(unit["support"]["members"])=={r["occurrence"] for r in eligible[pid] if r["bar"] in bars},"Adjacent-bar unit includes non-attack or omits member"
            checks["verified_adjacent_bar_memberships"]+=1


def _documents(package):
    state=package["representation"]
    while state["tier"]:state=state["lower_tier"]
    return state["documents"]
