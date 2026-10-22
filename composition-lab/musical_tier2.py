"""Reversible Tier2 coattack sonorities and conditional harmonic relationships.

Written-base pitch, not performed/sounding harmony. Theory-compatible alternatives
are not selected key/chord truth. No song-specific rules or external reads.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json

# THEORY_FORMS inserted reproducibly from music21.harmony.CHORD_TYPES by
# build_tier2_theory.py; these are theory definitions, not artist preferences.
THEORY_FORMS = (('major', (0, 4, 7)), ('minor', (0, 3, 7)), ('augmented', (0, 4, 8)), ('diminished', (0, 3, 6)), ('dominant-seventh', (0, 4, 7, 10)), ('major-seventh', (0, 4, 7, 11)), ('minor-major-seventh', (0, 3, 7, 11)), ('minor-seventh', (0, 3, 7, 10)), ('augmented-major-seventh', (0, 4, 8, 11)), ('augmented-seventh', (0, 4, 8, 10)), ('half-diminished-seventh', (0, 3, 6, 10)), ('diminished-seventh', (0, 3, 6, 9)), ('seventh-flat-five', (0, 4, 6, 10)), ('major-sixth', (0, 4, 7, 9)), ('minor-sixth', (0, 3, 7, 9)), ('major-ninth', (0, 2, 4, 7, 11)), ('dominant-ninth', (0, 2, 4, 7, 10)), ('minor-major-ninth', (0, 2, 3, 7, 11)), ('minor-ninth', (0, 2, 3, 7, 10)), ('augmented-major-ninth', (0, 2, 4, 8, 11)), ('augmented-dominant-ninth', (0, 2, 4, 8, 10)), ('half-diminished-ninth', (0, 2, 3, 6, 10)), ('half-diminished-minor-ninth', (0, 1, 3, 6, 10)), ('diminished-ninth', (0, 2, 3, 6, 9)), ('diminished-minor-ninth', (0, 1, 3, 6, 9)), ('dominant-11th', (0, 2, 4, 5, 7, 10)), ('major-11th', (0, 2, 4, 5, 7, 11)), ('minor-major-11th', (0, 2, 3, 5, 7, 11)), ('minor-11th', (0, 2, 3, 5, 7, 10)), ('augmented-major-11th', (0, 2, 4, 5, 8, 11)), ('augmented-11th', (0, 2, 4, 5, 8, 10)), ('half-diminished-11th', (0, 2, 3, 5, 6, 10)), ('diminished-11th', (0, 2, 3, 5, 6, 9)), ('major-13th', (0, 2, 4, 5, 7, 9, 11)), ('dominant-13th', (0, 2, 4, 5, 7, 9, 10)), ('minor-major-13th', (0, 2, 3, 5, 7, 9, 11)), ('minor-13th', (0, 2, 3, 5, 7, 9, 10)), ('augmented-major-13th', (0, 2, 4, 5, 8, 9, 11)), ('augmented-dominant-13th', (0, 2, 4, 5, 8, 9, 10)), ('half-diminished-13th', (0, 2, 3, 5, 6, 9, 10)), ('suspended-second', (0, 2, 7)), ('suspended-fourth', (0, 5, 7)), ('suspended-fourth-seventh', (0, 5, 7, 10)), ('Neapolitan', (0, 1, 4, 6)), ('Italian', (0, 6, 8)), ('French', (0, 2, 6, 8)), ('German', (0, 3, 6, 8)), ('pedal', (0,)), ('power', (0, 7)), ('Tristan', (0, 3, 6, 10)))
THEORY_PROVENANCE = {'source': 'music21.harmony.CHORD_TYPES', 'version': '9.9.2', 'forms_sha256': '9b4d190d20c19436449fe53e7a494a414ec48db8b18a79507aacb97ae70e7b5a', 'vocabulary_scope': 'Published Western chord-kind definitions; not exhaustive musical harmony', 'candidate_rule': 'Exact observed pitch-class set; all twelve roots; singleton excluded'}

TONAL_PROFILES = (('KrumhanslSchmuckler', (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88), (6.33, 2.68, 3.52, 5.38, 2.6, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)), ('TemperleyKostkaPayne', (0.748, 0.06, 0.488, 0.082, 0.67, 0.46, 0.096, 0.715, 0.104, 0.366, 0.057, 0.4), (0.712, 0.084, 0.474, 0.618, 0.049, 0.46, 0.105, 0.747, 0.404, 0.067, 0.133, 0.33)))
TONAL_PROVENANCE = {'source': 'music21.analysis.discrete', 'version': '9.9.2', 'profiles_sha256': 'd40198905f485641940f4b4341685b78aa842159050efe6de3547fb42b242a48', 'method': 'Pearson correlation to rotated duration-weighted profiles; not probability or general mode inference'}


def fraction(value):
    if not isinstance(value, str) or str(F(value)) != value:
        raise ValueError("Canonical rational string required")
    return F(value)


def relation(*, anchor=None, interval=None, pitch=None):
    """ONE equation: pitch = anchor + interval, solved in either direction."""
    values = [anchor, interval, pitch]
    if sum(v is None for v in values) > 1:
        raise ValueError("Underdetermined pitch relationship")
    a, d, p = [None if v is None else F(v) for v in values]
    if a is None:
        a = p - d
    if d is None:
        d = p - a
    if p is None:
        p = a + d
    if p != a + d:
        raise ValueError("Conflicting pitch relationship")
    return dict(anchor=str(a), interval=str(d), pitch=str(p))


def candidates(pitches):
    """Exhaustive exact pitch-class compatibility in a declared theory vocabulary.

    A singleton is not called a chord or a pedal. No missing chord tones are
    invented; incomplete/out-of-vocabulary sonorities remain unclassified.
    """
    pcs = sorted({F(p) % 12 for p in pitches})
    if len(pcs) < 2 or any(p.denominator != 1 for p in pcs):
        return []
    bass_pc = min(map(F, pitches)) % 12
    result = []
    for kind, pattern in THEORY_FORMS:
        if len(pattern) < 2 or len(pattern) != len(pcs):
            continue
        for root in range(12):
            if sorted((root + step) % 12 for step in pattern) == pcs:
                result.append(dict(root_pc=root, kind=kind, formula=list(pattern),
                                   bass_interval_pc=int((bass_pc - root) % 12),
                                   root_is_observed=root in pcs,
                                   status="theory_compatible_not_adjudicated"))
    return result


def context(pitches, ornament_timing_uncertain=False, unknown_count=0, timing_uncertain=False):
    values = list(map(F, pitches))
    possibilities = [] if ornament_timing_uncertain or timing_uncertain else candidates(values)
    return dict(known_members=len(values), unknown_members=unknown_count, attackness="unknown", evidence_status="partial_unknown_pitch" if unknown_count else "known_written_pitches", pitch_domain="written_base_not_sounding", distinct_pitch_classes=[str(p) for p in sorted({p % 12 for p in values})],
                sonority_kind="single_pitch" if len({p % 12 for p in values}) == 1 else "multiple_pitches" if values else "unpitched_or_empty",
                bass_pc=str(min(values) % 12) if values else None,
                chord_candidates=possibilities,
                harmonic_status="unresolved_source_timing" if timing_uncertain else "unresolved_ornament_timing" if ornament_timing_uncertain else "compatible_known_subset_only" if possibilities and unknown_count else "compatible_alternatives" if possibilities else "unresolved",
                base_key=dict(status="unknown", reason="No validated tonal-center inference in this boundary"),
                current_chord_mode=dict(status="unknown", reason="A chord does not determine a mode"))


TOP_FIELDS = {"tier", "schema", "events", "source_coverage", "scope"}
EVENT_FIELDS = {"id", "part_id", "bar", "voice", "beat", "note", "pitch", "onset_q", "duration_q"}
MEMBER_FIELDS = {"id", "bar", "voice", "beat", "note", "duration_q", "voicing_interval"}


def same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def coverage(value):
    if type(value) is not dict or set(value) != {"expected", "actual", "tracks", "layout_warnings", "timing_warnings"}:
        raise ValueError("Undeclared source quality payload")
    for key in ("expected", "actual", "tracks"):
        if type(value[key]) is not int or value[key] < 0:
            raise ValueError("Invalid coverage count")
    forms = {"conflicting_track_meter": {"bar", "reason"}, "conflicting_track_repeat": {"bar", "reason"},
             "missing_duration": {"part_id", "bar", "voice", "beat", "reason"},
             "nonpositive_duration": {"part_id", "bar", "voice", "beat", "reason"},
             "voice_overflows_bar": {"part_id", "bar", "voice", "reason", "duration_q", "span_q"}}
    for category in ("layout_warnings", "timing_warnings"):
        if type(value[category]) is not list: raise ValueError("Warning list required")
        for warning in value[category]:
            if type(warning) is not dict or warning.get("reason") not in forms or set(warning) != forms[warning["reason"]]:
                raise ValueError("Undeclared warning payload")
            if (category == "layout_warnings") != warning["reason"].startswith("conflicting_track_"):
                raise ValueError("Wrong warning owner")
            for key in set(warning) - {"reason", "duration_q", "span_q"}:
                if type(warning[key]) is not int or warning[key] < 0: raise ValueError("Invalid warning address")
            for key in set(warning) & {"duration_q", "span_q"}: fraction(warning[key])


def interpreted(group):
    pitches = [p for m in group["members"] if (p := member_pitch(group, m)) is not None]
    return context(pitches, any(F(m["duration_q"]) == 0 for m in group["members"]),
                   sum(m["voicing_interval"] is None for m in group["members"]), group["timing_uncertain"])


SIGNATURE_PROVENANCE = {
    "primary_client_vendor_sha256":"4e815b69e2bc8237e1680582c04a8c137029336675fb766c36dcffee7a16e6af",
    "primary_client_common_sha256":"a1e364ca45d13df13dc3cc47ca07e11fbbb6d8a9cecf38a943a6dc659c62e2cc",
    "verified_semantics":"signed fifths from transposeAs and abs count; explicit minor offset; missing inherits/null cancels",
    "coordinate_limit":"instrument/display transforms unverified; no established tonic claim"}


def signature_relation(*, source=None, parameters=None):
    """SAME declared-signature equations, retaining necessary spelling gauges.

    Verified Songsterr client semantics; NOT an inferred tonic/key or concert frame.
    """
    if (source is None)==(parameters is None): raise ValueError("Supply exactly one signature side")
    if source is not None:
        if type(source) is not dict or set(source)!={"accidentalCount","mode","transposeAs"}: raise ValueError("Unsupported source signature fields")
        count=source["accidentalCount"]; mode=source["mode"]; direction=source["transposeAs"]
        if type(count) is not int or mode not in ("major","minor") or direction not in ("b","#"): raise ValueError("Unsupported signature encoding; no guessed mode")
        fifths=(-1 if direction=="b" else 1)*abs(count)
        parameters=dict(signed_fifths=fifths,source_count_sign=-1 if count<0 else 1,
                        zero_accidental_spelling=direction if count==0 else None, declared_mode=mode)
    if type(parameters) is not dict or set(parameters)!={"signed_fifths","source_count_sign","zero_accidental_spelling","declared_mode"}: raise ValueError("Unsupported signature parameters")
    fifths=parameters["signed_fifths"]; sign=parameters["source_count_sign"]; zero=parameters["zero_accidental_spelling"]; mode=parameters["declared_mode"]
    if type(fifths) is not int or type(sign) is not int or sign not in (-1,1) or mode not in ("major","minor"): raise ValueError("Invalid signature parameters")
    if (fifths==0 and (zero not in ("b","#") or sign!=1)) or (fifths!=0 and zero is not None): raise ValueError("Invalid signature spelling gauge")
    rebuilt=dict(accidentalCount=sign*abs(fifths),mode=mode,transposeAs=zero if fifths==0 else "b" if fifths<0 else "#")
    return dict(parameters=parameters,source=rebuilt,notation_tonic_pc=(7*fifths-(3 if mode=="minor" else 0))%12,
                coordinate_domain="source_declared_signature", transposition_status="unverified_instrument_display_transform",
                status="declared_not_established_key")


def source_key_relations(lower):
    inventory=deepcopy(lower["source_key_inventory"])
    if type(inventory) is not list or len(inventory)!=lower["source_coverage"]["tracks"]: raise ValueError("Complete source key inventory required")
    parts={}
    for record in inventory:
        if set(record)!={"part_id","measure_count","end_q"} or any(type(record[k]) is not int or record[k]<0 for k in ("part_id","measure_count")) or fraction(record["end_q"])<0: raise ValueError("Invalid declaration inventory")
        if record["part_id"] in parts: raise ValueError("Duplicate declaration inventory")
        parts[record["part_id"]]=record
    if set(parts)!=set(range(lower["source_coverage"]["tracks"])): raise ValueError("Incomplete track inventory")
    definitions=[];lookup={};occurrences=[];seen=set()
    for row in lower["source_key_declarations"]:
        if set(row)!={"id","part_id","bar","onset_q","source_pointer","value"}: raise ValueError("Unsupported declaration facts")
        part,bar=row["part_id"],row["bar"]
        if type(part) is not int or part not in parts or type(bar) is not int or not 1<=bar<=parts[part]["measure_count"]: raise ValueError("Invalid declaration source address")
        if row["id"]!=f"key:{part}:{bar}" or row["source_pointer"]!=f"track-{part}.json#/measures/{bar-1}/keySignature" or (part,bar) in seen: raise ValueError("Declaration identity/ownership mismatch")
        seen.add((part,bar))
        if not 0<=fraction(row["onset_q"])<fraction(parts[part]["end_q"]): raise ValueError("Declaration outside source clock")
        decoded=signature_relation(source=row["value"]) if row["value"] is not None else None
        if decoded is not None: decoded.pop("source")
        token=json.dumps(decoded,sort_keys=True)
        if token not in lookup:
            lookup[token]=f"declared-signature:{len(definitions)}"
            definitions.append(dict(id=lookup[token],kind="cancel" if decoded is None else "signature",relation=decoded))
        occurrences.append(dict(id=row["id"],part_id=part,bar=bar,onset_q=row["onset_q"],definition_ref=lookup[token]))
    contexts=[]
    for part,record in sorted(parts.items()):
        ordered=sorted((o for o in occurrences if o["part_id"]==part),key=lambda o:o["bar"])
        if any(F(a["onset_q"])>=F(b["onset_q"]) for a,b in zip(ordered,ordered[1:])): raise ValueError("Declaration clocks disagree with source order")
        active=None;support=[];active_definitions=[];start="0";start_bar=1
        def add(end,end_bar):
            if F(end)>F(start): contexts.append(dict(part_id=part,start_q=start,end_q=end,start_bar=start_bar,end_bar_exclusive=end_bar,
                signature_state=None if active is None else dict(signed_fifths=active[0],declared_mode=active[1]), definition_refs=list(active_definitions), declaration_refs=list(support), status="unknown_no_active_declaration" if active is None else "inherited_source_declaration_not_tonal_truth"))
        for occurrence in ordered:
            definition=next(d for d in definitions if d["id"]==occurrence["definition_ref"])
            params=definition["relation"]["parameters"] if definition["kind"]=="signature" else None
            target=(params["signed_fifths"],params["declared_mode"]) if params is not None else None
            if target==active:
                support.append(occurrence["id"])
                if definition["id"] not in active_definitions: active_definitions.append(definition["id"])
                continue
            add(occurrence["onset_q"],occurrence["bar"])
            active=target;support=[occurrence["id"]];active_definitions=[definition["id"]];start=occurrence["onset_q"];start_bar=occurrence["bar"]
        add(record["end_q"],record["measure_count"]+1)
    return dict(provenance=deepcopy(SIGNATURE_PROVENANCE),definitions=definitions,occurrences=occurrences,inventory=inventory,contexts=contexts,
                inference_comparison="coordinate_frame_compatibility_unverified_no_agreement_or_conflict_claim",
                repeated_declarations_are_not_independent_votes=True)


def restore_source_keys(model):
    if set(model)!={"provenance","definitions","occurrences","inventory","contexts","inference_comparison","repeated_declarations_are_not_independent_votes"}: raise ValueError("Unsupported source-key payload")
    definitions={d["id"]:d for d in model["definitions"]}
    if len(definitions)!=len(model["definitions"]): raise ValueError("Duplicate signature definitions")
    rows=[]
    for o in model["occurrences"]:
        if set(o)!={"id","part_id","bar","onset_q","definition_ref"}: raise ValueError("Unsupported declaration occurrence")
        d=definitions[o["definition_ref"]]
        if set(d)!={"id","kind","relation"}: raise ValueError("Unsupported signature definition")
        if d["kind"]=="cancel":
            if d["relation"] is not None: raise ValueError("Cancellation cannot hide signature parameters")
            value=None
        elif d["kind"]=="signature":
            resolved=signature_relation(parameters=d["relation"]["parameters"])
            witness={k:v for k,v in resolved.items() if k!="source"}
            if not same(witness,d["relation"]): raise ValueError("Signature decoding conflicts with SAME equations")
            value=resolved["source"]
        else: raise ValueError("Unsupported signature kind")
        rows.append(dict(id=o["id"],part_id=o["part_id"],bar=o["bar"],onset_q=o["onset_q"],source_pointer=f"track-{o['part_id']}.json#/measures/{o['bar']-1}/keySignature",value=value))
    return dict(source_key_declarations=rows,source_key_inventory=deepcopy(model["inventory"]))


def analyze(tier1):
    """Consumes ONLY T1; published theory vocabulary is versioned shared code."""
    extended=tier1.get("schema")=="normalized-written-and-declared-keys/2"
    required=TOP_FIELDS|({"source_key_declarations","source_key_inventory"} if extended else set())
    expected_scope="base_pitch_metric_time_and_source_key_declarations" if extended else "base_pitch_and_metric_onset_duration_only"
    if set(tier1)!=required or type(tier1["tier"]) is not int or tier1["tier"]!=1 or tier1["schema"] not in ("normalized-written-fields/1","normalized-written-and-declared-keys/2") or tier1["scope"]!=expected_scope:
        raise ValueError("Unsupported T1 interface; no implicit field loss")
    coverage(tier1["source_coverage"])
    events = tier1["events"]
    if len({e["id"] for e in events}) != len(events):
        raise ValueError("Duplicate source occurrence")
    grouped = defaultdict(list)
    order = []
    for event in events:
        if set(event) != EVENT_FIELDS:
            raise ValueError("Unsupported event fields; declare reconstruction ownership first")
        if type(event["id"]) is not str or any(type(event[k]) is not int or event[k] < 0 for k in ("part_id", "bar", "voice", "beat", "note")):
            raise ValueError("Exact occurrence identity/address types required")
        onset, duration = fraction(event["onset_q"]), fraction(event["duration_q"])
        if onset < 0 or duration < 0:
            raise ValueError("Invalid event interval")
        if event["pitch"] is not None:
            fraction(event["pitch"])
        grouped[(event["part_id"], event["bar"], event["onset_q"])].append(event)
        order.append(event["id"])
    groups = []
    for index, ((part, bar, onset), members) in enumerate(sorted(grouped.items(), key=lambda x: (F(x[0][2]), x[0][1], x[0][0]))):
        pitches = [e["pitch"] for e in members if e["pitch"] is not None]
        anchor = str(min(map(F, pitches))) if pitches else None
        choices = []
        for event in members:
            choices.append(dict(id=event["id"], bar=event["bar"], voice=event["voice"], beat=event["beat"], note=event["note"],
                                duration_q=event["duration_q"], voicing_interval=relation(anchor=anchor, pitch=event["pitch"])["interval"] if event["pitch"] is not None else None))
        groups.append(dict(id=f"coattack:{index}", part_id=part, bar=bar, onset_q=onset,
                           timing_uncertain=any(w["bar"] == bar for k in ("layout_warnings", "timing_warnings") for w in tier1["source_coverage"][k]),
                           scope_type="coincident_written_note_starts", bass_register_anchor=anchor,
                           members=choices, interpretation=None))
    for group in groups: group["interpretation"] = interpreted(group)
    output = dict(tier=2, schema="musical-coattack-relations/1", input=deepcopy(tier1),
                  theory=deepcopy(THEORY_PROVENANCE), coattacks=groups,
                  realization_order=order, source_quality=deepcopy(tier1["source_coverage"]),
                  lower_scope=tier1["scope"], ensemble_coattacks=ensemble(groups), nominal_written_spans=written_spans(groups), tonal_evidence=tonal_evidence(groups))
    output["source_keys"] = source_key_relations(tier1) if extended else None
    # SAME relation checks operate on observed analysis and stripped reconstruction.
    validate(output)
    return output


def member_pitch(group, member):
    value = member["voicing_interval"]
    if value is None:
        return None
    return relation(anchor=fraction(group["bass_register_anchor"]), interval=fraction(value))["pitch"]


def ensemble(groups):
    """Separate ensemble interpretation; never confuse it with a part's context."""
    by_time = defaultdict(list)
    for group in groups:
        by_time[(group["bar"], group["onset_q"])].append(group)
    result = []
    for (bar, onset), frames in sorted(by_time.items(), key=lambda x: (F(x[0][1]), x[0][0])):
        pitches = [p for g in frames for m in g["members"] if (p := member_pitch(g, m)) is not None]
        result.append(dict(bar=bar, onset_q=onset, coattack_refs=[g["id"] for g in frames],
                           interpretation=context(pitches, any(F(m["duration_q"]) == 0 for g in frames for m in g["members"]), sum(m["voicing_interval"] is None for g in frames for m in g["members"]), any(g["timing_uncertain"] for g in frames))))
    return result


