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

TEMPORAL_PROFILE = {'family': 'AardenEssen', 'major': (17.7661, 0.145624, 14.9265, 0.160186, 19.8049, 11.3587, 0.291248, 22.062, 0.145624, 8.15494, 0.232998, 4.95122), 'minor': (18.2648, 0.737619, 14.0499, 16.8599, 0.702494, 14.4362, 0.702494, 18.6161, 4.56621, 1.93186, 7.37619, 1.75623)}
TEMPORAL_PROVENANCE = {'source': 'music21.analysis.floatingKey intended immutable weighted sum', 'version': '9.9.2', 'window': 4, 'neighbor_weight': '1/(abs(measure_distance)+1)', 'profile_sha256': 'b38cc7f0bfb0927f2a4f430d4e6cd9ed96304c2000975fbb889c8c4b0d63d36d', 'native_source_sha256': '8fd897f0812d726bf466733c4e77426b7bee14fd79070c50460f9aea2e969b64', 'native_divergence': 'Fixes cached-vector mutation; retains empty/undefined placeholders; does not claim full native parity', 'allocation': 'written_onset_measure_full_notated_duration_not_clipped_sustain', 'inference': 'offline_future_neighbors_included_not_key_truth'}


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


def geometry_relation(*, source=None, parameters=None):
    """One canonical measure geometry, SAME metric-unit/start/advance equations."""
    if (source is None)==(parameters is None): raise ValueError("Supply exactly one geometry side")
    if source is not None:
        if set(source)!={"source_format","source_id","frames","parts","first_notated_span_q"}: raise ValueError("Unsupported geometry facts")
        frames=[]
        for row in source["frames"]:
            if set(row)!={"id","ordinal","label","start_q","span_q","signature","meter_source","meter_source_frame"}: raise ValueError("Unsupported frame facts")
            signature=row["signature"]
            if type(signature) is not list or len(signature)!=2 or any(type(v) is not int or v<=0 for v in signature): raise ValueError("Source meter required; no inferred 4/4")
            frames.append(dict(id=row["id"],ordinal=row["ordinal"],label=row["label"],start_q=row["start_q"],duration_q=row["span_q"],
                               meter=dict(beats=signature[0],beat_unit_q=str(F(4,signature[1]))),meter_source=row["meter_source"],meter_source_frame=row["meter_source_frame"]))
        parameters=dict(source_format=source["source_format"],source_id=source["source_id"],frames=frames,parts=deepcopy(source["parts"]),first_notated_span_q=source["first_notated_span_q"])
    if set(parameters)!={"source_format","source_id","frames","parts","first_notated_span_q"}: raise ValueError("Unsupported geometry parameters")
    if parameters["source_format"] not in ("songsterr_json","musicxml") or type(parameters["source_id"]) is not str or not 1<=len(parameters["source_id"])<=128: raise ValueError("Typed geometry provenance required")
    frames=[];cursor=F(0);last_explicit=0
    for ordinal,row in enumerate(parameters["frames"],1):
        if set(row)!={"id","ordinal","label","start_q","duration_q","meter","meter_source","meter_source_frame"}: raise ValueError("Unsupported measure geometry")
        if row["id"]!=f"measure:{ordinal}" or type(row["ordinal"]) is not int or row["ordinal"]!=ordinal or type(row["label"]) is not str or len(row["label"])>32: raise ValueError("Frame identity mismatch")
        meter=row["meter"]
        if set(meter)!={"beats","beat_unit_q"} or type(meter["beats"]) is not int or meter["beats"]<=0: raise ValueError("Invalid meter")
        unit=fraction(meter["beat_unit_q"]); denominator=F(4)/unit if unit>0 else F(0)
        if denominator.denominator!=1 or denominator<=0: raise ValueError("Metric unit must reconstruct source denominator")
        start,span=fraction(row["start_q"]),fraction(row["duration_q"])
        if start!=cursor or span<=0: raise ValueError("Noncontiguous/invalid written measure clock")
        cursor=F(relation(anchor=start,interval=span)["pitch"])
        witness=row["meter_source_frame"]
        if type(witness) is not int or not 1<=witness<=ordinal or row["meter_source"] not in ("explicit","inherited"): raise ValueError("Unverified meter source")
        if row["meter_source"]=="explicit":
            if witness!=ordinal: raise ValueError("Explicit meter source mismatch")
            last_explicit=ordinal
        if row["meter_source"]=="inherited":
            if witness!=last_explicit or witness>=ordinal or parameters["frames"][witness-1]["meter_source"]!="explicit" or not same(parameters["frames"][witness-1]["meter"],meter): raise ValueError("Meter inheritance witness mismatch")
        frames.append(dict(id=row["id"],ordinal=ordinal,label=row["label"],start_q=str(start),span_q=str(span),signature=[meter["beats"],int(denominator)],meter_source=row["meter_source"],meter_source_frame=witness))
    seen=set()
    for part in parameters["parts"]:
        if set(part)!={"part_id","frame_refs","source_pickup_declared"} or type(part["part_id"]) is not int or part["part_id"]<0 or part["part_id"] in seen: raise ValueError("Invalid geometry part membership")
        seen.add(part["part_id"])
        if part["source_pickup_declared"] is not None and type(part["source_pickup_declared"]) is not bool: raise ValueError("Typed pickup declaration required")
        if part["frame_refs"] != [f"measure:{i+1}" for i in range(len(part["frame_refs"]))] or len(part["frame_refs"])>len(frames): raise ValueError("Unaligned/missing source measure membership")
    if seen!=set(range(len(seen))) or max((len(p["frame_refs"]) for p in parameters["parts"]),default=0)!=len(frames): raise ValueError("Incomplete geometry inventory")
    if frames:
        observed=fraction(parameters["first_notated_span_q"])
        if observed<0: raise ValueError("Invalid notated extent witness")
        nominal=F(4*frames[0]["signature"][0],frames[0]["signature"][1])
        if parameters["source_format"]=="songsterr_json":
            declared=any(p["source_pickup_declared"] is True for p in parameters["parts"])
            expected=observed if declared and 0<observed<nominal else nominal
            if F(frames[0]["span_q"])!=expected: raise ValueError("Shortening lacks source pickup and observed extent witnesses")
            if any(F(f["span_q"])!=F(4*f["signature"][0],f["signature"][1]) for f in frames[1:]): raise ValueError("Unsupported source partial measure")
    elif parameters["first_notated_span_q"] is not None: raise ValueError("Empty geometry cannot hide extent")
    rebuilt=dict(source_format=parameters["source_format"],source_id=parameters["source_id"],frames=frames,parts=deepcopy(parameters["parts"]),first_notated_span_q=parameters["first_notated_span_q"])
    return dict(parameters=parameters,source=rebuilt)


