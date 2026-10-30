"""Actual original/zero GP and performed-clock audit; no changed-case claim."""
from pathlib import Path
import hashlib,json,re,sys,zipfile
import xml.etree.ElementTree as ET
from source_fact_tier1 import extract
from check_step_tempo_artifacts import canonical_model,tempo_inventory,verify_clock,verify_source_geometry
from check_dynamic_artifacts import read,sha
from check_voicing_artifacts import canonical_ids,differences


def source_binding(qa,plan):
    hashes=plan['source_hashes']
    if not hashes:raise ValueError('Complete original source hashes required')
    capture=Path(next(iter(hashes))).parent
    if {Path(p).name for p in hashes}!={p.name for p in capture.glob('*.json')} or any(Path(p).parent!=capture or sha(p)!=h for p,h in hashes.items()):raise ValueError('Original source hash/inventory differs')
    original=extract(capture);zero=extract(qa/'zero-capture');worker=read(qa/'zero-isolated/worker/output.json')
    if original!=zero or zero!=worker:raise ValueError('Actual zero worker differs from original capture')
    no_choice=qa/'no-choice-isolated/worker/output.json'
    if no_choice.exists() and read(no_choice)!=original:raise ValueError('Actual no-choice worker differs from original capture')
    return capture,original


def check(root,qa,*,report_path=None):
    root,qa=Path(root),Path(qa);issues=[];detail={}
    try:
        capture,facts=source_binding(qa,read(qa/'plan.json'));s=read(root/'native-zero-snapshot.json');module=Path(s['module_path'])
        if s['schema']!='native-step-tempo-zero/1' or set(s['cases'])!={'source','zero'}:raise ValueError('Exactly original and zero native cases required')
        if s['adapter_sha256']!=sha(Path(__file__).with_name('build_step_tempo_zero.mjs')) or s['module_sha256']!=sha(module) or s['core_sha256']!=sha(module.with_name('alphaTab.core.mjs')) or s['extractor_sha256']!=sha(Path(__file__).parent/'songsterr_automation/songsterr_api/export_csv_gp7.mjs'):raise ValueError('Native zero dependency binding differs')
        if len(re.findall(r'static QuarterTime = 960;',module.with_name('alphaTab.core.mjs').read_text(encoding='utf-8')))!=1:raise ValueError('Quarter tick scope changed')
        _,marks,frames=tempo_inventory(facts);trees={};assets={};inventories={};companions={};ledgers={};scope=[]
        for name,c in s['cases'].items():
            folder=root/name;v=read(folder/'gp7-validation.json')
            if sha(folder/'score.gp')!=c['gp_sha256'] or v.get('error') or v['directSource']['differences']!=0 or v['directPitchedGraces']['status']not in('PASS_INDEPENDENT_PITCHED_SOURCE_GRACES','NO_COVERED_PITCHED_GRACE_VOICES'):raise ValueError('Native source/grace fidelity check failed')
            actual=extract(folder)
            if actual!=facts:raise ValueError('Export input capture differs from actual original/zero')
            refpath=folder/'roundtrip-before.json';reference=read(refpath)if refpath.exists()else None
            if reference!=c['pre_export_model']:raise ValueError('Native pre-export reference binding differs')
            paired=reference is not None and reference==c['checked_model']
            if not v['roundtripPass'] and not paired:raise ValueError('Neither standalone nor exact-companion checked fields pass')
            scope.append(dict(method=name,standalone_checked_roundtrip=bool(v['roundtripPass']),paired_checked_fields=paired))
            profile=folder/'score.playback.json'
            if c['playback_profile']!=(read(profile)if profile.exists()else{}):raise ValueError('Native playback settings changed')
            side=folder/'score.exact-model-bends.json';companions[name]=None
            if (sha(side)if side.exists()else None)!=c['sidecar_sha256']:raise ValueError('Bend companion hash differs')
            if side.exists():
                d=read(side)
                if d['gp_sha256']!=c['gp_sha256']:raise ValueError('Bend companion GP binding differs')
                companions[name]={k:v for k,v in d.items()if k!='gp_sha256'}
            with zipfile.ZipFile(folder/'score.gp')as z:
                names=z.namelist();gpif=[n for n in names if n.endswith('.gpif')]
                if len(names)!=len(set(names)) or len(gpif)!=1:raise ValueError('Complete unique GP archive required')
                inventories[name]=set(names);trees[name]=ET.fromstring(z.read(gpif[0]));canonical_ids(trees[name]);assets[name]={n:z.read(n)for n in names if n!=gpif[0]}
            if hashlib.sha256(c['raw_midi_json'].encode()).hexdigest()!=c['midi_sha256'] or json.loads(c['raw_midi_json'])!=[e['data']for e in c['events']]:raise ValueError('Actual full MIDI binding differs')
            if c['midi_tick_shift']!=0:raise ValueError('Leading grace clock shift not covered by this tempo ledger')
            verify_source_geometry(c['model'],c['performed_bars'],frames,960)
            ledgers[name]=verify_clock(c,dict(performed_bars=c['performed_bars'],note_calls=[],callbacks=[]),marks,960)
        a,b=s['cases']['source'],s['cases']['zero']
        if canonical_model(a['model'])!=canonical_model(b['model']) or any(a[k]!=b[k]for k in('events','performed_bars','playback_profile')) or ledgers['source']!=ledgers['zero']:raise ValueError('Original/zero native model, MIDI or performed clock differs')
        if any(c['source']!=c['zero']for c in(inventories,assets,companions)) or differences(trees['source'],trees['zero']):raise ValueError('Original/zero GP archive, XML or companion differs')
        detail=dict(source_facts_exact=len(facts['facts']),artifact_fidelity=scope,complete_gp_and_midi_equal=True,performed_clock_equal=True,
            events_per_case=len(a['events']),performed_bars=len(ledgers['source']['bars']),total_seconds=ledgers['source']['total_seconds'],source_tempo_marks=len(marks),source_native_quarter_geometry_equal=True,audio_rendered=False)
    except Exception as exc:issues.append(str(exc))
    report=dict(status='FAIL'if issues else'PASS_NATIVE_SOURCE_ZERO_WITH_STEP_CLOCK',issues=issues,**detail,changed_case_tested=False,listening_judgment=None)
    (Path(report_path)if report_path is not None else root/'native-zero-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    r=check(*sys.argv[1:3]);print(json.dumps(r,indent=2));raise SystemExit(r['status']=='FAIL')
