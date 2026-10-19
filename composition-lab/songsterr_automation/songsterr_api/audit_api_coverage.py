"""Exhaustive observed-field audit of the cached API, not an API specification.

Public output contains field names, counts and implementation dispositions only.
New fields default to retained_only + review_required; parent coverage never
silently grants coverage to descendants. No raw response values are exported.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from analyze_relationships import NOTE_FIELDS, BEAT_FIELDS

STATUSES = ('analyzed', 'retained_only', 'unsupported', 'not_applicable')
M = 'track.measures[]'
V = M+'.voices[]'
B = V+'.beats[]'
N = B+'.notes[]'


def registry():
    rules={}
    def add(paths,status,level,use,gap='',evidence=''):
        for path in paths:
            if path in rules:raise ValueError('Duplicate rule: '+path)
            rules[path]=dict(status=status,analysis_level=level,current_use=use,remaining_gap=gap,
                             code_evidence=evidence,review_required=False)
    def fields(base,names,*args,**kwargs):
        add([base+'.'+k for k in names.split()],*args,**kwargs)
    add(['metadata','track','track.measures',M,M+'.voices',V,V+'.beats',B,B+'.notes',N],
        'analyzed','structural_traversal','Traversed to preserve source occurrence and scope identity.',
        'Container traversal does not imply analysis of all its children.',evidence='analyze; occurrences')
    fields('metadata','songId revisionId artist title','analyzed','provenance_and_grouping',
           'Source identity, exact artist-label grouping and provisional title families.',
           'No automatic revision-history comparison or confirmed composition identity.',evidence='analyze; family')
    fields('metadata','aiGenerated isJunk','analyzed','catalog_cohort',
           'Separate cohorts without silently dropping entries.','Flags are not verified transcription-quality labels.',evidence='analyze')
    fields('metadata','artistId createdAt createdVia description fingerstyle hasChords hasPlayer hasTracks defaultTrack popularTrack popularTrackBass popularTrackDrum popularTrackGuitar popularTrackVocals isCollaborative latestRevisionId prevRevisionId lyrics',
           'retained_only','raw_capture','Available in cached metadata; not consumed by the relational analyzer.',
           'No timestamp/history, track-selection, lyric or declared-capability analysis.')
    fields('metadata','author author.isModerator author.name author.personId author.profileName',
           'retained_only','raw_capture','Contributor provenance retained privately.',
           'No contributor reliability model or provenance-weighted technique estimate.')
    fields('metadata','tracks tracks[] tracks[].difficulty tracks[].hash tracks[].instrument tracks[].instrumentId tracks[].isEmpty tracks[].isVocalTrack tracks[].name tracks[].tuning tracks[].tuning[] tracks[].views',
           'retained_only','raw_capture','Metadata track catalog retained; actual part payloads drive analysis.',
           'Catalog track-role/empty/vocal flags and difficulty are not integrated; views are not quality scores.')
    fields('metadata','tags tags[]','retained_only','raw_capture','Tags retained privately.','No semantic tag interpretation.')
    fields('metadata','audio audioV2 audioV2Generated audioV2Midi audioV4 audioV4Generated audioV4Midi audioV4Meta audioV4Meta.hasMixLayout audioV4Meta.hasQuickMix audios audios.current audios.current.hash audios.current.meta audios.current.meta.hasMixLayout audios.current.meta.hasQuickMix audios.v4 audios.v4.hash audios.v4.meta audios.v4.meta.hasMixLayout audios.v4.meta.hasQuickMix videos videos[] videos[].feature videos[].id videos[].status videos[].videoId',
           'retained_only','raw_capture','Playback references/metadata retained without fetching or alignment.',
           'No audio/video performance analysis, playback verification or score alignment.')
    fields('metadata','favoritesCount image isBlank isBlocked isNextRevisionPremoderated isOnModeration isPopular isPublished isRestricted moderationType restriction views',
           'not_applicable','catalog_or_service_state','Outside symbolic technique measurement; retained in raw captures.',
           'Access/publication/popularity state does not establish musical correctness.')
    fields('track','partId name','analyzed','occurrence_identity','Part identity and display name label source observations.',
           'Names are not validated musical roles.',evidence='occurrences; track_analysis')
    fields('track','instrumentId','analyzed','scope_filter','Programs24..39 define the guitar/bass aggregate scope.',
           'Instrument program is not an inferred role; metadata vocal flags are not integrated.',evidence='track_analysis')
    fields('track','tuning tuning[] capo','analyzed','written_pitch','Written base pitch from tuning/string/fret/capo.',
           'No bend-adjusted or harmonic sounding-pitch model.',evidence='pitch')
    fields('track','instrument title version songId revisionId voices','retained_only','raw_capture',
           'Retained in raw track; top-level metadata supplies song/revision identity.',
           'No cross-response revision consistency check or top-level voice-catalog interpretation.')
    fields('track','frets strings anacrusis key tuningFlat tuningShortDrone balance volume',
           'unsupported','raw_capture','Musically relevant source field is retained but not interpreted.',
           'No fret-limit/string-count validation, pickup/key/alternate tuning semantics or mix model.')
    fields('track','automations automations.tempo automations.tempo[] automations.tempo[].bpm automations.tempo[].linear automations.tempo[].measure automations.tempo[].position automations.tempo[].text automations.tempo[].type automations.tempo[].visible sounds sounds[] sounds[].instrumentId sounds[].label trackAutomations trackAutomations.trackSoundAutomations trackAutomations.trackSoundAutomations[] trackAutomations.trackSoundAutomations[].measure trackAutomations.trackSoundAutomations[].position trackAutomations.trackSoundAutomations[].soundId',
           'unsupported','hash_only','Included in selected-content duplicate hashes, not musical interpretation.',
           'No tempo-ramp/seconds mapping, sound-switch timeline or automated arrangement analysis.',evidence='analyze content digest')
    fields('track','newLyrics newLyrics[] newLyrics[].line newLyrics[].offset newLyrics[].text withLyrics',
           'retained_only','raw_capture','Lyric information retained privately.','No lyric-to-phrase alignment.')
    fields(M,'signature signature[]','analyzed','rational_meter','Exact bar spans and inherited meter drive rational onsets.',
           'Not a performed tempo or pickup/repeat expansion.',evidence='occurrences')
    fields(M,'marker marker.text','analyzed','partial_source_label','The whole marker value is stringified as a section label.',
           'Text is not normalized separately from object layout fields; labels are not verified form/phrase functions.',evidence='occurrences str(marker)')
    fields(M,'marker.width','not_applicable','layout','Layout width has no musical technique meaning.',
           'Current str(marker) can leak width into the raw section display label; it should be separated.')
    fields(M,'alternateEnding alternateEnding[] repeat repeatStart rest','unsupported','raw_capture',
           'Written flags retained but not expanded or reconciled.','No performed repeat order or whole-measure-rest interpretation.')
    fields(M,'doubleBarline index','retained_only','raw_capture','Retained notation metadata; array position supplies analysis bar identity.',
           'Double barlines are not used as phrase/section evidence; source index not cross-checked.')
    fields(V,'rest','unsupported','raw_capture','Whole-voice rest flag is retained.','Analyzer consumes beats and note-rest flags; it does not expand this flag.')
    fields(B,'duration duration[]','analyzed','rational_written_timing','Declared fraction sets exact written duration and onset advancement.',
           'Duration notation is not cross-validated against type/dots/tuplet; no seconds mapping.',evidence='occurrences')
    fields(B,'graceNote','analyzed','separate_occurrence_scope','Grace notes are retained separately and block certain HOPO transitions.',
           'No grace performance timing or grace-specific conditional corpus statistics.',evidence='occurrences; hopo')
    fields(N,'rest','analyzed','rest_filter','Explicit note-rest entries are omitted from note counts while beat duration advances.',
           'No separate rest-pattern statistics or higher-level rest-flag reconciliation.',evidence='occurrences')
    fields(N,'string fret tie','analyzed','written_note_relationships','String/fret/base pitch, tied-attack exclusion and contiguous HOPO tie chaining.',
           'No complete sustained-sonority or tied-gesture-duration analysis.',evidence='pitch; occurrences; hopo; track_analysis')
    for base,markers in [(N,NOTE_FIELDS),(B,BEAT_FIELDS)]:
        for marker in markers:
            level='presence_and_raw_value_summary' if base==N and marker in ('slide','harmonic','accentuated') else 'presence_and_conditionals'
            if marker=='bend':level='presence_and_partial_curve_values'
            gap='Presence/relationships do not establish performance mechanics or musical function.'
            if marker=='hp':gap='Origin-marker transition candidates only; not independently adjudicated technique truth.'
            if marker in ('vibrato','wideVibrato','leftHandVibrato'):gap='No measured physical oscillation rate/depth or source audio validation.'
            if marker=='tremoloBar':gap='Only presence and unresolved-pitch flag; curve values are not interpreted.'
            if marker in ('brushStroke','pickStroke','upStroke','tremolo','gradualVelocity'):gap='Marker presence is counted; detailed rate/direction/envelope mechanics are not interpreted.'
            add([base+'.'+marker],'analyzed',level,'Technique marker shares and conditional notation statistics.',gap,evidence='occurrences; summary; NOTE_FIELDS/BEAT_FIELDS')
    fields(N,'harmonicFret','analyzed','raw_value_summary','Histogram of explicitly supplied harmonic node/fret value.',
           'No physical harmonic-type or sounding-pitch interpretation.',evidence='summary marker_value_histograms')
    for base in (B,N):
        fields(base,'velocity','analyzed','written_dynamic_inheritance','Local histogram plus voice-local explicit/inherited written dynamics and marking provenance; note override does not alter voice state.',
               'No ghost attenuation, dynamic-envelope reconstruction, performed loudness or playback-repeat dynamics inference.',evidence='source_dynamics.dynamic_observations; summary')
    fields(N,'bend.points bend.points[] bend.points[].position bend.points[].tone','analyzed','partial_curve_values',
           'Exact initial/peak/final tone/25 and first-peak position/60 statistics.',
           'No complete curve similarity, precise-position override, per-point vibrato or performed bend-rate analysis.',evidence='summary')
    fields(N,'bend.tone bend.points[].precisePosition bend.points[].vibrato','unsupported','raw_capture',
           'Curve metadata retained without interpretation.','Declared tone vs curve consistency, precise timing and per-point vibrato are not modeled.')
    fields(B,'brushStroke.direction brushStroke.duration brushStroke.shift tremolo[] tempo tempo.bpm tempo.type rest',
           'unsupported','raw_capture','Field values retained beyond any parent marker presence.',
           'No brush mechanics, tremolo rate, beat-tempo or beat-rest reconciliation.')
    fields(N,'tremolo[]','unsupported','raw_capture','Tremolo value/rate retained; parent marker presence is counted.',
           'No picking-rate or rate-change analysis.')
    fields(B,'tremoloBar.points tremoloBar.points[] tremoloBar.points[].position tremoloBar.points[].tone tremoloBar.tone',
           'unsupported','raw_capture','Raw whammy curve retained; parent marker presence is counted.',
           'No whammy curve or sounding-pitch relationship analysis.')
    fields(B,'type dots dotted','retained_only','raw_capture','Redundant duration notation retained; duration fraction drives analysis.',
           'No type/dot-to-duration consistency check.')
    fields(B,'tuplet tupletStart tupletStop','unsupported','raw_capture','Tuplet annotations retained; their declared duration is used separately.',
           'No tuplet-group identity, grouping or accent-pattern analysis.')
    fields(B,'beamStart beamStop','not_applicable','engraving','Engraving beam flags are not technique measurements.',
           'They are not used as phrasing evidence.')
    fields(B,'text text.text','retained_only','raw_capture','Free text retained privately; not interpreted as technique instruction.',
           'No free-text instruction parser or trusted-label treatment.')
    fields(B,'text.width','not_applicable','layout','Text layout width is outside musical technique analysis.')
    # Current source_semantics.py implementation supersedes the original audit.
    def upgrade(paths,level,use,gap,evidence):
        for path in paths:
            rules[path].update(status='analyzed',analysis_level=level,current_use=use,remaining_gap=gap,code_evidence=evidence)
    upgrade(['metadata.tracks','metadata.tracks[]','metadata.tracks[].isVocalTrack','metadata.tracks[].isEmpty'],
            'catalog_scope_filter','Vocal/empty flags exclude tracks from guitar aggregation while retaining observations.',
            'Catalog flags are not inferred musical roles or verified accuracy.','analyze; track_analysis')
    upgrade(['track.songId','track.revisionId','track.partId'],'identity_validation','Track identities checked against metadata and filename part index.',
            'No automatic upstream revision-history comparison.','analyze')
    upgrade(['track.anacrusis'],'shared_pickup_layout','Flagged short first bar measured across tracks; shared rational bar layout.',
            'Ambiguous/full-length flagged bars are not shortened by guesswork.','source_semantics.layout')
    upgrade(['track.frets'],'physical_notation_check','Note frets checked against declared range.',
            'Range compliance is not certified hand playability.','track_analysis')
    upgrade([M+'.marker',M+'.marker.text'],'normalized_source_label','Marker text separated from layout width; section instances remain distinct.',
            'Not verified phrase/form functions.','source_semantics.marker_text')
    rules[M+'.marker.width']['remaining_gap']='Layout width is excluded from the normalized section label.'
    upgrade([M+'.repeat',M+'.repeatStart',M+'.alternateEnding',M+'.alternateEnding[]'],'bounded_playback_order',
            'Nested repeats and alternate endings produce a separate source-bar visit map.',
            'Ambiguous/unclosed repeats and expansion limits are reported; written occurrences are not duplicated.','source_semantics.playback_order')
    upgrade([M+'.rest',V+'.rest',B+'.rest'],'rest_spans_and_conflicts',
            'Explicit whole/voice/beat rests produce rational spans; contradictory notes are flagged.',
            'No artistic pause/phrase-end interpretation.','source_semantics.rests')
    upgrade([N+'.bend.tone'],'curve_consistency','Declared peak checked against point-curve maximum.',
            'Does not certify a physically performed bend.','source_semantics.curve')
    upgrade([N+'.bend.points[].precisePosition'],'exact_curve_fraction',
            'Observed percent encoding uses precisePosition/100 instead of coarse position/60 when present.',
            'Undocumented API encoding inferred from captured values; invalid/unsorted offsets flagged.','source_semantics.curve')
    upgrade([N+'.bend.points[].vibrato'],'point_vibrato_observation','Point-level vibrato flags retained and counted; affected pitch centers remain unresolved.',
            'Flag does not encode physical rate/depth.','source_semantics.curve; sustain_context')
    for base in [N,B]:
        upgrade([base+'.tremolo',base+'.tremolo[]'],'exact_notated_rate',
                'Fraction supplies rational picking period and attacks per quarter.',
                'Not actual performed picking precision.','source_semantics.mechanics')
    upgrade([B+'.brushStroke',B+'.brushStroke.direction',B+'.brushStroke.duration',B+'.brushStroke.shift'],
            'native_brush_values','Direction and native duration/shift distributions, linked to source occurrences.',
            'Duration/shift time units remain unverified; no guessed milliseconds or per-string attack offsets.','source_semantics.mechanics')
    upgrade([B+'.tremoloBar',B+'.tremoloBar.points',B+'.tremoloBar.points[]',B+'.tremoloBar.points[].position',B+'.tremoloBar.points[].tone',B+'.tremoloBar.tone'],
            'exact_notated_curve','Whammy point curves, excursions and notated pitch-center hypotheses use raw tone/50 semitones.',
            'Performed vibrato/physical trem-bar behavior not reconstructed.','source_semantics.curve; mechanics; sustain_context')
    tempo_paths=['track.automations','track.automations.tempo','track.automations.tempo[]']+['track.automations.tempo[].'+k for k in ('bpm','type','position','measure','linear')]+[B+'.tempo',B+'.tempo.bpm',B+'.tempo.type']
    upgrade(tempo_paths,'step_tempo_timeline','Tempo locations/BPM/beat unit yield exact step-tempo seconds; conflicts are flagged.',
            'Linear ramp convention remains unresolved; seconds abstain for such timelines. No linear ramps observed here.','source_semantics.timeline; seconds_between')
    sound_paths=['track.sounds','track.sounds[]','track.sounds[].instrumentId','track.sounds[].label','track.trackAutomations','track.trackAutomations.trackSoundAutomations','track.trackAutomations.trackSoundAutomations[]']+['track.trackAutomations.trackSoundAutomations[].'+k for k in ('measure','position','soundId')]
    upgrade(sound_paths,'sound_timeline','Sound IDs resolve programs/labels at source locations; technique contexts record attack program.',
            'Program identity is not musical role; no synthesized instrument-quality judgment.','source_semantics.timeline; analyze')
    for path in (N+'.bend',N+'.bend.points',N+'.bend.points[]',N+'.bend.points[].position',N+'.bend.points[].tone'):
        rules[path].update(analysis_level='exact_notated_curve',current_use='Curve summaries use correct tone/50 semitones and precise percent positions when present.',remaining_gap='Not performed sound, physical vibrato or inferred artistic intent.',code_evidence='summary; source_semantics.curve')
    return rules


def value_type(value):
    if value is None:return 'null'
    if isinstance(value,bool):return 'boolean'
    if isinstance(value,dict):return 'object'
    if isinstance(value,list):return 'array'
    if isinstance(value,str):return 'string'
    if isinstance(value,(int,float)):return 'number'
    raise TypeError(type(value))


def scan_documents(documents):
    """documents: iterable (scope, value, private song key, private track key).

    Scalar fields use parent-object counts as denominator. Array element paths
    use actual element slots; empty arrays count as present parent fields.
    """
    stats={};private=defaultdict(list);doc_counts=Counter()
    def walk(value,path,song,track,seen):
        s=stats.setdefault(path,dict(present=0,nonnull=0,truthy=0,types=Counter(),songs=set(),tracks=set()))
        s['present']+=1;s['nonnull']+=value is not None;s['truthy']+=bool(value)
        s['types'][value_type(value)]+=1;s['songs'].add(song)
        if track is not None:s['tracks'].add((song,track))
        seen.add(path)
        if isinstance(value,dict):
            for key,child in value.items():walk(child,path+'.'+key,song,track,seen)
        elif isinstance(value,list):
            for child in value:walk(child,path+'[]',song,track,seen)
    for scope,value,song,track in documents:
        doc_counts[scope]+=1;seen=set();walk(value,scope,song,track,seen)
        private[song].append(dict(scope=scope,track=track,observed_paths=sorted(seen)))
    rules=registry();rows=[]
    for path,s in sorted(stats.items()):
        if path.endswith('[]'):
            denominator=s['present'];denominator_kind='observed_array_element_slots'
        elif '.' in path:
            parent=path.rsplit('.',1)[0];denominator=stats[parent]['types']['object'];denominator_kind='parent_object_instances'
        else:denominator=doc_counts[path];denominator_kind='response_documents'
        rule=rules.get(path,dict(status='retained_only',analysis_level='unreviewed_field',
                                current_use='Captured raw field; no audited analysis mapping.',remaining_gap='New/unmapped field requires review.',
                                code_evidence='',review_required=True))
        rows.append(dict(path=path,present_count=s['present'],parent_denominator=denominator,
                         denominator_kind=denominator_kind,presence_percent=100*s['present']/denominator if denominator else None,
                         nonnull_count=s['nonnull'],truthy_value_count=s['truthy'],types=dict(s['types']),
                         entries_with_field=len(s['songs']),track_responses_with_field=len(s['tracks']),**rule))
    source=Path(__file__).with_name('analyze_relationships.py')
    return dict(schema='songsterr-api-field-coverage-v1',analyzer_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                semantics_sha256=hashlib.sha256(source.with_name('source_semantics.py').read_bytes()).hexdigest(),
                dynamics_sha256=hashlib.sha256(source.with_name('source_dynamics.py').read_bytes()).hexdigest(),
                entries=len(private),response_counts=dict(doc_counts),observed_paths=len(rows),
                status_counts=dict(Counter(r['status'] for r in rows)),review_required_paths=[r['path'] for r in rows if r['review_required']],
                declared_but_unobserved_paths=sorted(set(rules)-set(stats)),fields=rows,
                limitations=['Observed captured responses only, not an exhaustive upstream API specification',
                             'Presence counts include false/null/zero values and containers; they are not performed technique counts',
                             'Analyzed can be partial: inspect analysis_level and remaining_gap; raw storage and hashing are not functional analysis',
                             'Not applicable means outside this symbolic technique audit, not permanently useless',
                             'All source values and per-source identities remain private']),dict(schema='songsterr-api-private-field-coverage-v1',sources=dict(private))


def documents(root):
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or not (folder/'metadata.json').exists():continue
        yield 'metadata',json.loads((folder/'metadata.json').read_text(encoding='utf-8-sig')),folder.name,None
        for file in sorted(folder.glob('track-*.json')):
            yield 'track',json.loads(file.read_text(encoding='utf-8-sig')),folder.name,file.stem


def markdown(report):
    lines=['# Captured API field coverage','',f"Audited {report['entries']} entries, {report['response_counts'].get('track',0)} track responses and **{report['observed_paths']} distinct paths**.",'',
           'This is a coverage audit of `analyze_relationships.py`, not a statement that every analyzed field is fully interpreted. Container traversal, marker presence and raw value histograms are explicitly distinguished. Raw capture and hash-only use do not count as functional technique analysis.','',
           '| Disposition | Paths |','|---|---:|']
    for status in STATUSES:lines.append(f"| {status} | {report['status_counts'].get(status,0)} |")
    lines+=['',f"Unreviewed observed fields: {len(report['review_required_paths'])}. Analyzer SHA256: `{report['analyzer_sha256']}`.",'',
            '## What the gaps mean','',
            '- Implemented: normalized marker text, cross-response identity checks, vocal/empty scope flags, shared pickups, rest spans, bounded nested repeats/endings, step-tempo/sound timelines, precise bend and whammy curves, point-vibrato observations, tremolo fractions and brush native values.',
            '- Corrected: raw tone/25 is quarter-tone units, not semitones. Current semitone summaries use tone/50; prior v1 semitone labels were doubled. The GP conversion/audio was not changed by that labeling error.',
            '- Remaining: brush duration/shift units, performed vibrato rate/depth, harmonic sounding-pitch interpretation, physical playability, tuplets as musical groups and inferred phrase/function/roles. Linear-tempo ramps remain unresolved and cause seconds to abstain; none were observed in this capture.',
            '- Retained metadata and layout/service fields do not all need technique metrics. Contributor history, playback-reference alignment and catalog state remain separate from observed note technique.',
            '',
            'Field-presence numerators include false/null/zero values. For scalar/object fields the denominator is parent object instances; for `[]` paths it is observed element slots. Entry/track coverage is deduplicated by response identity. Empty arrays are present fields but have no observed child slots. Values, source identities and private annotations are not included.','',
            '## Complete observed matrix','', '| Field | Present / parent scope | Entries | Tracks | Status / level | Current use; remaining gap |', '|---|---:|---:|---:|---|---|']
    for r in report['fields']:
        text=(r['current_use']+' '+r['remaining_gap']).replace('|','/').replace('\n',' ')
        lines.append(f"| `{r['path']}` | {r['present_count']}/{r['parent_denominator']} | {r['entries_with_field']} | {r['track_responses_with_field']} | {r['status']} / {r['analysis_level']} | {text} |")
    lines+=['','## Limits','']+['- '+x for x in report['limitations']]
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('--json',type=Path,required=True);p.add_argument('--markdown',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--strict',action='store_true');a=p.parse_args()
    if 'local-artifacts' not in a.private.resolve().parts:p.error('Per-source coverage must remain in private local-artifacts')
    report,private=scan_documents(documents(a.corpus))
    a.json.write_text(json.dumps(report,indent=2),encoding='utf-8');a.markdown.write_text(markdown(report),encoding='utf-8');a.private.write_text(json.dumps(private,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('entries','response_counts','observed_paths','status_counts','review_required_paths')}))
    if a.strict and report['review_required_paths']:raise SystemExit(2)