def written_spans(groups):
    """Half-open nominal notation overlaps; NOT acoustic sustain/attack inference.

    Only occurrence references are stored. Pitches are solved from the same
    group's register/interval equation. Source bars prevent invalid-clock merges.
    """
    by_bar = defaultdict(list)
    for group in groups:
        for member in group["members"]:
            start = F(group["onset_q"]); end = start + F(member["duration_q"])
            if end > start:
                by_bar[group["bar"]].append((start, end, group, member))
    result = []
    for bar, events in sorted(by_bar.items()):
        boundaries = sorted({t for a,b,_,_ in events for t in (a,b)})
        starts = defaultdict(list); ends = defaultdict(list); active = {}
        for event in events:
            starts[event[0]].append(event); ends[event[1]].append(event)
        for start, end in zip(boundaries, boundaries[1:]):
            for _,_,g,m in ends[start]: active.pop(m["id"], None)
            for event in starts[start]: active[event[3]["id"]] = event
            if not active: continue
            rows = sorted(active.values(), key=lambda row: row[3]["id"])
            def evidence(population):
                pitches = [p for _,_,g,m in population if (p := member_pitch(g,m)) is not None]
                return dict(occurrence_refs=[m["id"] for _,_,g,m in population],
                            starting_refs=[m["id"] for a,_,g,m in population if a == start],
                            continuing_refs=[m["id"] for a,_,g,m in population if a < start],
                            interpretation=context(pitches, False,
                              sum(m["voicing_interval"] is None for _,_,g,m in population),
                              any(g["timing_uncertain"] for _,_,g,m in population)))
            parts = defaultdict(list)
            for row in rows: parts[row[2]["part_id"]].append(row)
            result.append(dict(id=f"nominal-span:{len(result)}", bar=bar, start_q=str(start), end_q=str(end),
                               scope_type="half_open_nominal_written_duration_not_acoustic_sustain",
                               part_contexts=[dict(part_id=part, **evidence(population)) for part,population in sorted(parts.items())],
                               ensemble_context=evidence(rows)))
    return result