def geometry_inventory(geometry):
    frames=geometry["frames"]
    return [dict(part_id=p["part_id"],measure_count=len(p["frame_refs"]),end_q=str(F(frames[len(p["frame_refs"])-1]["start_q"])+F(frames[len(p["frame_refs"])-1]["duration_q"])) if p["frame_refs"] else "0") for p in geometry["parts"]]


def materialized_source_keys(upper):
    model=deepcopy(upper["source_keys"])
    if model is not None and "inventory_ref" in model:
        if model.pop("inventory_ref")!="measure_geometry": raise ValueError("Unsupported inventory reference")
        model["inventory"]=geometry_inventory(upper["measure_geometry"])
    return model


def analyze(tier1):
    """Consumes ONLY T1; published theory vocabulary is versioned shared code."""
    ties_owned=tier1.get('schema')=='normalized-written-tie-context/4'
    geometry_owned=ties_owned or tier1.get("schema")=="normalized-written-context-facts/3"
    extended=geometry_owned or tier1.get("schema")=="normalized-written-and-declared-keys/2"
    required=TOP_FIELDS|({"source_key_declarations","source_key_inventory"} if extended else set())|({"measure_geometry"} if geometry_owned else set())|({'tie_notation'} if ties_owned else set())
    expected_scope='written_context_geometry_keys_and_tie_notation' if ties_owned else "written_context_facts_geometry_and_optional_source_keys" if geometry_owned else "base_pitch_metric_time_and_source_key_declarations" if extended else "base_pitch_and_metric_onset_duration_only"
    if set(tier1)!=required or type(tier1["tier"]) is not int or tier1["tier"]!=1 or tier1["schema"] not in ("normalized-written-fields/1","normalized-written-and-declared-keys/2","normalized-written-context-facts/3",'normalized-written-tie-context/4') or tier1["scope"]!=expected_scope:
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
    output = dict(tier=2, schema="musical-context-relations/2", input=deepcopy(tier1),
                  theory=deepcopy(THEORY_PROVENANCE), coattacks=groups,
                  realization_order=order, source_quality=deepcopy(tier1["source_coverage"]),
                  lower_scope=tier1["scope"], ensemble_coattacks=ensemble(groups), nominal_written_spans=written_spans(groups), tonal_evidence=tonal_evidence(groups))
    output["measure_geometry"] = geometry_relation(source=tier1["measure_geometry"])["parameters"] if geometry_owned else None
    if geometry_owned and not same(geometry_inventory(output["measure_geometry"]),tier1["source_key_inventory"]): raise ValueError("Summary differs from canonical geometry")
    output["source_keys"] = source_key_relations(tier1) if extended and tier1["source_key_declarations"] is not None else None
    if geometry_owned and output["source_keys"] is not None:
        output["source_keys"].pop("inventory")
        output["source_keys"]["inventory_ref"]="measure_geometry"
    output["temporal_tonal_evidence"] = temporal_tonal_evidence(groups,output["measure_geometry"])
    if ties_owned:output['written_ties']=lift_written_ties(tier1['tie_notation'],output)
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


def immutable_temporal_scores(raw, window):
    """Intended inverse-distance sum; NEVER mutates raw/cached neighbor scores."""
    if type(window) is not int or window<0: raise ValueError("Nonnegative integer temporal window required")
    vectors=[v for v in raw if v is not None]
    if vectors and any(len(v)!=len(vectors[0]) for v in vectors): raise ValueError("Inconsistent temporal candidate vocabulary")
    result=[]
    for index,base in enumerate(raw):
        if base is None: result.append(None); continue
        neighbors=[(j,values) for j,values in enumerate(raw) if abs(j-index)<=window and values is not None]
        result.append([sum(values[k]/(abs(j-index)+1) for j,values in neighbors) for k in range(len(base))])
    return result


def temporal_tonal_evidence(groups, geometry):
    """Offline timed key CANDIDATES, using true frames and written-onset evidence."""
    if geometry is None:return None
    allframes=geometry["frames"]; index={g["id"]:g for g in groups}
    populations=[("song-pooled",groups,[f["id"] for f in allframes])]
    populations += [(f"part:{p['part_id']}",[g for g in groups if g["part_id"]==p["part_id"]],p["frame_refs"]) for p in geometry["parts"]]
    scopes=[]
    for scope,population,frame_refs in populations:
        grouped=defaultdict(list)
        for group in population: grouped[group["bar"]].append(group)
        records=[];raw=[]
        for frame_ref in frame_refs:
            frame=allframes[int(frame_ref.split(":")[1])-1]; ordinal=frame["ordinal"]
            histogram=[F(0) for _ in range(12)];used=[];excluded={k:[] for k in ("unknown_pitch","noninteger_pitch","zero_duration","source_timing_uncertain")};cross=[]
            end=F(frame["start_q"])+F(frame["duration_q"])
            for group in grouped[ordinal]:
                for member in group["members"]:
                    pitch=member_pitch(group,member);length=F(member["duration_q"])
                    if F(group["onset_q"])+length>end:cross.append(member["id"])
                    reason="unknown_pitch" if pitch is None else "noninteger_pitch" if F(pitch).denominator!=1 else "zero_duration" if length==0 else "source_timing_uncertain" if group["timing_uncertain"] else None
                    if reason: excluded[reason].append(member["id"]);continue
                    used.append(member["id"]);histogram[int(F(pitch)%12)]+=length
            vector=[profile_score(histogram,TEMPORAL_PROFILE[quality],tonic) for quality in ("major","minor") for tonic in range(12)]
            vector=None if all(v is None for v in vector) else vector
            raw.append(vector)
            records.append(dict(id=f"temporal:{scope}:{ordinal}",frame_ref=frame_ref,used_member_refs=used,excluded_member_refs=excluded,cross_frame_duration_refs=cross,
                                pitch_class_duration_q=list(map(str,histogram)),raw_scores=vector if vector is not None else [None]*24,smoothed_scores=[None]*24,candidates=[],contributing_frame_refs=[],
                                status="unknown_no_defined_distribution" if vector is None else "major_minor_hypotheses_not_established_key"))
        smoothed=immutable_temporal_scores(raw,TEMPORAL_PROVENANCE["window"])
        for i,record in enumerate(records):
            record["smoothed_scores"]=smoothed[i] if smoothed[i] is not None else [None]*24
            record["contributing_frame_refs"]=[dict(frame_ref=frame_refs[j],distance=j-i,weight=str(F(1,abs(j-i)+1))) for j,v in enumerate(raw) if raw[i] is not None and v is not None and abs(j-i)<=TEMPORAL_PROVENANCE["window"]]
            for k,(quality,tonic) in enumerate((q,t) for q in ("major","minor") for t in range(12)):
                record["candidates"].append(dict(id=f"{record['id']}/AardenEssen/{tonic}/{quality}",family="AardenEssen",tonic_pc=tonic,quality=quality,raw_score=raw[i][k] if raw[i] is not None else None,smoothed_score=smoothed[i][k] if smoothed[i] is not None else None,
                                                  score_type="uncalibrated_inverse_distance_sum",reference_collection="major" if quality=="major" else "natural_minor_reference_only",reference_intervals=[0,2,4,5,7,9,11] if quality=="major" else [0,2,3,5,7,8,10]))
        scopes.append(dict(id=scope,measures=records,established_key=None,established_mode=None))
    return dict(provenance=deepcopy(TEMPORAL_PROVENANCE),scopes=scopes)


