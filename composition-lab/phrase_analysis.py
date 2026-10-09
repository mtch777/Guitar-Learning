"""Independent GP7 edited-motif finder. Standard library only; no web/audio dependencies."""
import argparse, json, zipfile
from pathlib import Path
from collections import defaultdict
from xml.etree import ElementTree as ET

DURATION={'Whole':4,'Half':2,'Quarter':1,'Eighth':.5,'16th':.25,'32nd':.125,'64th':.0625,'128th':.03125}

def ids(x,tag):
    return (x.findtext(tag) or '').split()

def parse(path):
    with zipfile.ZipFile(path) as z:
        root=ET.fromstring(z.read('Content/score.gpif'))
    def idx(a,b):
        return {e.get('id'):e for e in root.findall('./%s/%s'%(a,b))}
    bars,voices,beats,notes,rhythms=[idx(a,b) for a,b in (
        ('Bars','Bar'),('Voices','Voice'),('Beats','Beat'),('Notes','Note'),('Rhythms','Rhythm'))]
    masters=root.findall('./MasterBars/MasterBar')
    sections=[{'measure':i+1,'label':b.findtext('./Section/Text')}
              for i,b in enumerate(masters) if b.findtext('./Section/Text')]
    tracks=[]
    for ti,track in enumerate(root.findall('./Tracks/Track')):
        measures=[]
        for mi,master in enumerate(masters):
            barids=ids(master,'Bars')
            if ti>=len(barids):raise ValueError('Missing bar at measure '+str(mi+1))
            events=[]
            for vi,vid in enumerate(ids(bars[barids[ti]],'Voices')):
                if vid=='-1':continue
                onset=0.0
                for bid in ids(voices[vid],'Beats'):
                    beat=beats[bid]; rr=beat.find('Rhythm')
                    rhythm=rhythms[rr.get('ref')] if rr is not None else None
                    value=rhythm.findtext('NoteValue') if rhythm is not None else None
                    if value not in DURATION:raise ValueError('Unsupported duration: '+str(value))
                    dur=DURATION[value]
                    dot=rhythm.find('AugmentationDot')
                    if dot is not None:dur*=2-.5**int(dot.get('count','1'))
                    tup=rhythm.find('PrimaryTuplet')
                    if tup is not None and tup.findtext('Num') and tup.findtext('Den'):
                        dur*=int(tup.findtext('Den'))/int(tup.findtext('Num'))
                    pitches=[]
                    for nid in ids(beat,'Notes'):
                        note=notes[nid]
                        midi=note.findtext("./Properties/Property[@name='Midi']/Number")
                        fret=note.findtext("./Properties/Property[@name='Fret']/Fret")
                        string=note.findtext("./Properties/Property[@name='String']/String")
                        if midi is not None and fret is not None and string is not None:
                            pitches.append(int(midi))
                    if pitches:events.append((vi,round(onset,5),round(dur,5),tuple(sorted(pitches))))
                    onset+=dur
            measures.append(events)
        tracks.append({'name':track.findtext('Name') or '', 'measures':measures})
    return {'file':Path(path).name,'sections':sections,'tracks':tracks}

def representative(bars,start,span):
    return [(offset,time,duration,ps[0])
            for offset,bar in enumerate(bars[start:start+span])
            for voice,time,duration,ps in bar if voice==0]

def distance(a,b):
    if not a or not b:return 1.0
    def normalized(seq):
        first=seq[0][3]
        return [(pitch-first,round(bar+onset,3),round(duration,3))
                for bar,onset,duration,pitch in seq]
    x,y=normalized(a),normalized(b)
    prev=list(range(len(y)+1))
    for i,(pitch,time,duration) in enumerate(x,1):
        row=[i]
        for j,(p,t,d) in enumerate(y,1):
            cost=(0 if pitch==p else .8)+(.15 if abs(time-t)>.125 else 0)+(.05 if abs(duration-d)>.125 else 0)
            row.append(min(prev[j]+1,row[j-1]+1,prev[j-1]+cost))
        prev=row
    return round(min(1.0,prev[-1]/max(len(x),len(y))),4)

def scan(path,threshold=.28,spans=(2,4),max_matches=12):
    song=parse(path); output=[]
    for track in song['tracks']:
        bars=track['measures']; matches=[]
        for span in spans:
            entries=[]
            for start in range(len(bars)-span+1):
                seq=representative(bars,start,span)
                if len(seq)>=5 and len({e[3] for e in seq})>=3:
                    entries.append((start,seq))
            for i,(a,left) in enumerate(entries):
                for b,right in entries[i+1:]:
                    if b<a+span:continue
                    if abs(len(left)-len(right))>max(2,round(.35*max(len(left),len(right)))):continue
                    d=distance(left,right)
                    if 0<d<=threshold:
                        matches.append({'bars':[a+1,b+1],'length_bars':span,
                                        'edit_distance':d,'notes':[len(left),len(right)],
                                        'first_pitch_shift':right[0][3]-left[0][3]})
        matches.sort(key=lambda x:(x['edit_distance'],-x['length_bars'],x['bars']))
        seen=set();selected=[]
        for m in matches:
            key=tuple(m['bars'])
            if key in seen:continue
            seen.add(key);selected.append(m)
            if len(selected)>=max_matches:break
        output.append({'track':track['name'],'candidate_variant_motifs':selected,
                       'silent_primary_voice_measures':[
                           i+1 for i,bar in enumerate(bars)
                           if not any(event[0]==0 for event in bar)][:30]})
    return {'file':song['file'],'sections_from_tab':song['sections'],'tracks':output,
            'method':{'window_lengths_bars':list(spans),'max_normalized_distance':threshold,
            'similarity':'edit distance over relative pitch, onset and duration',
            'limitations':['Window pairs are candidate motifs, not verified phrases',
                           'First voice and lowest pitch only; no chord voicing modeling',
                           'Heuristic costs; no held-out accuracy assessment',
                           'Section labels are source annotations, not automatically inferred']}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('files',nargs='+',type=Path)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    result=json.dumps([scan(p) for p in args.files],indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(result,encoding='utf-8')
        print('Wrote '+str(args.output))
    else:print(result)

if __name__=='__main__':main()
