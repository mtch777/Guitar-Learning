#!/usr/bin/env python3
"""Score exported live trial ZIPs. One pluck/trial is a unit; frames are diagnostics."""
import argparse,json,math,statistics,struct,zipfile
from pathlib import Path

def percentile(values,p):
    v=sorted(x for x in values if isinstance(x,(int,float)) and math.isfinite(x))
    return v[int((len(v)-1)*p)] if v else None

def wilson(k,n):
    if not n:return None
    z=1.96;center=(k/n+z*z/(2*n))/(1+z*z/n)
    half=z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/(1+z*z/n)
    return [max(0,center-half),min(1,center+half)]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('archives',nargs='+',type=Path)
    ap.add_argument('--out',required=True,type=Path);args=ap.parse_args()
    seen=set();rows=[];manifests={}
    for archive in args.archives:
        with zipfile.ZipFile(archive) as z:
            if z.testzip():raise ValueError('ZIP CRC failure')
            source=json.loads(z.read('results.json'))
            if source['schema']!='live-pipeline-v1':raise ValueError('Unexpected schema')
            fingerprint=json.dumps(source['modelManifest']['sha256'],sort_keys=True)
            manifests[fingerprint]=source['modelManifest']
            for t in source['trials']:
                key=(source['sessionId'],t['id'])
                if key in seen:continue
                seen.add(key)
                audio=z.read(t['audioFile'])
                if audio[:4]!=b'RIFF' or audio[8:12]!=b'WAVE':raise ValueError('Missing WAV header')
                if struct.unpack_from('<H',audio,20)[0]!=3:raise ValueError('Expected Float32 WAV')
                if struct.unpack_from('<I',audio,24)[0]!=t['report']['sampleRate']:raise ValueError('Sample-rate mismatch')
                if len(audio)!=44+t['blocks']*4096*4:raise ValueError('Audio sample count mismatch')
                frames=t['report']['frames'];expected=t['target']['positions']
                gap=sum(f['missingCallbacks'] for f in frames)
                invalid=t['aborted'] or bool(t.get('error')) or gap>0
                route_rows={}
                for name in ['hybrid','correlation']:
                    r=t['report']['routes'][name];events=r['events']
                    match=lambda e,p:e['midi']==p['midi'] and e['string']==p['string']
                    first=bool(expected and events and match(events[0],expected[0]))
                    exact=len(events)==len(expected) and all(match(e,p) for e,p in zip(events,expected))
                    delivery=[e['receivedWallMs'] for e in t['renderedEvents'] if e['route']==name]
                    latency=[delivery[i]-e['captureStartReceivedWallMs']+4096/t['report']['sampleRate']*1000
                             for i,e in enumerate(events) if i<len(delivery) and e['captureStartReceivedWallMs'] is not None]
                    route_rows[name]={'events':events,'first_position_correct':first,'exact_sequence_correct':exact,
                        'miss':bool(expected and not events),'extra_events':max(0,len(events)-len(expected)),
                        'incomplete_capture':r['incompleteCapture'],'error_events':sum(bool(e['error']) for e in events),
                        'trigger_to_delivered_ms':latency}
                rows.append({'session_id':source['sessionId'],'id':t['id'],'target':t['target'],'invalid':invalid,
                    'model_fingerprint':fingerprint,'missing_callbacks':gap,'clipping_frames':sum(f['peak']>=.99 for f in frames),
                    'worker_queue_p95_ms':percentile([f['workerStartWallMs']-f['receivedWallMs'] for f in frames],.95),
                    'routes':route_rows})
    valid=[r for r in rows if not r['invalid']]
    singles=[r for r in valid if r['target']['kind']=='single'];silent=[r for r in valid if r['target']['kind']=='silence']
    report={'trials':len(rows),'valid_trials':len(valid),'invalid_trials':len(rows)-len(valid),
        'single_plucks':len(singles),'silence_trials':len(silent),'model_bundles':len(manifests),
        'note':'Target-label match only; actual lesson acceptance is not tested. Overlap is a monophonic stress test. Paired inference adds CPU load. Timing starts at threshold-trigger frame, not externally measured pluck onset.',
        'routes':{}}
    for name in ['hybrid','correlation']:
        correct=sum(r['routes'][name]['first_position_correct'] for r in singles)
        report['routes'][name]={'single_first_correct':correct,'single_first_accuracy':correct/len(singles) if singles else None,
            'single_wilson95':wilson(correct,len(singles)),
            'single_misses':sum(r['routes'][name]['miss'] for r in singles),
            'single_extra_events':sum(r['routes'][name]['extra_events'] for r in singles),
            'silent_false_events':sum(len(r['routes'][name]['events']) for r in silent),
            'incomplete_captures':sum(r['routes'][name]['incomplete_capture'] for r in valid),
            'error_events':sum(r['routes'][name]['error_events'] for r in valid),
            'trigger_to_delivered_median_ms':percentile([v for r in singles for v in r['routes'][name]['trigger_to_delivered_ms']],.5),
            'trigger_to_delivered_p95_ms':percentile([v for r in singles for v in r['routes'][name]['trigger_to_delivered_ms']],.95),
            'stress':{kind:{'trials':sum(r['target']['kind']==kind for r in valid),
                'exact_sequences':sum(r['target']['kind']==kind and r['routes'][name]['exact_sequence_correct'] for r in valid)}
                for kind in ['repeated','transition']}}
    report['hybrid_rescues']=sum(r['routes']['hybrid']['first_position_correct'] and not r['routes']['correlation']['first_position_correct'] for r in singles)
    report['hybrid_regressions']=sum(r['routes']['correlation']['first_position_correct'] and not r['routes']['hybrid']['first_position_correct'] for r in singles)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps({'report':report,'rows':rows,'manifests':list(manifests.values())},indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