def harmonic_template_scores(weights):
    """Published Pardo-Birmingham Figure3 score, no stylistic tie breakers.

    Positive note-cell evidence minus negative evidence minus missing PCs.
    Weights count nominal minimal segments, not seconds or note durations.
    """
    if len(weights)!=12 or any(type(v) is not int or v<0 for v in weights):raise ValueError('Twelve nonnegative integer note-cell weights required')
    kinds=('major','dominant-seventh','minor','diminished-seventh','half-diminished-seventh','diminished')
    forms=dict(THEORY_FORMS);total=sum(weights);rows=[]
    for kind in kinds:
        formula=forms[kind]
        for root in range(12):
            pcs={(root+d)%12 for d in formula};positive=sum(weights[pc] for pc in pcs);missing=sum(weights[pc]==0 for pc in pcs)
            rows.append(dict(root_pc=root,kind=kind,formula=list(formula),positive=positive,negative=total-positive,missing=missing,score=2*positive-total-missing))
    return rows


def harmonic_span_evidence(upper,start_q,end_q,part_id=None,max_edges=50000):
    """Bounded deterministic T2 refinement, not a separate generation engine.

    Every candidate boundary is a nominal written occurrence start/end; request
    edges clip already-active notes without inventing attacks. Full DAG search
    within the declared interval; no hidden bar cuts or musical duration cap.
    """
    validate(upper);start,end=fraction(start_q),fraction(end_q)
    if start<0 or end<=start:raise ValueError('Positive ordered explicit query interval required')
    if part_id is not None and (type(part_id) is not int or not 0<=part_id<upper['source_quality']['tracks']):raise ValueError('Typed owned part scope required')
    if type(max_edges) is not int or max_edges<1:raise ValueError('Positive explicit edge resource limit required')
    request=dict(start_q=start_q,end_q=end_q,part_id=part_id,max_edges=max_edges)
    if upper['measure_geometry'] is not None:
        inventory=geometry_inventory(upper['measure_geometry'])
        horizon=max((F(r['end_q']) for r in inventory if part_id is None or r['part_id']==part_id),default=F(0))
        if end>horizon:raise ValueError('Query beyond owned source measure geometry')
    rows=[];excluded=dict(zero_duration=[],unknown_pitch=[]);uncertain=[]
    for group in upper['coattacks']:
        if part_id is not None and group['part_id']!=part_id:continue
        for member in group['members']:
            a=F(group['onset_q']);b=a+F(member['duration_q'])
            if b==a:
                if start<=a<end:excluded['zero_duration'].append(member['id'])
                continue
            if b<=start or a>=end:continue
            if group['timing_uncertain']:uncertain.append(member['id'])
            pitch=member_pitch(group,member)
            if pitch is None or F(pitch).denominator!=1:excluded['unknown_pitch'].append(member['id'])
            rows.append(dict(occurrence_ref=member['id'],start=max(a,start),end=min(b,end),pitch=pitch,started_before_request=a<start))
    result=dict(analytical_stage='deterministic_refinement_of_T2_nominal_relations_not_new_pitch_owner',request=request,
                method=dict(source='Pardo-Birmingham2002 Figure3 + full DAG relaxation',url='https://interactiveaudiolab.github.io/assets/papers/pardo-birmingham-cmj02.pdf',vocabulary='published_six_chord_families_72_roots',weight='count_of_nominal_minimal_segments_per_occurrence',tie_breaking='NONE_all_equal_scores_and_optimal_predecessors_retained',limits='No key/mode/function/style inference; written intervals not acoustic sustain; no prior or resolution tie-breaks'),
                excluded_member_refs=excluded,source_timing_uncertain_refs=uncertain)
    if uncertain:return dict(result,status='NOT_RUN_SOURCE_TIMING_UNCERTAIN')
    eligible=[r for r in rows if r['pitch'] is not None and F(r['pitch']).denominator==1]
    unknown=[r for r in rows if r not in eligible]
    overlays=[dict(occurrence_ref=r['occurrence_ref'],start_q=str(r['start']),end_q=str(r['end']),status='unknown_or_noninteger_pitch_not_in_scoring_grid') for r in unknown]
    result['unknown_pitch_overlays']=overlays
    points=sorted({start,end}|{t for r in eligible for t in (r['start'],r['end'])});n=len(points);edge_count=n*(n-1)//2
    result.update(partition_points_q=list(map(str,points)),candidate_edges=edge_count)
    if edge_count>max_edges:return dict(result,status='NOT_RUN_RESOURCE_LIMIT',required_edges=edge_count)
    cells=[];prefix=[[0]*12]
    for a,b in zip(points,points[1:]):
        active=[r for r in eligible if r['start']<=a<r['end']];uncertain_active=[r for r in unknown if r['start']<b and r['end']>a];weights=[0]*12
        for row in active:
            if row['pitch'] is not None and F(row['pitch']).denominator==1:weights[int(F(row['pitch'])%12)]+=1
        prefix.append([x+y for x,y in zip(prefix[-1],weights)])
        cells.append(dict(start_q=str(a),end_q=str(b),occurrence_refs=[r['occurrence_ref'] for r in active],
                          unknown_overlapping_refs=[r['occurrence_ref'] for r in uncertain_active],
                          already_active_at_request_refs=[r['occurrence_ref'] for r in active if r['started_before_request']],
                          status='no_known_pitched_evidence' if not any(weights) else 'conditional_known_pitch_subset' if uncertain_active else 'known_written_pitch_evidence'))
    # Predecessor lists retain ALL globally optimal boundary alternatives.
    best=[0]+[None]*(n-1);predecessors=[[] for _ in range(n)];edge_cache={}
    for stop in range(1,n):
        for begin in range(stop):
            weights=[b-a for a,b in zip(prefix[begin],prefix[stop])]
            scores=harmonic_template_scores(weights) if any(weights) else []
            local=max((r['score'] for r in scores),default=0)
            edge_cache[begin,stop]=(local,weights,[r for r in scores if r['score']==local])
            value=best[begin]+local
            if best[stop] is None or value>best[stop]:best[stop]=value;predecessors[stop]=[begin]
            elif value==best[stop]:predecessors[stop].append(begin)
    path_count=[1]+[0]*(n-1)
    for stop in range(1,n):path_count[stop]=sum(path_count[p] for p in predecessors[stop])
    suffix=[0]*n;suffix[-1]=1
    for stop in range(n-1,0,-1):
        for begin in predecessors[stop]:suffix[begin]+=suffix[stop]
    mandatory=[i for i in range(n) if path_count[i]*suffix[i]==path_count[-1]]
    label_union=[{} for _ in cells];no_evidence=[False]*len(cells)
    for stop in range(1,n):
        if not suffix[stop]:continue
        for begin in predecessors[stop]:
            labels=edge_cache[begin,stop][2]
            for cell_index in range(begin,stop):
                if not labels:no_evidence[cell_index]=True
                for label in labels:label_union[cell_index][label['root_pc'],label['kind']]=dict(root_pc=label['root_pc'],kind=label['kind'],formula=label['formula'])
    consensus=[]
    for i,cell in enumerate(cells):
        labels=[label_union[i][key] for key in sorted(label_union[i])]
        consensus.append(dict(start_q=cell['start_q'],end_q=cell['end_q'],candidate_labels=labels,no_pitched_evidence_possibility=no_evidence[i],
                              status='unanimous_under_this_objective' if len(labels)==1 and not no_evidence[i] else 'ambiguous_under_this_objective' if labels else 'no_pitched_evidence',
                              direct_evidence_status=cell['status']))
    path=[];cursor=n-1
    while cursor:
        begin=min(predecessors[cursor]);score,weights,labels=edge_cache[begin,cursor]
        refs=list(dict.fromkeys(ref for c in cells[begin:cursor] for ref in c['occurrence_refs']))
        partial=[o['occurrence_ref'] for o in overlays if F(o['start_q'])<points[cursor] and F(o['end_q'])>points[begin]]
        path.append(dict(start_index=begin,end_index=cursor,start_q=str(points[begin]),end_q=str(points[cursor]),score=score,pitch_class_note_cell_weights=weights,
                         occurrence_refs=refs,unknown_overlapping_refs=partial,candidates=labels,status='no_known_pitched_evidence' if not labels else 'partial_known_pitch_scored_alternatives' if partial else 'conditional_scored_alternatives_not_adjudicated_chord'))
        cursor=begin
    return dict(result,status='SCORED_NOT_MUSICAL_TRUTH',minimal_cells=cells,optimal_score=best[-1],optimal_boundary_path_count=str(path_count[-1]),
                path_count_scope='boundary_paths_NOT_full_chord_label_assignments',mandatory_boundary_indices=mandatory,all_optimal_path_cell_consensus=consensus,
                optimal_predecessors=predecessors,canonical_display_path=list(reversed(path)),canonical_path_rule='minimum_predecessor_for_serialization_only_not_preferred_music',
                unknown_regions=[dict(start_q=c['start_q'],end_q=c['end_q'],status=c['status']) for c in cells if c['status']!='known_written_pitch_evidence'])


