"""Time/evidence addresses for existing pattern outputs; no new detections."""
from fractions import Fraction as F


def connect_patterns(mapper,outputs):
    song=mapper.song;sid=song["song_id"];headers={h["bar"]:h for h in song["shared_layout"]}
    tracks={t["part_id"]:t for t in song["tracks"]}

    def save(kind,key,values,spans,members,source,scope):
        ident="pattern-view:"+key
        if ident in mapper.nodes:raise AssertionError("Duplicate pattern view")
        node=dict(id=ident,tier=3,kind=kind,scope=dict(song_id=sid,**scope),values=values,
            time=dict(basis="written_quarter_notes",spans=spans,status="disjoint_evidence_extents_not_continuous_sound"),
            origin=dict(document="pattern_occurrence_projection",pointer="/"+key),status="existing_mathematical_pattern_or_candidate_not_human_phrase_truth")
        mapper.nodes[ident]=node;mapper.tiers[3]["records"].append(node)
        mapper.links.append(dict(type="existing_pattern_output",from_id=ident,to_id=source))
        for occurrence in sorted(set(members)):
            mapper.links.append(dict(type="pattern_event_member",from_id=ident,to_id=mapper.event_ids[occurrence]))
        return ident

    extended=outputs["extended"]
    streams=extended["source_attack_streams"]["streams"]
    for i,record in enumerate(extended["source_fingerprint_windows"]):
        stream=streams[record["stream_index"]]
        for wi,window in enumerate(record["windows"]):
            start,length=window["start_event_index"],window["length"]
            events=stream["events"][start:start+length]
            left=min(F(e["q"]) for e in events)
            right=max(F(e["q"])+F(duration) for e in events for _,duration in e["notes"])
            save("source_attack_fingerprint_window",f"fingerprint/{i}/{wi}",window,
                [dict(start=str(left),end=str(right))],[m for e in events for m in e["members"]],
                f"r:extended/source_fingerprint_windows:/{i}/windows/{wi}",dict(part_id=record["part_id"],voice=record["voice"]))

    patterns=extended["pattern_hypotheses"]
    for ti,result in enumerate(patterns["phrases"]):
        track=tracks[result["part_id"]];phrases=result["analysis"]["phrases"]
        ids={p["start_measure"]:f"r:extended/pattern_hypotheses:/phrases/{ti}/analysis/phrases/{pi}" for pi,p in enumerate(phrases)}
        for pi,phrase in enumerate(phrases):
            ident=ids[phrase["start_measure"]]
            population=[r for r in track["rows"]+track["grace_rows"] if r["voice"]==0 and r["midi"] is not None and phrase["start_measure"]<=r["bar"]<=phrase["end_measure"]]
            minima={}
            for row in population:
                key=(row["bar"],row["beat"])
                minima[key]=min(minima.get(key,row["midi"]),row["midi"])
            for row in population:
                mapper.links.append(dict(type="primary_voice_comparison_population",from_id=ident,to_id=mapper.event_ids[row["occurrence"]]))
                if row["midi"]==minima[row["bar"],row["beat"]]:mapper.links.append(dict(type="lowest_pitch_outline_input",from_id=ident,to_id=mapper.event_ids[row["occurrence"]]))
            mapper.nodes[ident]["selection_contract"]="Legacy first-written-voice, lowest pitch per beat; equal-pitch minima retain all source witnesses. Rounded inputs are stored separately."
            if "develops_phrase_at" in phrase:
                predecessor=ids[phrase["develops_phrase_at"]]
                mapper.links.append(dict(type="develops_previous_phrase",from_id=ident,to_id=predecessor))
        # The existing transition histogram counts these exact adjacent pairs.
        summary=f"r:extended/pattern_hypotheses:/phrases/{ti}/analysis"
        for pi,(a,b) in enumerate(zip(phrases,phrases[1:])):
            ident=f"phrase-transition:{ti}:{pi}"
            node=dict(id=ident,tier=3,kind="existing_candidate_phrase_transition",scope=dict(song_id=sid,part_id=track["part_id"]),values=dict(histogram_key=a["relationship"]+" → "+b["relationship"]),time=None,origin=dict(document="phrase_transition_projection",pointer=f"/{ti}/{pi}"),status="existing_candidate_classification_transition_not_human_phrase_truth")
            mapper.nodes[ident]=node;mapper.tiers[3]["records"].append(node)
            mapper.links.append(dict(type="transition_histogram_unit",from_id=summary,to_id=ident))
            for endpoint,phrase in (("previous",a),("next",b)):mapper.links.append(dict(type="transition_"+endpoint,from_id=ident,to_id=ids[phrase["start_measure"]]))
    for mi,motif in enumerate(patterns["motifs"]):
        track=tracks[motif["part_id"]]
        for label,width in (("timed_repeats",1),("flexible_repeats",1),("two_bar_repeats",2)):
            for gi,bars in enumerate(motif[label]):
                spans=[];members=[]
                for bar in bars:
                    first,last=headers[bar],headers[bar+width-1]
                    spans.append(dict(start=first["start_q"],end=str(F(last["start_q"])+F(last["span_q"]))))
                    for current in range(bar,bar+width):
                        rows=[r for r in track["rows"]+track["grace_rows"] if r["bar"]==current and r["midi"] is not None]
                        voices=sorted({r["voice"] for r in rows})
                        if voices:members.extend(r["occurrence"] for r in rows if r["voice"]==voices[0])
                save("legacy_relative_motif_repeat_group",f"motif/{mi}/{label}/{gi}",dict(basis=label,bars=bars,width_bars=width,original_selection_limit=12),spans,members,
                    f"r:extended/pattern_hypotheses:/motifs/{mi}",dict(part_id=motif["part_id"]))

    for ti,result in enumerate(patterns["variant_windows"]["tracks"]):
        track=song["tracks"][ti]
        for wi,window in enumerate(result["candidate_variant_motifs"]):
            spans=[];members=[]
            for bar in window["bars"]:
                first,last=headers[bar],headers[bar+window["length_bars"]-1]
                spans.append(dict(start=first["start_q"],end=str(F(last["start_q"])+F(last["span_q"]))))
                members.extend(r["occurrence"] for r in track["rows"]+track["grace_rows"] if r["voice"]==0 and bar<=r["bar"]<bar+window["length_bars"])
            save("legacy_variant_window_candidate",f"variant/{ti}/{wi}",window,spans,members,
                f"r:extended/pattern_hypotheses:/variant_windows/tracks/{ti}/candidate_variant_motifs/{wi}",dict(part_id=track["part_id"]))

    for index,record in enumerate(patterns["source_section_content_identity"]):
        track=tracks[record["part_id"]]
        tails={chain["origin"]:F(chain["end_q"]) for chain in track["sustain_relationships"]["chains"]}
        grace_ids={r["occurrence"] for r in track["grace_rows"]};members=[]
        for row in track["rows"]+track["grace_rows"]:
            if row["voice"]!=0 or row["tie_destination"]:continue
            q=F(row["onset_q"]);end=q if row["occurrence"] in grace_ids else tails.get(row["occurrence"],q+F(row["duration_q"]))
            if F(record["start_q"])<=q<F(record["end_q"]) or q<F(record["start_q"])<end:members.append(row["occurrence"])
        ident=save("source_section_content_identity",f"content/{index}",dict(signature=record["signature"],source_section_start=record["section_start"],abstained=record["signature"] is None,abstention_detail="Existing helper returns None without a finer reason code" if record["signature"] is None else None),
            [dict(start=record["start_q"],end=record["end_q"])],members,
            f"r:extended/pattern_hypotheses:/source_section_content_identity/{index}",dict(part_id=track["part_id"]))

        ti=next(i for i,t in enumerate(song["tracks"]) if t["part_id"]==track["part_id"])
        for ci,chain in enumerate(track["sustain_relationships"]["chains"]):
            if chain["origin"] in members and F(chain["onset_q"])<F(record["start_q"])<F(chain["end_q"]):
                mapper.links.append(dict(type="cross_boundary_sustain_input",from_id=ident,to_id=f"r:core:/songs/0/tracks/{ti}/sustain_relationships/chains/{ci}"))
