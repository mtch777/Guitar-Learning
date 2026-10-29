"""Independent raw notation/context and complete source-lock accent oracle.

No local_accents imports. Source clock semantics are shared with the accepted
parser; dynamic state is independently scanned by check_local_dynamics.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import json,math,random
from source_fact_tier1 import project_documents
from source_tie_tier1 import extract_documents
from check_local_dynamics import inventory as dynamic_inventory

SCHEMA='source-local-accents/1'
POLICY='source_local_note_accent'
NOTE_EXPR=('hp','ghost','dead','tie','slide','bend','harmonic','harmonicFret','staccato','tremolo','vibrato','wideVibrato','leftHandVibrato','pickScrape','trill')
BEAT_EXPR=('brushStroke','arpeggio','downArpeggio','letRing','tremoloBar','fadeIn','tapping','gradualVelocity','sustainPedal')


def _encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def _duration(beat):
    d=beat.get('duration')
    return F(*d)*4 if type(d)is list and len(d)==2 and all(type(x)is int for x in d)and d[0]>=0 and d[1]>0 else None


def inventory(tier1):
    docs=project_documents(tier1);lower=extract_documents(docs)
    states={r['occurrence_ref']:r for r in dynamic_inventory(tier1)['states']}
    events={e['id']:e for e in lower['events']};frames={f['ordinal']:f for f in lower['measure_geometry']['frames']}
    warnings=lower['source_coverage']['layout_warnings']+lower['source_coverage']['timing_warnings'];rows=[]
    for name,part in sorted(docs.items()):
        if not name.startswith('track-'):continue
        for bar,measure in enumerate(part.get('measures',[]),1):
            for voice,v in enumerate(measure.get('voices',[])):
                position=F(0);prefix_known=True
                for beat,b in enumerate(v.get('beats',[])):
                    duration=_duration(b);beat_ref=f'{name}#/measures/{bar-1}/voices/{voice}/beats/{beat}'
                    for note,n in enumerate(b.get('notes',[])):
                        ref=f"event:{part['songId']}:{part['partId']}:{bar}:{voice}:{beat}:{note}";note_ref=beat_ref+f'/notes/{note}'
                        present='accentuated'in n;value=n.get('accentuated');known=not present or type(value)is int and value in(0,1,2)
                        notation={'kind':'absent'}if not present else dict(kind='explicit',value=deepcopy(value))
                        state=states.get(ref);frame=frames.get(bar);event=events.get(ref);reasons=[]
                        if n.get('rest'):reasons.append('SOURCE_REST')
                        if event is None:reasons.append('NO_NORMALIZED_SOURCE_EVENT')
                        if type(part.get('instrumentId'))is not int or not 0<=part['instrumentId']<128:reasons.append('NONPITCHED_OR_UNKNOWN_INSTRUMENT')
                        if event is not None and(event['pitch']is None or F(event['pitch']).denominator!=1):reasons.append('UNKNOWN_OR_FRACTIONAL_WRITTEN_PITCH')
                        if state is None or not state['known']:reasons.append('UNKNOWN_WRITTEN_DYNAMIC')
                        if not known:reasons.append('UNKNOWN_ACCENT_DECLARATION')
                        if b.get('graceNote')or duration is None or duration<=0:reasons.append('NONPOSITIVE_OR_UNKNOWN_REGULAR_DURATION')
                        if not prefix_known or duration is None:reasons.append('UNKNOWN_BAR_OFFSET')
                        if frame is None or F(frame['span_q'])!=F(frame['signature'][0])*4/F(frame['signature'][1]):reasons.append('NONNOMINAL_FRAME')
                        if frame is not None and not F(0)<=position<F(frame['span_q']):reasons.append('OUTSIDE_SOURCE_FRAME')
                        if frame is not None and duration is not None and position+duration>F(frame['span_q']):reasons.append('SOURCE_FRAME_CROSSING')
                        if any(w.get('bar')==bar and(w.get('part_id')is None or w['part_id']==part['partId'])for w in warnings):reasons.append('SOURCE_CLOCK_QUALIFICATION')
                        expression=[k for k in NOTE_EXPR if n.get(k)]+['beat:'+k for k in BEAT_EXPR if b.get(k)]
                        if expression:reasons.append('OTHER_EXECUTION_OR_ARTICULATION')
                        marking=state['marking']if state else None;meter=deepcopy(frame['signature'])if frame else None
                        rows.append(dict(occurrence_ref=ref,note_ref=note_ref,beat_ref=beat_ref,
                            part_id=part['partId'],voice=voice,bar=bar,beat=beat,note=note,state=notation,sound_level=(0 if not present else value)if known else None,
                            dynamic_marking=marking,dynamic_origin_ref=state['origin_fact_ref']if state else None,
                            source_meter=meter,position_q=str(position),duration_q=str(duration)if duration is not None else None,
                            context_key=None if reasons else[part['partId'],voice,marking,meter,str(position),str(duration)if duration is not None else None],
                            expression_fields=expression,reasons=sorted(set(reasons))))
                    if duration is None:prefix_known=False
                    elif not b.get('graceNote'):position+=duration
    return dict(schema=SCHEMA,occurrences=sorted(rows,key=lambda r:(r['part_id'],r['bar'],r['voice'],r['beat'],r['note'])))


def _level(notation):return 0 if notation['kind']=='absent'else notation['value']


class Oracle:
    def __init__(self,tier1):
        self.before=deepcopy(tier1);self.view=inventory(tier1);self.rows={r['occurrence_ref']:r for r in self.view['occurrences']};self.contexts=defaultdict(list)
        for r in self.view['occurrences']:
            if not r['reasons']:self.contexts[_encoded(r['context_key'])].append(r)

    def inventory(self):return deepcopy(self.view)

    def options(self,target_ref):
        if target_ref not in self.rows:raise ValueError('Original source occurrence required')
        target=self.rows[target_ref];peers=[]
        if not target['reasons']:peers=[r for r in self.contexts[_encoded(target['context_key'])]if r['beat_ref']!=target['beat_ref']]
        groups={}
        for donor in peers:groups.setdefault(_encoded(donor['state']),[]).append(donor)
        observed=[dict(state=deepcopy(ds[0]['state']),sound_level=_level(ds[0]['state']),donor_refs=sorted(d['occurrence_ref']for d in ds),changed=ds[0]['state']!=target['state'])for ds in sorted(groups.values(),key=lambda ds:(_level(ds[0]['state']),ds[0]['state']['kind']!='absent'))]
        pair=next(([a['occurrence_ref'],b['occurrence_ref']]for i,a in enumerate(peers)for b in peers[i+1:]if a['beat_ref']!=b['beat_ref']and _level(a['state'])!=_level(b['state'])),None)
        return dict(target_ref=target_ref,target=deepcopy(target),observed_options=observed,options=deepcopy(observed)if pair else [],witness_pair=pair,
            status='NO_SUPPORTED_ACCENT_CONTEXT'if target['reasons']else'SOURCE_SUPPORTED_LOCAL_ACCENT_CHOICES'if pair else'NO_INDEPENDENT_ACCENT_MULTI_CHOICE')

    choices=options

    def check_sample(self,target_ref,controls,chosen,decision):
        if type(decision)is not dict:raise ValueError('Typed decision required')
        if type(controls)is not dict or set(controls)!={'context_policy','accents','target_ref','seed'}or controls['context_policy']!=POLICY or controls['target_ref']!=target_ref or type(controls['seed'])is not int:
            raise ValueError('Exact local-accent controls required')
        strength=controls['accents']
        if type(strength)not in(int,float)or not math.isfinite(strength)or not 0<=strength<=100:raise ValueError('Accent release must be0..100')
        rng=random.Random(controls['seed']);released=rng.random()<strength/100;ev=self.options(target_ref)
        weighted=[o for o in ev['options']for _ in o['donor_refs']];expected=deepcopy(rng.choice(weighted))if released and weighted else None
        issues=[]
        if chosen!=expected:issues.append('Seeded source draw differs')
        if type(decision)is not dict or type(decision.get('released'))is not bool or type(decision.get('changed'))is not bool or decision['released']is not released or decision['changed']is not bool(expected and expected['changed']):issues.append('Release/change flags differ')
        if decision.get('chosen')!=expected:issues.append('Decision chosen evidence differs')
        return dict(status='PASS_INDEPENDENT_LOCAL_ACCENT_SAMPLE'if not issues else'FAIL_INDEPENDENT_LOCAL_ACCENT_SAMPLE',issues=issues)

    def check(self,after,target_ref,donor_refs,decision=None):
        if decision is not None and type(decision)is not dict:raise ValueError('Typed decision required')
        issues=[];target=self.rows.get(target_ref)
        if target is None:raise ValueError('Original target occurrence required')
        ev=self.options(target_ref);old={r['id']:r for r in self.before['facts']}
        # This also validates every source pointer, type, traversal and child slot.
        docs=project_documents(after);new={r['id']:r for r in after['facts']};accent_ref=target['note_ref']+'/accentuated';row=new.get(accent_ref)
        raw_note=docs[old[target['note_ref']]['document']]['measures'][target['bar']-1]['voices'][target['voice']]['beats'][target['beat']]['notes'][target['note']]
        notation={'kind':'absent'}if row is None else dict(kind='explicit',value=deepcopy(raw_note.get('accentuated')))
        changed=_encoded(notation)!=_encoded(target['state']);released=decision.get('released')if type(decision)is dict else changed
        if type(donor_refs)is not list or any(type(r)is not str for r in donor_refs)or donor_refs!=sorted(set(donor_refs)):issues.append('Canonical actual donor references required')
        if decision is not None:
            if type(decision.get('released'))is not bool or type(decision.get('changed'))is not bool or decision['changed']is not changed:issues.append('Actual decision flags differ')
            if changed and not released:issues.append('Unreleased source change')
            if 'evidence'in decision and decision['evidence']!=ev:issues.append('Recorded source-context evidence differs')
        if released:
            chosen=next((o for o in ev['options']if o['state']==notation),None)
            if ev['options']:
                if chosen is None or donor_refs!=chosen['donor_refs']:issues.append('No complete source-supported accent choice')
                if decision is not None and decision.get('chosen')!=chosen:issues.append('Chosen evidence differs')
            elif changed or donor_refs or decision is not None and(decision.get('chosen')is not None or decision.get('status')!='NO_ADMITTED_CHOICE'):issues.append('Invalid no-choice result')
        elif donor_refs or changed or decision is not None and decision.get('chosen')is not None:issues.append('Unreleased donor/change evidence')
        if self.before['documents']!=after['documents']or self.before['scope']!=after['scope']:issues.append('Source document/scope changed')
        if set(old)-{accent_ref}!=set(new)-{accent_ref}:issues.append('Unrelated source topology changed')
        before_note=old[target['note_ref']];expected=deepcopy(before_note)
        if accent_ref not in old and accent_ref in new:expected['children'].append(accent_ref)
        elif accent_ref in old and accent_ref not in new:expected['children'].remove(accent_ref)
        if new.get(target['note_ref'])!=expected:issues.append('Target note metadata/child order changed')
        for ref,r in old.items():
            if ref not in(accent_ref,target['note_ref'])and new.get(ref)!=r:issues.append('Locked source fact changed: '+ref)
        if row is not None and (target['sound_level']is not None or row!=old.get(accent_ref)):
            expected_scalar=dict(id=accent_ref,document=before_note['document'],pointer=before_note['pointer']+'/accentuated',parent=before_note['id'],slot='accentuated',type='integer',value=row.get('value'))
            if row!=expected_scalar or type(row.get('value'))is not int or row['value']not in(0,1,2):issues.append('Invalid typed accent scalar')
        return dict(status='PASS_INDEPENDENT_LOCAL_ACCENTS'if not issues else'FAIL_INDEPENDENT_LOCAL_ACCENTS',issues=issues,
            target_ref=target_ref,changed=changed,scope='Source notation and exact surrounding facts; no intent, artist or listening judgment')


def options(tier1,target_ref):return Oracle(tier1).options(target_ref)
def check(before,after,target_ref,donor_refs,decision=None):return Oracle(before).check(after,target_ref,donor_refs,decision)