def profile_score(histogram, weights, tonic):
    """Published Pearson key-profile arithmetic, not a probability."""
    x = list(map(float,histogram)); y = [weights[(pc-tonic)%12] for pc in range(12)]
    ax, ay = sum(x)/12, sum(y)/12
    numerator = sum((a-ax)*(b-ay) for a,b in zip(x,y))
    denominator = (sum((a-ax)**2 for a in x)*sum((b-ay)**2 for b in y))**0.5
    return numerator/denominator if denominator else None


def tonal_evidence(groups):
    """All published major/minor profile candidates from SAME pitch/time facts.

    Pooled and separate-part views are evidence, not independent votes. Written
    duration is not an attack or performed accent. No arbitrary winner cutoff.
    """
    populations = [("song-pooled",groups)] + [(f"part:{part}",[g for g in groups if g["part_id"]==part]) for part in sorted({g["part_id"] for g in groups})]
    scopes = []
    for ident, population in populations:
        used_refs=[]; excluded_refs={k:[] for k in ("unknown_pitch", "noninteger_pitch", "zero_duration", "source_timing_uncertain")}
        histogram = [F(0) for _ in range(12)]; unknown=noninteger=zero=known=timing_excluded=0; duration=F(0)
        for group in population:
            for member in group["members"]:
                pitch = member_pitch(group,member); length = F(member["duration_q"])
                if pitch is None: unknown+=1; excluded_refs["unknown_pitch"].append(member["id"]); continue
                if F(pitch).denominator != 1: noninteger+=1; excluded_refs["noninteger_pitch"].append(member["id"]); continue
                if length == 0: zero+=1; excluded_refs["zero_duration"].append(member["id"]); continue
                if group["timing_uncertain"]: timing_excluded+=1; excluded_refs["source_timing_uncertain"].append(member["id"]); continue
                used_refs.append(member["id"]); known+=1; duration+=length; histogram[int(F(pitch)%12)] += length
        candidates = []
        for family, major, minor in TONAL_PROFILES:
            for quality, weights in (("major",major),("minor",minor)):
                for tonic in range(12):
                    candidates.append(dict(id=f"{ident}/{family}/{tonic}/{quality}", family=family, tonic_pc=tonic,
                                           quality=quality, score=profile_score(histogram,weights,tonic),
                                           score_type="uncalibrated_Pearson_correlation",
                                           reference_collection="major" if quality=="major" else "natural_minor_reference_only",
                                           reference_intervals=[0,2,4,5,7,9,11] if quality=="major" else [0,2,3,5,7,8,10]))
        timing = any(g["timing_uncertain"] for g in population)
        scopes.append(dict(id=ident, group_refs=[g["id"] for g in population],
                           used_member_refs=used_refs, excluded_member_refs=excluded_refs,
                           pitch_class_duration_q=list(map(str,histogram)), total_known_duration_q=str(duration),
                           known_positive_duration_members=known, unknown_pitch_members=unknown,
                           noninteger_pitch_members=noninteger, zero_duration_known_members=zero, timing_excluded_members=timing_excluded,
                           timing_evidence="source_timing_uncertain" if timing else "nominal_written_duration",
                           candidates=candidates, established_key=None, established_mode=None,
                           declaration_availability="not_in_preceding_input",
                           limitation="Distribution only: order-invariant, pooled part-doubling sensitive; no tonal-center or modal adjudication"))
    return dict(provenance=deepcopy(TONAL_PROVENANCE), scopes=scopes)


