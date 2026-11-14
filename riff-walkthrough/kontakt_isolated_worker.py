"""Isolated Kontakt renderer. No UI, playback, generator changes or source MIDI edits."""
import argparse, hashlib, json, math, os, pathlib, sys, time, uuid, wave
ROOT=pathlib.Path(__file__).resolve().parent
PRESETS={"modern-metal-1":("Hydra 3.5 Modern Metal 1","verify-console-live.state"),"ready-to-djent":("Hydra 3.5 Ready to Djent!","verify-console-djent.state")}
def sha(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()
def preset_catalog():
 manifest=os.environ.get('RIFF_KONTAKT_MANIFEST')
 if not manifest:return PRESETS.copy()
 items=json.loads(pathlib.Path(manifest).read_text(encoding='utf-8-sig')).get('presets',[])
 result={}
 for item in items:
  if not isinstance(item,dict) or item.get('verified') is not True:continue
  key=item.get('id');label=item.get('label');filename=item.get('state_file')
  import re
  if not isinstance(key,str) or not re.fullmatch('[a-z0-9][a-z0-9-]*',key) or key in result or not isinstance(label,str) or not isinstance(filename,str):continue
  state=(ROOT/filename).resolve()
  if state.parent!=ROOT.resolve() or not state.is_file():continue
  if item.get('state_sha256') and sha(state)!=item['state_sha256']:continue
  result[key]=(label,filename)
 return result

def main():
 presets=preset_catalog()
 ap=argparse.ArgumentParser()
 ap.add_argument("--midi",required=True);ap.add_argument("--output",required=True)
 ap.add_argument("--preset",required=True,choices=presets)
 ap.add_argument("--bpm",required=True,type=float);ap.add_argument("--duration",required=True,type=float)
 ap.add_argument("--job-id",required=True)
 args=ap.parse_args()
 if not math.isfinite(args.bpm) or args.bpm<=0 or not math.isfinite(args.duration) or args.duration<=0: raise ValueError("bpm/duration must be finite and positive")
 source=pathlib.Path(args.midi).resolve(strict=True);out=pathlib.Path(args.output).resolve()
 meta=pathlib.Path(str(out)+".json")
 if source==out: raise ValueError("output cannot overwrite input")
 if out.exists() or meta.exists(): raise FileExistsError("Use fresh output path; refusing existing result")
 if not out.parent.is_dir(): raise ValueError("Output directory must already exist")
 payload=source.read_bytes()
 if not payload.startswith(b"MThd"): raise ValueError("Input is not a standard MIDI file")
 name,state_name=presets[args.preset];state=ROOT/state_name
 source_hash=hashlib.sha256(payload).hexdigest();state_hash=sha(state)
 job=args.job_id or uuid.uuid4().hex
 # Cross-process lock shared across all renders; OS releases it on process exit.
 import msvcrt
 lock=open(ROOT/"kontakt-render.lock","a+b");lock.seek(0);lock.write(b"0");lock.flush();lock.seek(0)
 try: msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 except OSError: raise RuntimeError("Kontakt renderer busy; serialize and retry")
 import dawdreamer as d,numpy as np
 started=time.perf_counter()
 engine=d.RenderEngine(44100,512)
 plugin=engine.make_plugin_processor("kontakt",r"C:\Program Files\Common Files\VST3\Kontakt 8.vst3")
 plugin.load_state(str(state))
 engine.load_graph([(plugin,[])])
 engine.render(0.25)
 if not plugin.load_midi(str(source), beats=False, all_events=True): raise ValueError("MIDI load failed")
 engine.set_bpm(args.bpm)
 t=time.perf_counter();engine.render(args.duration);audio=engine.get_audio();render_seconds=time.perf_counter()-t
 if audio.ndim!=2 or audio.shape[0]<2 or audio.shape[1]==0: raise ValueError("Invalid audio shape")
 if not np.isfinite(audio).all(): raise ValueError("Nonfinite output")
 stereo=audio[:2]
 peak=float(np.max(np.abs(stereo)));rms=float(np.sqrt(np.mean(stereo.astype(np.float64)**2)))
 if peak<1e-7: raise ValueError("Silent output: no playable MIDI notes or instrument unavailable")
 if peak>1: raise ValueError("Output exceeds PCM range; refusing clipped render")
 if audio.shape[0]>2 and np.max(np.abs(audio[2:]))>1e-7: raise ValueError("Unexpected additional active audio channels")
 if sha(source)!=source_hash or sha(state)!=state_hash: raise ValueError("Input/state changed during render")
 pcm=(stereo.T*32767).astype("<i2").tobytes()
 temp=out.with_name(out.name+"."+uuid.uuid4().hex+".tmp")
 with wave.open(str(temp),"wb") as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100);w.writeframes(pcm)
 with wave.open(str(temp),"rb") as w:
  if w.getnchannels()!=2 or w.getsampwidth()!=2 or w.getnframes()!=stereo.shape[1]: raise ValueError("WAV verification failed")
 result={"termination_mode":"controlled_process_termination","expected_exit_code":85,"success":True,"job_id":job,"preset":args.preset,"preset_name":name,"state_sha256":state_hash,"midi_sha256":source_hash,"output":str(out),"wav_sha256":sha(temp),"peak":peak,"rms":rms,"sample_rate":44100,"channels":2,"frames":int(stereo.shape[1]),"duration":stereo.shape[1]/44100,"requested_duration":args.duration,"bpm":args.bpm,"timing_source":"midi_tempo_map","render_seconds":render_seconds,"total_seconds":time.perf_counter()-started}
 # rename (not replace) refuses existing destination on Windows.
 temp.rename(out)
 metatemp=meta.with_name(meta.name+"."+uuid.uuid4().hex+".tmp")
 metatemp.write_text(json.dumps(result,sort_keys=True),encoding="utf-8")
 metatemp.rename(meta)
 print("KONTAKT_RENDER_COMPLETE "+json.dumps(result,sort_keys=True),flush=True)
 lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()
 # Avoid plugin destructor hangs; parent still verifies exit + fresh completion manifest.
 import ctypes
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.GetCurrentProcess.restype=ctypes.c_void_p
 k.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint]
 k.TerminateProcess.restype=ctypes.c_int
 print('CONTROLLED_PROCESS_TERMINATION code=85',flush=True)
 if not k.TerminateProcess(k.GetCurrentProcess(),85): raise ctypes.WinError(ctypes.get_last_error())
if __name__=="__main__":
 try: main()
 except Exception as exc:
  print("KONTAKT_RENDER_ERROR "+json.dumps({"success":False,"error":str(exc),"error_type":type(exc).__name__}),flush=True)
  os._exit(2)