def validate(upper):
    if upper.get("schema") != "musical-context-relations/2" or type(upper.get("tier")) is not int or upper.get("tier") != 2:
        raise ValueError("Unsupported T2 interface")
    allowed = {"tier", "schema", "input", "theory", "coattacks", "realization_order", "source_quality", "lower_scope", "ensemble_coattacks", "nominal_written_spans", "tonal_evidence", "source_keys", "measure_geometry", "temporal_tonal_evidence",'written_ties'}
    if set(upper) - allowed:
        raise ValueError("Undeclared upper payload")
    coverage(upper["source_quality"])
    if upper["lower_scope"] not in ("base_pitch_and_metric_onset_duration_only","base_pitch_metric_time_and_source_key_declarations","written_context_facts_geometry_and_optional_source_keys",'written_context_geometry_keys_and_tie_notation'): raise ValueError("Unsupported lower scope")
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
    ties_owned=upper['lower_scope']=='written_context_geometry_keys_and_tie_notation'
    geometry_owned=ties_owned or upper["lower_scope"]=="written_context_facts_geometry_and_optional_source_keys"
    if geometry_owned:
        geometry_relation(parameters=upper["measure_geometry"])
        inventory=geometry_inventory(upper["measure_geometry"])
        inventory_by_part={r["part_id"]:r for r in inventory}
        if len(inventory)!=upper["source_quality"]["tracks"]: raise ValueError("Geometry track coverage mismatch")
        for group in upper["coattacks"]:
            if not 1<=group["bar"]<=inventory_by_part[group["part_id"]]["measure_count"]: raise ValueError("Note outside owned measure membership")
            frame=upper["measure_geometry"]["frames"][group["bar"]-1]
            start=F(frame["start_q"]);end=start+F(frame["duration_q"]);onset=F(group["onset_q"])
            if (not start<=onset<=end or (onset==end and any(F(m["duration_q"])>0 for m in group["members"]))) and not group["timing_uncertain"]: raise ValueError("Note start outside actual source measure")
    elif upper["measure_geometry"] is not None: raise ValueError("Geometry outside declared scope")
    model=materialized_source_keys(upper)
    if upper["lower_scope"]=="base_pitch_metric_time_and_source_key_declarations" or (geometry_owned and model is not None):
        facts=restore_source_keys(model);facts["source_coverage"]=upper["source_quality"]
        if not same(source_key_relations(facts),model): raise ValueError("Source declaration contexts conflict with shared signature relations")
        if geometry_owned:
            for occurrence in model["occurrences"]:
                if occurrence["onset_q"]!=upper["measure_geometry"]["frames"][occurrence["bar"]-1]["start_q"]: raise ValueError("Declaration clock conflicts with owned geometry")
    elif upper["source_keys"] is not None: raise ValueError("Source keys outside declared lower scope")
    if not same(temporal_tonal_evidence(upper["coattacks"],upper["measure_geometry"]),upper["temporal_tonal_evidence"]): raise ValueError("Temporal evidence conflicts with shared pitch/duration/frame relationships")
    if ties_owned:
        model=upper['written_ties'];notation=restore_written_ties(model)
        if not same(lift_written_ties(notation,upper),model):raise ValueError('Written tie graph conflicts with SAME source relations')
    elif 'written_ties' in upper:raise ValueError('Tie notation outside declared T1 scope')
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
        result.update(schema="normalized-written-and-declared-keys/2", **restore_source_keys(materialized_source_keys(upper)))
    if upper["measure_geometry"] is not None:
        result.update(schema="normalized-written-context-facts/3", measure_geometry=geometry_relation(parameters=upper["measure_geometry"])["source"],source_key_inventory=geometry_inventory(upper["measure_geometry"]))
        if upper["source_keys"] is None: result["source_key_declarations"]=None
    if upper['lower_scope']=='written_context_geometry_keys_and_tie_notation':
        result.update(schema='normalized-written-tie-context/4',tie_notation=restore_written_ties(upper['written_ties']))
    return result