def validate(upper):
    if upper.get("schema") != "musical-coattack-relations/1" or type(upper.get("tier")) is not int or upper.get("tier") != 2:
        raise ValueError("Unsupported T2 interface")
    allowed = {"tier", "schema", "input", "theory", "coattacks", "realization_order", "source_quality", "lower_scope", "ensemble_coattacks", "nominal_written_spans", "tonal_evidence", "source_keys"}
    if set(upper) - allowed:
        raise ValueError("Undeclared upper payload")
    coverage(upper["source_quality"])
    if upper["lower_scope"] not in ("base_pitch_and_metric_onset_duration_only","base_pitch_metric_time_and_source_key_declarations"): raise ValueError("Unsupported lower scope")
    if not same(upper["theory"], THEORY_PROVENANCE):
        raise ValueError("Theory version mismatch")
    identities = []
    group_ids = set()
    context_keys = set()
    for group in upper["coattacks"]:
        if set(group) != {"id", "part_id", "bar", "timing_uncertain", "onset_q", "scope_type", "bass_register_anchor", "members", "interpretation"}:
            raise ValueError("Undeclared coattack payload")
        if type(group["id"]) is not str or group["id"] in group_ids: raise ValueError("Invalid/duplicate context identity")
        group_ids.add(group["id"])
        key = (group["part_id"], group["bar"], group["onset_q"])
        if key in context_keys or not group["members"]: raise ValueError("Duplicate/empty context ownership")
        context_keys.add(key)
        if any(type(group[k]) is not int or group[k] < 0 for k in ("part_id", "bar")) or type(group["timing_uncertain"]) is not bool: raise ValueError("Invalid context address")
        expected_uncertain = any(w["bar"] == group["bar"] for k in ("layout_warnings", "timing_warnings") for w in upper["source_quality"][k])
        if group["timing_uncertain"] != expected_uncertain: raise ValueError("Timing warning mismatch")
        if fraction(group["onset_q"]) < 0:
            raise ValueError("Negative onset")
        if group["scope_type"] != "coincident_written_note_starts":
            raise ValueError("Unsupported context scope")
        pitches = []
        intervals = []
        for member in group["members"]:
            if set(member) != MEMBER_FIELDS:
                raise ValueError("Undeclared member payload/hidden lower pitch")
            if type(member["id"]) is not str or any(type(member[k]) is not int or member[k] < 0 for k in ("bar", "voice", "beat", "note")) or member["bar"] != group["bar"]: raise ValueError("Invalid occurrence address")
            if fraction(member["duration_q"]) < 0:
                raise ValueError("Negative duration")
            identities.append(member["id"])
            pitch = member_pitch(group, member)
            if pitch is not None:
                pitches.append(pitch)
                intervals.append(fraction(member["voicing_interval"]))
        if intervals and min(intervals) != 0:
            raise ValueError("Bass anchor must be the realized lowest member")
        if not intervals and group["bass_register_anchor"] is not None:
            raise ValueError("Unpitched group cannot hide a pitch anchor")
        if not same(interpreted(group), group["interpretation"]):
            raise ValueError("Harmonic context conflicts with shared pitch relationships")
    if len(set(identities)) != len(identities) or set(upper["realization_order"]) != set(identities) or len(upper["realization_order"]) != len(identities):
        raise ValueError("Occurrence ownership/order mismatch")
    quality = upper["source_quality"]
    if quality["actual"] != len(identities) or quality["expected"] != len(identities): raise ValueError("Coverage does not match owned occurrences")
    if any(g["part_id"] >= quality["tracks"] for g in upper["coattacks"]): raise ValueError("Part outside source track inventory")
    if not same(ensemble(upper["coattacks"]), upper["ensemble_coattacks"]):
        raise ValueError("Ensemble context conflicts with part relationships")

    if not same(written_spans(upper["coattacks"]), upper["nominal_written_spans"]):
        raise ValueError("Nominal overlap context conflicts with shared pitch/time relationships")

    if not same(tonal_evidence(upper["coattacks"]), upper["tonal_evidence"]):
        raise ValueError("Tonal evidence conflicts with shared pitch/duration relationships")
    if upper["lower_scope"]=="base_pitch_metric_time_and_source_key_declarations":
        facts=restore_source_keys(upper["source_keys"])
        facts["source_coverage"]=upper["source_quality"]
        if not same(source_key_relations(facts),upper["source_keys"]): raise ValueError("Source declaration contexts conflict with shared signature relations")
    elif upper["source_keys"] is not None: raise ValueError("Source keys outside declared lower scope")
    if "input" in upper and not same(upper["input"], realize(upper)):
        raise ValueError("Nested lower tier conflicts with its higher relationships")


