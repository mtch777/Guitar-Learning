#!/usr/bin/env python3
"""Full official corpus of MIDI exports from MuseScore Studio's own test corpus.

The files are officially published by musescore/MuseScore. This tests the
MIDI->MusicXML->piano-lesson path, but NOT cloudflare-protected musescore.com
score-page access. All work is transient inside the CI checkout.
"""
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'https://raw.githubusercontent.com/musescore/MuseScore/main/src/importexport/midi/tests/midiexport_data/'
FILES = [
    'midi01-ref.mid', 'midi02-ref.mid', 'midi03-ref.mid',
    'testArpeggio-ref.mid', 'testBends1-ref.mid', 'testBends2-ref.mid',
    'testInitialKeySigThenRepeatToMeas2-ref.mid', 'testMeasureRepeats-ref.mid',
    'testMidiPort-ref.mid', 'testMutedUnison-ref.mid',
    'testRepeatsWithKeySigs-ref.mid', 'testRepeatsWithKeySigsExceptFirstMeas-ref.mid',
    'testSingleNoteDynamics-ref.mid', 'testTimeStretchFermata-ref.mid',
    'testTimeStretchFermataTempoEdit-120-ref.mid', 'testTimeStretchFermataTempoEdit-200-ref.mid',
    'testVoltaDynamic-ref.mid', 'testVoltaStaffText-ref.mid', 'testVoltaTemp-ref.mid',
]
SEED=20261119


def main():
    from importlib import util
    p = ROOT / 'scripts/piano/import-midi-url.py'
    spec=util.spec_from_file_location('piano_import', p)
    module=util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sources=list(FILES)
    random.Random(SEED).shuffle(sources)
    root=ROOT / 'public/piano/learning-songs'
    consecutive=0
    longest=0
    passed=0
    rejected=0
    failed=0
    results=[]
    for count,name in enumerate(sources,1):
        link=SOURCE+name
        print(f'QA OFFICIAL ATTEMPT {count} | {name} | {link}', flush=True)
        result={'test':count,'name':name,'url':link}
        try:
            xml=module.import_midi(link, root, name[:-8])
            build=subprocess.run(['npm','run','prebuild'],cwd=ROOT,capture_output=True,text=True,timeout=80)
            if build.returncode:
                raise RuntimeError('Catalog build failed: '+build.stderr[-350:])
            check=subprocess.run(['node','scripts/piano/assert-midi-import.mjs',xml.name],
                                 cwd=ROOT,capture_output=True,text=True,timeout=80)
            if check.returncode:
                raise RuntimeError('Lesson reject/fidelity validation: '+check.stderr[-450:])
            catalog=json.loads((root/'song-library.json').read_text())
            song=next(s for s in catalog['songs'] if s.get('sourceFilename')==xml.name)
            result.update(outcome='PASS',attacks=song['attackCount'],score_notes=song['noteCount'])
            consecutive+=1
            passed+=1
            longest=max(longest,consecutive)
        except ValueError as error:
            if 'no completed pitched notes' in str(error):
                result.update(outcome='EXPECTED_REJECTION',reason=str(error))
                rejected+=1
            else:
                result.update(outcome='FAIL',reason=str(error)[:400])
                failed+=1
            consecutive=0
        except Exception as error:
            result.update(outcome='FAIL',reason=str(error)[:400])
            failed+=1
            consecutive=0
        results.append(result)
        print(f'QA OFFICIAL RESULT {count} {result["outcome"]}: {result.get("reason",str(result.get("attacks"))+" attacks")} | consecutive={consecutive}',flush=True)
    output={'source_repository':'musescore/MuseScore', 'random_seed':SEED, 'target':4,
            'longest_streak':longest, 'passed':passed, 'expected_rejections':rejected,
            'unexpected_failures':failed, 'attempts':results}
    (ROOT/'musescore-official-midi-qa-results.json').write_text(json.dumps(output,indent=2))
    print(f'QA OFFICIAL FINAL longest={longest}/4 consecutive; passed={passed}; expected_rejections={rejected}; unexpected_failures={failed}; total={len(results)}',flush=True)
    return 0 if longest>=4 and failed==0 else 1


if __name__=='__main__':
    sys.exit(main())