def _chord_coordinates(pitch,bass,candidates,status):
    """Same pitch/root/register equation for start, overlap and inferred spans."""
    coordinates=[]
    if pitch is None:return coordinates
    for candidate in candidates:
        root=relation(pitch=bass,interval=candidate['bass_interval_pc'])['anchor']
        distance=F(relation(anchor=root,pitch=pitch)['interval'])
        coordinates.append(dict(root_pc=candidate['root_pc'],kind=candidate['kind'],root_register_reference=root,
                                unwrapped_semitones=str(distance),semitones_mod12=str(distance%12),relative_octaves=int(distance//12),
                                chord_member=distance%12 in candidate['formula'],reference_is_not_an_added_note=True,status=status))
    return coordinates


def note_context(upper, ident):
    """On-demand conditional coordinates, not a copied note stream per context."""
    validate(upper)
    for group in upper["coattacks"]:
        for member in group["members"]:
            if member["id"] != ident:
                continue
            pitch = member_pitch(group, member)
            coordinates = _chord_coordinates(pitch,group['bass_register_anchor'],group['interpretation']['chord_candidates'],'conditional_on_candidate_not_a_note_function')
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
    coordinates = _chord_coordinates(pitch,min(map(F,pitches)) if pitches else None,evidence['interpretation']['chord_candidates'],'conditional_on_nominal_overlap_candidate_not_note_function')
    return dict(occurrence_ref=ident, span_ref=span["id"], at_q=at_q,
                context_scope="ensemble" if ensemble_scope else "part", coordinates=coordinates,
                interval_of_note_base_key=None, interval_of_note_current_chord_mode=None,
                interpretation=evidence["interpretation"])


def harmonic_note_context(upper,ident,evidence,begin,stop):
    """One explicitly selected optimal-edge hypothesis, never hidden path choice."""
    request=evidence.get('request',{})
    expected=harmonic_span_evidence(upper,**request)
    if not same(expected,evidence):raise ValueError('Stale harmonic refinement contradicts current relationships')
    if evidence['status']!='SCORED_NOT_MUSICAL_TRUTH':raise ValueError('No scored harmonic hypothesis')
    n=len(evidence['partition_points_q'])
    if any(type(v) is not int for v in (begin,stop)) or not 0<=begin<stop<n:raise ValueError('Typed ordered edge indices required')
    reachable={n-1};pending=[n-1]
    while pending:
        j=pending.pop()
        for i in evidence['optimal_predecessors'][j]:
            if i not in reachable:reachable.add(i);pending.append(i)
    if stop not in reachable or begin not in evidence['optimal_predecessors'][stop]:raise ValueError('Edge is not on any optimal boundary path')
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']}
    group,member=index[ident];pitch=member_pitch(group,member)
    a,b=map(F,(evidence['partition_points_q'][begin],evidence['partition_points_q'][stop]))
    note_start=F(group['onset_q']);note_end=note_start+F(member['duration_q'])
    refs=list(dict.fromkeys(ref for c in evidence['minimal_cells'][begin:stop] for key in ('occurrence_refs','unknown_overlapping_refs') for ref in c[key]))
    if ident not in refs or max(a,note_start)>=min(b,note_end):raise ValueError('Note outside requested harmonic edge')
    weights=[0]*12
    for cell in evidence['minimal_cells'][begin:stop]:
        for ref in cell['occurrence_refs']:
            p=member_pitch(*index[ref])
            if p is not None and F(p).denominator==1:weights[int(F(p)%12)]+=1
    scores=harmonic_template_scores(weights) if any(weights) else [];best=max((r['score'] for r in scores),default=0)
    candidates=[r for r in scores if r['score']==best]
    pitches=[F(p) for ref in refs if (p:=member_pitch(*index[ref])) is not None]
    bass=min(pitches) if pitches else None
    for candidate in candidates:candidate['bass_interval_pc']=str((bass-candidate['root_pc'])%12) if bass is not None else None
    return dict(occurrence_ref=ident,edge_ref=[begin,stop],context_start_q=str(max(a,note_start)),context_end_q=str(min(b,note_end)),
                evidence_status='partial_known_pitch_evidence' if any(F(o['start_q'])<b and F(o['end_q'])>a for o in evidence['unknown_pitch_overlays']) else 'known_written_pitch_evidence',
                coordinates=_chord_coordinates(pitch,bass,candidates,'conditional_on_scored_span_not_adjudicated_chord_or_function'),
                reference_register_scope='lowest_written_pitch_anywhere_in_edge_not_simultaneous_bass',
                edge_selection='explicit_one_of_retained_optimal_hypotheses',established_key=None,established_mode=None)


def note_motion_evidence(upper,occurrence_refs):
    """Measured three-occurrence shape; NEVER identifies passing/neighbor intent."""
    validate(upper)
    if type(occurrence_refs) is not list or len(occurrence_refs)!=3 or len(set(occurrence_refs))!=3:raise ValueError('Three distinct owned occurrences required')
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']}
    rows=[index[i] for i in occurrence_refs];parts={g['part_id'] for g,m in rows};voices={m['voice'] for g,m in rows};reasons=[]
    if len(parts)!=1 or len(voices)!=1:reasons.append('different_source_part_or_voice')
    else:
        # Serialization order is not source musical order: the retained
        # extractor appends grace occurrences after regular events. Original
        # source addresses remain owned and are the only sequence authority.
        sequence=sorted((i for i in upper['realization_order'] if index[i][0]['part_id']==rows[0][0]['part_id'] and index[i][1]['voice']==rows[0][1]['voice']),
                        key=lambda i:(index[i][1]['bar'],index[i][1]['beat'],index[i][1]['note']))
        position=sequence.index(occurrence_refs[0])
        if sequence[position:position+3]!=occurrence_refs:reasons.append('not_consecutive_owned_occurrences')
        for g,m in rows:
            if sum(index[i][0]['onset_q']==g['onset_q'] for i in sequence)!=1:reasons.append('ambiguous_same_voice_simultaneity');break
    pitches=[member_pitch(g,m) for g,m in rows];starts=[F(g['onset_q']) for g,m in rows];durations=[F(m['duration_q']) for g,m in rows]
    if any(g['timing_uncertain'] for g,m in rows):reasons.append('source_timing_uncertain')
    if any(d==0 for d in durations):reasons.append('zero_duration_or_grace_occurrence')
    if any(p is None for p in pitches):reasons.append('unknown_pitch_occurrence')
    if len(parts)==1 and len(voices)==1:
        left=min(starts);right=max(a+d for a,d in zip(starts,durations))
        if any(i not in occurrence_refs and F(index[i][0]['onset_q'])<right and F(index[i][0]['onset_q'])+F(index[i][1]['duration_q'])>left for i in sequence):reasons.append('ambiguous_same_voice_overlap')
    gaps=[starts[i+1]-starts[i]-durations[i] for i in (0,1)]
    if any(gap!=0 for gap in gaps):reasons.append('noncontiguous_written_intervals')
    motion=None
    if all(p is not None for p in pitches):
        approach=F(relation(anchor=pitches[0],pitch=pitches[1])['interval']);departure=F(relation(anchor=pitches[1],pitch=pitches[2])['interval'])
        shape='strictly_monotonic' if approach*departure>0 else 'departure_and_return' if approach!=0 and F(pitches[0])==F(pitches[2]) else 'contains_repetition' if approach==0 or departure==0 else 'direction_change_without_register_return'
        motion=dict(approach_semitones=str(approach),departure_semitones=str(departure),register_return=F(pitches[0])==F(pitches[2]),shape=shape,diatonic_step=None)
    return dict(occurrence_refs=occurrence_refs,source_part_id=next(iter(parts)) if len(parts)==1 else None,source_voice=next(iter(voices)) if len(voices)==1 else None,
                clocks=[dict(occurrence_ref=i,onset_q=str(a),duration_q=str(d)) for i,a,d in zip(occurrence_refs,starts,durations)],
                gaps_q=list(map(str,gaps)),motion=motion,eligibility='eligible_owned_written_sequence' if not reasons else 'refused_unique_melodic_interpretation',refusal_reasons=list(dict.fromkeys(reasons)),
                passing_tone=None,neighbor_tone=None,attack_and_tie_status='outside_owned_T1_scope',claim='Measured shape and continuity only; even large leaps may be monotonic')


def harmonic_membership_evidence(upper,evidence,queries):
    """At most three memberships, jointly feasible on ONE optimal path/labels.

    State is a bounded tuple, not a general-purpose new inference engine.
    An edge uses one label for every queried note/time it covers.
    """
    if type(queries) is not list or not 1<=len(queries)<=3:raise ValueError('One to three explicit occurrence/time queries required')
    expected=harmonic_span_evidence(upper,**evidence.get('request',{}))
    if not same(evidence,expected) or evidence['status']!='SCORED_NOT_MUSICAL_TRUTH':raise ValueError('Current scored harmonic relationships required')
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']};points=list(map(F,evidence['partition_points_q']));query_values=[]
    for row in queries:
        if type(row) is not dict or set(row)!={'occurrence_ref','at_q'}:raise ValueError('Declared occurrence and clock only')
        group,member=index[row['occurrence_ref']];at=fraction(row['at_q']);start=F(group['onset_q']);end=start+F(member['duration_q'])
        if not start<=at<end or not points[0]<=at<points[-1]:raise ValueError('Query outside half-open written note/request')
        if evidence['request']['part_id'] is not None and group['part_id']!=evidence['request']['part_id']:raise ValueError('Query outside harmonic part scope')
        query_values.append((at,member_pitch(group,member)))
    # Prefix note-cell evidence derived from existing occurrence relationships.
    prefix=[[0]*12]
    for cell in evidence['minimal_cells']:
        weights=[0]*12
        for ref in cell['occurrence_refs']:
            p=member_pitch(*index[ref])
            if p is not None and F(p).denominator==1:weights[int(F(p)%12)]+=1
        prefix.append([a+b for a,b in zip(prefix[-1],weights)])
    reachable={len(points)-1};pending=list(reachable)
    while pending:
        j=pending.pop()
        for i in evidence['optimal_predecessors'][j]:
            if i not in reachable:reachable.add(i);pending.append(i)
    empty=tuple('not_visited' for _ in queries);states=[{} for _ in points];states[0][empty]=None
    for stop in range(1,len(points)):
        if stop not in reachable:continue
        for begin in evidence['optimal_predecessors'][stop]:
            weights=[b-a for a,b in zip(prefix[begin],prefix[stop])]
            scores=harmonic_template_scores(weights) if any(weights) else [];best=max((r['score'] for r in scores),default=0)
            labels=[r for r in scores if r['score']==best] or [None]
            covered=[k for k,(at,pitch) in enumerate(query_values) if points[begin]<=at<points[stop]]
            for label in labels:
                updates={}
                for k in covered:
                    pitch=query_values[k][1]
                    updates[k]='unknown' if pitch is None or F(pitch).denominator!=1 or label is None else 'chord_member' if F(relation(anchor=label['root_pc'],pitch=pitch)['interval'])%12 in label['formula'] else 'nonmember'
                for previous in states[begin]:
                    current=tuple(updates.get(k,value) for k,value in enumerate(previous))
                    if current not in states[stop]:states[stop][current]=(begin,previous,None if label is None else dict(root_pc=label['root_pc'],kind=label['kind'],formula=label['formula']))
    alternatives=[]
    for vector in sorted(states[-1]):
        if 'not_visited' in vector:raise ValueError('Incomplete membership coverage')
        edges=[];cursor=len(points)-1;state=vector
        while cursor:
            begin,previous,label=states[cursor][state]
            partial=any(F(o['start_q'])<points[cursor] and F(o['end_q'])>points[begin] for o in evidence['unknown_pitch_overlays'])
            edges.append(dict(begin=begin,stop=cursor,label=label,supporting_edge_has_partial_known_pitch_evidence=partial));cursor=begin;state=previous
        witness=list(reversed(edges))
        supporting=[next(e['supporting_edge_has_partial_known_pitch_evidence'] for e in witness if points[e['begin']]<=at<points[e['stop']]) for at,pitch in query_values]
        alternatives.append(dict(memberships=list(vector),one_valid_path_and_label_witness=witness,witness_supporting_edge_has_partial_evidence=supporting))
    partial=[any(F(o['start_q'])<=at<F(o['end_q']) for o in evidence['unknown_pitch_overlays']) for at,pitch in query_values]
    domains=['unknown_pitch' if pitch is None else 'outside_supported_12_pitch_class_domain' if F(pitch).denominator!=1 else 'integer_pitch_class' for at,pitch in query_values]
    return dict(queries=deepcopy(queries),query_pitch_domain=domains,query_has_partial_known_pitch_evidence=partial,feasible_membership_vectors=alternatives,
                dependence='Jointly feasible under existing harmonic objective; not independent unions or probabilities',
                established_key=None,established_mode=None,passing_tone=None,neighbor_tone=None,attack_and_tie_status='outside_owned_T1_scope')


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
    return _candidate_note_context(upper,ident,group,member,pitch,scope['id'],candidate,at_q,ensemble_scope)


def _candidate_note_context(upper,ident,group,member,pitch,scope_id,candidate,at_q,ensemble_scope):
    """One note/tonic/chord coordinate calculation for global AND timed evidence."""
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
    return dict(occurrence_ref=ident, tonal_scope_ref=scope_id, candidate_ref=candidate['id'], harmonic_context_ref=harmonic_context,
                interval_of_note_base_key_candidate=coordinate, interval_of_note_current_chord_mode=None,
                chord_root_coordinates=chords, established_key=None, established_mode=None)


def temporal_note_context(upper,ident,candidate_id,ensemble_scope=True):
    """Written-onset measure candidate; not a claim about sustained-note function."""
    validate(upper)
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']}
    group,member=index[ident]
    evidence=upper['temporal_tonal_evidence']
    if evidence is None:raise ValueError('No owned source measure geometry')
    found=[(s,r,c) for s in evidence['scopes'] for r in s['measures'] for c in r['candidates'] if c['id']==candidate_id]
    if len(found)!=1:raise ValueError('Exact timed candidate ID required')
    scope,record,candidate=found[0]
    if record['frame_ref']!=f"measure:{group['bar']}" or (scope['id']!='song-pooled' and scope['id']!=f"part:{group['part_id']}"):raise ValueError('Note outside timed candidate scope')
    result=_candidate_note_context(upper,ident,group,member,member_pitch(group,member),scope['id'],candidate,group['onset_q'],ensemble_scope)
    result.update(frame_ref=record['frame_ref'],candidate_evidence_status=record['status'],context_time='written_onset_only_not_sounding_sustain')
    return result


def declared_key_context(upper, part_id, at_q):
    """Compare source declarations to evidence ONLY conditional on pitch frame.

    A matching candidate coordinate is not inferred agreement or tonal truth.
    """
    validate(upper); at=fraction(at_q)
    if type(part_id) is not int or part_id<0: raise ValueError("Exact nonnegative part ID required")
    model=materialized_source_keys(upper)
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
    changed["temporal_tonal_evidence"] = temporal_tonal_evidence(changed["coattacks"],changed["measure_geometry"])
    validate(changed)
    return changed


def written_tie_edges(ctx,true_ids):
    """Accepted written-lane eligibility, shared by legacy and musical contexts."""
    lanes=defaultdict(lambda:defaultdict(list));links=[];unresolved=[]
    for ident,row in ctx.items():
        if row["duration"]<=0:
            if ident in true_ids:unresolved.append(dict(destination=ident,reason="zero_metric_duration"))
        elif row["lane"] is None:
            if ident in true_ids:unresolved.append(dict(destination=ident,reason="invalid_string_lane"))
        else:lanes[row["lane"]][row["onset"]].append(row)
    for groups in lanes.values():
        previous=None
        for q,group in sorted(groups.items()):
            if len(group)!=1:
                unresolved.extend(dict(destination=r["id"],reason="ambiguous_lane_onset") for r in group if r["id"] in true_ids)
                previous=None;continue
            row=group[0]
            if row["id"] in true_ids:
                reason=("no_predecessor" if previous is None else
                        "noncontiguous" if previous["onset"]+previous["duration"]!=q else
                        "unmapped_position" if previous["kind"]!="pitched_position" or row["kind"]!="pitched_position" or previous["position"] is None or row["position"] is None else
                        "invalid_written_position" if not previous["valid_position"] or not row["valid_position"] else
                        "dead_transition" if previous["dead"]!=row["dead"] else
                        "different_written_position" if previous["position"]!=row["position"] else None)
                if reason:unresolved.append(dict(destination=row["id"],reason=reason))
                else:links.append(dict(origin=previous["id"],destination=row["id"],kind="written_dead_tie" if row["dead"] else "written_pitched_tie"))
            previous=row
    links=sorted(links,key=lambda r:r["destination"]);unresolved=sorted(unresolved,key=lambda r:r["destination"])
    if {x["destination"] for x in links+unresolved}!=set(true_ids):raise ValueError("Tie ownership incomplete")
    return links,unresolved


def written_tie_context(notation,upper):
    """Minimum exact source declarations -> accepted written-lane predicate.

    Position is tuning+capo+fret, never a claimed acoustic frequency. No
    second onset/duration/base-pitch stream is stored in notation.
    """
    if type(notation) is not dict or set(notation)!={'parts','occurrences'}:raise ValueError('Exact tie notation owners required')
    settings={}
    for row in notation['parts']:
        if type(row) is not dict or set(row)!={'part_id','fields'} or type(row['part_id']) is not int or row['part_id'] in settings or type(row['fields']) is not dict or set(row['fields'])-{'instrumentId','tuning','capo'}:raise ValueError('Invalid tie settings')
        values=row['fields']
        for key in ('instrumentId','capo'):
            if values.get(key) is not None:
                if type(values[key]) not in (int,float):raise ValueError('Unsupported numeric setting')
                F(str(values[key]))
        tuning=values.get('tuning')
        if tuning is not None and (type(tuning) is not list or any(type(p) not in (int,float) for p in tuning)):raise ValueError('Unsupported source tuning')
        if tuning is not None:
            for pitch in tuning:F(str(pitch))
        settings[row['part_id']]=values
    if set(settings)!=set(range(upper['source_quality']['tracks'])):raise ValueError('Tie settings part coverage mismatch')
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']};ctx={};true=set()
    for row in notation['occurrences']:
        if type(row) is not dict or set(row)!={'occurrence_ref','fields'} or row['occurrence_ref'] not in index or row['occurrence_ref'] in ctx or type(row['fields']) is not dict or set(row['fields'])-{'string','fret','dead','tie'}:raise ValueError('Invalid tie occurrence ownership')
        ident=row['occurrence_ref'];values=row['fields'];group,member=index[ident];part=settings[group['part_id']]
        for key in ('string','fret'):
            if values.get(key) is not None:
                if type(values[key]) not in (int,float):raise ValueError('Unsupported source position')
                F(str(values[key]))
        if values.get('dead') is not None and type(values['dead']) is not bool:raise ValueError('Unsupported dead declaration')
        if values.get('tie') is not None and type(values['tie']) not in (bool,int,float,str):raise ValueError('Unsupported tie scalar')
        if type(values.get('tie')) is float:F(str(values['tie']))
        string=values.get('string');fret=values.get('fret');tuning=part.get('tuning');position=None
        lane=(group['part_id'],member['voice'],string) if type(string) is int and string>=0 else None
        if part.get('instrumentId')!=1024 and type(string) is int and tuning is not None and 0<=string<len(tuning) and type(fret) in (int,float):
            position=F(str(tuning[string]))+F(str(part.get('capo') or 0))+F(str(fret))
        pitch=member_pitch(group,member)
        if values.get('dead') is True and pitch is not None:raise ValueError('Dead notation conflicts with owned unknown base pitch')
        if values.get('dead') is not True and position is not None and pitch is not None and position!=F(pitch):raise ValueError('Physical position conflicts with shared pitch relation')
        ctx[ident]=dict(id=ident,lane=lane,onset=F(group['onset_q']),duration=F(member['duration_q']),position=position,kind='pitched_position' if position is not None else 'unmapped_position',valid_position=type(fret) in (int,float) and fret>=0,dead=values.get('dead') is True)
        if values.get('tie') is True:true.add(ident)
    if set(ctx)!=set(index):raise ValueError('Tie notation note coverage mismatch')
    return ctx,true


def lift_written_ties(notation,upper):
    ctx,true=written_tie_context(notation,upper);links,unresolved=written_tie_edges(ctx,true)
    # Exact explicit true declarations are represented by relationship ownership;
    # all missing/null/false/other scalar choices remain exact physical witnesses.
    physical=deepcopy(notation)
    for row in physical['occurrences']:
        if row['occurrence_ref'] in true:row['fields'].pop('tie')
    return dict(schema='written-tie-context/1',physical_choices=physical,links=links,unresolved=unresolved,
                semantics='Explicit written continuation only; no acoustic sustain or verified attack claim')


def restore_written_ties(model):
    if type(model) is not dict or set(model)!={'schema','physical_choices','links','unresolved','semantics'} or model['schema']!='written-tie-context/1' or model['semantics']!='Explicit written continuation only; no acoustic sustain or verified attack claim':raise ValueError('Unsupported written tie model')
    notation=deepcopy(model['physical_choices']);rows={r['occurrence_ref']:r for r in notation['occurrences']};seen=set()
    for link in model['links']+model['unresolved']:
        ident=link['destination']
        if ident not in rows or ident in seen or 'tie' in rows[ident]['fields']:raise ValueError('Duplicate/invalid tie declaration ownership')
        rows[ident]['fields']['tie']=True;seen.add(ident)
    return notation


def written_tie_chains(upper):
    """References and derived nominal endpoints; original occurrences preserved."""
    validate(upper)
    if 'written_ties' not in upper:raise ValueError('Tie declarations outside owned scope')
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']};links=upper['written_ties']['links']
    next_note={link['origin']:link['destination'] for link in links};destinations={link['destination'] for link in links};unresolved={r['destination'] for r in upper['written_ties']['unresolved']};chains=[]
    for origin in next_note:
        if origin in destinations:continue
        refs=[origin]
        while refs[-1] in next_note:refs.append(next_note[refs[-1]])
        first,_=index[origin];last,member=index[refs[-1]];a=F(first['onset_q']);b=F(last['onset_q'])+F(member['duration_q'])
        uncertain=any(index[i][0]['timing_uncertain'] for i in refs)
        chains.append(dict(origin_ref=origin,occurrence_refs=refs,onset_q=str(a),written_end_q=str(b),nominal_span_q=str(b-a),origin_has_unresolved_incoming_tie=origin in unresolved,
                           source_timing_uncertain=uncertain,context_eligibility='quarantined_source_timing_uncertain' if uncertain else 'eligible_declared_nominal_continuity',
                           kind=next(link['kind'] for link in links if link['origin']==origin)))
    return dict(chains=chains,unresolved=deepcopy(upper['written_ties']['unresolved']),semantics='Declared nominal written continuity; not acoustic sustain, not new attacks')


def tied_harmonic_context(upper,evidence,origin_ref,at_qs):
    """Declared continuity -> ORIGINAL constituents -> SAME joint memberships."""
    if type(at_qs) is not list or not 1<=len(at_qs)<=3:raise ValueError('One to three explicit clocks required')
    clocks=list(map(fraction,at_qs));chains=written_tie_chains(upper)['chains']
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']}
    if origin_ref not in index:raise ValueError('Owned origin occurrence required')
    chain=next((c for c in chains if c['origin_ref']==origin_ref),None)
    if chain is None:
        if any(origin_ref in c['occurrence_refs'] for c in chains):raise ValueError('Use declared chain origin, not a later constituent')
        unresolved=next((r for r in upper['written_ties']['unresolved'] if r['destination']==origin_ref),None)
        if unresolved is not None:return dict(status='UNRESOLVED_DECLARATION_WITHOUT_RESOLVED_CHAIN',origin_ref=origin_ref,requested_clocks_q=deepcopy(at_qs),unresolved_declaration=deepcopy(unresolved),membership=None,claim='Declared continuation is unresolved; no link or acoustic attack inferred')
        return dict(status='NO_DECLARED_CHAIN',origin_ref=origin_ref,requested_clocks_q=deepcopy(at_qs),membership=None,claim='No declared continuity does not establish an acoustic attack')
    if any(not F(chain['onset_q'])<=at<F(chain['written_end_q']) for at in clocks):raise ValueError('Clock outside half-open declared chain')
    group,_=index[origin_ref];request=evidence.get('request',{})
    if request.get('part_id') not in (None,group['part_id']) or F(request['start_q'])>F(chain['onset_q']) or F(request['end_q'])<F(chain['written_end_q']):raise ValueError('Harmonic evidence must cover this whole chain/part')
    if not same(harmonic_span_evidence(upper,**request),evidence):raise ValueError('Stale harmonic evidence')
    queries=[]
    for at,clock in zip(clocks,at_qs):
        matches=[i for i in chain['occurrence_refs'] if F(index[i][0]['onset_q'])<=at<F(index[i][0]['onset_q'])+F(index[i][1]['duration_q'])]
        if len(matches)!=1:raise ValueError('Clock does not map to exactly one original constituent')
        queries.append(dict(occurrence_ref=matches[0],at_q=clock))
    reasons=[]
    if chain['source_timing_uncertain']:reasons.append('source_timing_uncertain')
    if chain['kind']=='written_dead_tie':reasons.append('unpitched_dead_notation')
    if chain['origin_has_unresolved_incoming_tie']:reasons.append('unresolved_incoming_continuity')
    if any(member_pitch(*index[i]) is None for i in chain['occurrence_refs']):reasons.append('unknown_written_pitch')
    result=dict(origin_ref=origin_ref,chain=deepcopy(chain),requested_clocks_q=deepcopy(at_qs),resolved_original_queries=queries,
                harmonic_request=deepcopy(request),harmonic_status=evidence['status'],quarantine_reasons=reasons,membership=None,
                claim='Conditional chord membership of declared written continuity; original occurrences retained, no acoustic attack/sustain/function claim')
    if reasons:return dict(result,status='QUARANTINED_CHAIN')
    if evidence['status']!='SCORED_NOT_MUSICAL_TRUTH':return dict(result,status='HARMONIC_ANALYSIS_NOT_RUN')
    return dict(result,status='CONDITIONAL_CONTINUITY_CONTEXT',membership=harmonic_membership_evidence(upper,evidence,queries))