def strip_lower(upper):
    result = deepcopy(upper)
    result.pop("input")
    return result


def reconstruct(upper, controls):
    """Blind exact inverse; no access to input/source or a separate music engine."""
    if "input" in upper:
        raise ValueError("Remove the entire lower tier before inverse QA")
    if controls != {"variation": 0} or type(controls["variation"]) not in (int, float):
        raise ValueError("Explicit 0% control required; proposals are not implemented")
    validate(upper)
    return realize(upper)


def realize(upper):
    """Materialize already-validated shared equations; never interprets labels."""
    events = {}
    for group in upper["coattacks"]:
        for member in group["members"]:
            event = {k: deepcopy(member[k]) for k in ("id", "bar", "voice", "beat", "note", "duration_q")}
            event.update(part_id=group["part_id"], onset_q=group["onset_q"], pitch=member_pitch(group, member))
            events[event["id"]] = event
    result = dict(tier=1, schema="normalized-written-fields/1", events=[events[i] for i in upper["realization_order"]],
                source_coverage=deepcopy(upper["source_quality"]), scope=upper["lower_scope"])
    if upper["source_keys"] is not None:
        result.update(schema="normalized-written-and-declared-keys/2", **restore_source_keys(upper["source_keys"]))
    return result


def note_context(upper, ident):
    """On-demand conditional coordinates, not a copied note stream per context."""
    validate(upper)
    for group in upper["coattacks"]:
        for member in group["members"]:
            if member["id"] != ident:
                continue
            pitch = member_pitch(group, member)
            coordinates = []
            if pitch is not None:
                for candidate in group["interpretation"]["chord_candidates"]:
                    root_register = relation(pitch=group["bass_register_anchor"], interval=candidate["bass_interval_pc"])["anchor"]
                    distance = F(relation(anchor=root_register, pitch=pitch)["interval"])
                    coordinates.append(dict(root_pc=candidate["root_pc"], kind=candidate["kind"],
                                            root_register_reference=root_register, reference_is_not_an_added_note=True,
                                            unwrapped_semitones=str(distance), semitones_mod12=str(distance % 12), relative_octaves=int(distance // 12),
                                            chord_member=distance % 12 in candidate["formula"],
                                            status="conditional_on_candidate_not_a_note_function"))
            return dict(occurrence_ref=ident, coattack_ref=group["id"], onset_q=group["onset_q"], duration_q=member["duration_q"],
                        coordinates=coordinates, interval_of_note_base_key=None,
                        interval_of_note_current_chord_mode=None,
                        unknown_reason="Key and chord-relative mode not established")
    raise KeyError(ident)


def note_context_at(upper, ident, at_q, ensemble_scope=False):
    """A held written note against its CURRENT nominal overlap context.

    Context membership and root coordinates derive from existing occurrence
    relationships; no second note stream or chord guesses.
    """
    validate(upper)
    at = fraction(at_q)
    index = {m["id"]:(g,m) for g in upper["coattacks"] for m in g["members"]}
    group, member = index[ident]
    pitch = member_pitch(group, member)
    matches = [span for span in upper["nominal_written_spans"] if span["bar"] == group["bar"]
               and F(span["start_q"]) <= at < F(span["end_q"])]
    if not matches: raise ValueError("No nominal written-duration context at requested time")
    span = matches[0]
    evidence = span["ensemble_context"] if ensemble_scope else next((p for p in span["part_contexts"] if p["part_id"] == group["part_id"]), None)
    if evidence is None or ident not in evidence["occurrence_refs"]: raise ValueError("Note is not present at requested nominal time")
    pitches = [p for ref in evidence["occurrence_refs"] if (p := member_pitch(*index[ref])) is not None]
    coordinates = []
    if pitch is not None:
        bass = min(map(F,pitches))
        for candidate in evidence["interpretation"]["chord_candidates"]:
            root = relation(pitch=bass, interval=candidate["bass_interval_pc"])["anchor"]
            distance = F(relation(anchor=root,pitch=pitch)["interval"])
            coordinates.append(dict(root_pc=candidate["root_pc"], kind=candidate["kind"], root_register_reference=root,
                                    unwrapped_semitones=str(distance), semitones_mod12=str(distance%12),
                                    relative_octaves=int(distance//12), chord_member=distance%12 in candidate["formula"],
                                    reference_is_not_an_added_note=True,
                                    status="conditional_on_nominal_overlap_candidate_not_note_function"))
    return dict(occurrence_ref=ident, span_ref=span["id"], at_q=at_q,
                context_scope="ensemble" if ensemble_scope else "part", coordinates=coordinates,
                interval_of_note_base_key=None, interval_of_note_current_chord_mode=None,
                interpretation=evidence["interpretation"])


def tonal_note_context(upper, ident, candidate_id, at_q=None, ensemble_scope=True):
    """Exact note/chord coordinates CONDITIONAL on one explicit tonal candidate.

    No chosen key, spelling, diatonic function or emotional role is implied.
    """
    validate(upper)
    index = {m["id"]:(g,m) for g in upper["coattacks"] for m in g["members"]}
    group, member = index[ident]; pitch = member_pitch(group,member)
    found = [(scope,c) for scope in upper["tonal_evidence"]["scopes"] for c in scope["candidates"] if c["id"]==candidate_id]
    if len(found)!=1: raise ValueError("Exact tonal candidate ID required")
    scope,candidate=found[0]
    if group["id"] not in scope["group_refs"]: raise ValueError("Note is outside tonal evidence scope")
    coordinate=None
    if pitch is not None:
        # Pitch-class tonic reference at MIDI0-octave; retains signed register.
        distance=F(relation(anchor=candidate["tonic_pc"],pitch=pitch)["interval"])
        coordinate=dict(tonic_pc=candidate["tonic_pc"],unwrapped_semitones=str(distance), semitones_mod12=str(distance%12),
                        relative_octaves=int(distance//12), tonic_reference_convention="tonic_pc_in_MIDI_zero_octave_not_observed_tonic_note", reference_is_not_an_added_note=True, reference_collection=candidate["reference_collection"],
                        in_reference_collection=distance%12 in candidate["reference_intervals"],
                        status="conditional_reference_collection_not_established_key_or_function")
    if at_q is not None:
        local = note_context_at(upper,ident,at_q,ensemble_scope)
        harmony = local["interpretation"]
        harmonic_context = dict(span_ref=local["span_ref"], at_q=at_q, scope=local["context_scope"])
    else:
        harmony = group["interpretation"]
        harmonic_context = dict(coattack_ref=group["id"], at_q=group["onset_q"], scope="part_written_start")
    chords=[dict(chord_root_pc=c["root_pc"],kind=c["kind"],root_interval_from_candidate_tonic=(c["root_pc"]-candidate["tonic_pc"])%12,
                 status="conditional_root_coordinate_not_harmonic_function") for c in harmony["chord_candidates"]]
    return dict(occurrence_ref=ident, tonal_scope_ref=scope["id"], candidate_ref=candidate_id, harmonic_context_ref=harmonic_context,
                interval_of_note_base_key_candidate=coordinate, interval_of_note_current_chord_mode=None,
                chord_root_coordinates=chords, established_key=None, established_mode=None)


def declared_key_context(upper, part_id, at_q):
    """Compare source declarations to evidence ONLY conditional on pitch frame.

    A matching candidate coordinate is not inferred agreement or tonal truth.
    """
    validate(upper); at=fraction(at_q)
    if type(part_id) is not int or part_id<0: raise ValueError("Exact nonnegative part ID required")
    model=upper["source_keys"]
    if model is None: return dict(status="source_declarations_not_in_input_scope")
    if part_id not in {r["part_id"] for r in model["inventory"]}: raise ValueError("Part outside source inventory")
    matches=[c for c in model["contexts"] if c["part_id"]==part_id and F(c["start_q"])<=at<F(c["end_q"])]
    if len(matches)!=1: raise ValueError("No unique source declaration context at requested point")
    context=matches[0]; state=context["signature_state"]
    if state is None: return dict(part_id=part_id,at_q=at_q,status="unknown_no_active_source_declaration",declaration_refs=context["declaration_refs"],established_key=None)
    definition=next(d for d in model["definitions"] if d["id"]==context["definition_refs"][0])
    tonic=definition["relation"]["notation_tonic_pc"]; mode=state["declared_mode"]
    scores=[]
    for scope in upper["tonal_evidence"]["scopes"]:
        if scope["id"] not in ("song-pooled",f"part:{part_id}"): continue
        for candidate in scope["candidates"]:
            if candidate["tonic_pc"]==tonic and candidate["quality"]==mode:
                scores.append(dict(scope_ref=scope["id"],candidate_ref=candidate["id"],score=candidate["score"],
                                   condition="ONLY_if_source_signature_and_note_coordinate_frames_align"))
    return dict(part_id=part_id,at_q=at_q,source_context_span=[context["start_q"],context["end_q"]],
                declaration_refs=context["declaration_refs"],declared_signed_fifths=state["signed_fifths"],
                declared_mode=mode,decoded_notation_tonic_pc=tonic,profile_scores_if_frames_align=scores,
                coordinate_frame_compatibility="unverified",agreement_or_conflict="not_asserted",established_key=None)


def transpose(upper, semitones):
    """Deterministic relation intervention, NOT an artist-style percentage lever."""
    changed = strip_lower(upper) if "input" in upper else deepcopy(upper)
    for group in changed["coattacks"]:
        if group["bass_register_anchor"] is not None:
            group["bass_register_anchor"] = relation(anchor=group["bass_register_anchor"], interval=semitones)["pitch"]
        pitches = [p for m in group["members"] if (p := member_pitch(group, m)) is not None]
        group["interpretation"] = interpreted(group)
    changed["ensemble_coattacks"] = ensemble(changed["coattacks"])
    changed["nominal_written_spans"] = written_spans(changed["coattacks"])
    changed["tonal_evidence"] = tonal_evidence(changed["coattacks"])
    validate(changed)
    return changed
