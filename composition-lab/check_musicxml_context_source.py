"""Independent XML arithmetic oracle; no music21 or tier implementation imports."""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET


def raw_notes(path):
    path=Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            container=ET.fromstring(archive.read('META-INF/container.xml'))
            rootfile=next(x.attrib['full-path'] for x in container.iter() if x.tag.endswith('rootfile'))
            root=ET.fromstring(archive.read(rootfile))
    else:root=ET.parse(path).getroot()
    if '}' in root.tag:raise ValueError('Namespaced XML not supported by this independent oracle')
    result=[];geometry=[]
    for part_id,part in enumerate(root.findall('part')):
        divisions=None;start=F(0);frames=[]
        for bar,measure in enumerate(part.findall('measure'),1):
            cursor=F(0);extent=F(0);last_start=None
            for child in measure:
                if child.tag=='attributes':
                    value=child.findtext('divisions')
                    if value is not None:divisions=int(value)
                    if child.find('transpose') is not None:raise ValueError('Transposing XML outside independent written-pitch scope')
                if child.tag in ('backup','forward'):
                    if divisions is None:raise ValueError('Missing divisions')
                    cursor+=F(int(child.findtext('duration')),divisions)*(1 if child.tag=='forward' else -1)
                if child.tag!='note':continue
                grace=child.find('grace') is not None
                if not grace and divisions is None:raise ValueError('Missing divisions')
                duration=F(0) if grace else F(int(child.findtext('duration')),divisions)
                onset=last_start if child.find('chord') is not None else cursor
                if onset is None:raise ValueError('Chord without preceding onset')
                pitch=child.find('pitch')
                if pitch is not None:
                    step={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[pitch.findtext('step')]
                    value=12*(int(pitch.findtext('octave'))+1)+step+F(pitch.findtext('alter','0'))
                    result.append((part_id,bar,str(value),str(start+onset),str(duration)))
                elif child.find('rest') is None:raise ValueError('Unpitched XML outside reference scope')
                extent=max(extent,onset+duration)
                if child.find('chord') is None:last_start=onset;cursor+=duration
            frames.append((measure.attrib['number'],str(start),str(extent)))
            start+=extent
        geometry.append(frames)
    return result,geometry


def meter_inventory(path):
    """Independent literal XML meter ownership and source part inventory."""
    path=Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            c=ET.fromstring(archive.read('META-INF/container.xml'))
            name=next(x.attrib['full-path'] for x in c.iter() if x.tag.endswith('rootfile'))
            root=ET.fromstring(archive.read(name))
    else:root=ET.parse(path).getroot()
    inventories=[]
    for part_id,part in enumerate(root.findall('part')):
        rows=[];signature=None;witness=0
        for ordinal,measure in enumerate(part.findall('measure'),1):
            times=measure.findall('attributes/time')
            if len(times)>1:raise ValueError('Multiple XML time declarations require explicit handling')
            if times:
                time=times[0]
                if len(time.findall('beats'))!=1 or len(time.findall('beat-type'))!=1:raise ValueError('Composite meter outside adapter scope')
                signature=[int(time.findtext('beats')),int(time.findtext('beat-type'))];witness=ordinal
            if signature is None:raise ValueError('No explicit source meter')
            rows.append(dict(signature=signature,meter_source='explicit' if times else 'inherited',meter_source_frame=witness))
        inventories.append(dict(part_id=part_id,frames=rows))
    return inventories


def check(path,lower):
    raw,frames=raw_notes(path)
    given=[(r['part_id'],r['bar'],r['pitch'],r['onset_q'],r['duration_q']) for r in lower['events']]
    issues=[]
    if Counter(raw)!=Counter(given):issues.append('Independent XML note occurrence multiset differs')
    canonical=[(r['label'],r['start_q'],r['span_q']) for r in lower['measure_geometry']['frames']]
    if any(f!=canonical for f in frames):issues.append('Independent XML measure labels/start/extent differ')
    inventory=meter_inventory(path)
    for part in inventory:
        actual=[{k:r[k] for k in ('signature','meter_source','meter_source_frame')} for r in lower['measure_geometry']['frames']]
        if part['frames']!=actual:issues.append('Independent XML meter declaration/inheritance differs')
    members=[dict(part_id=p['part_id'],frame_refs=[f'measure:{i+1}' for i in range(len(p['frames']))],source_pickup_declared=None) for p in inventory]
    if lower['measure_geometry']['parts']!=members:issues.append('Independent XML source part/frame inventory differs')
    return dict(status='FAIL' if issues else 'PASS',issues=issues,raw_notes=len(raw),raw_parts=len(frames),scope='Written pitch/time multiplicity and source measure extent; not full XML serialization')
