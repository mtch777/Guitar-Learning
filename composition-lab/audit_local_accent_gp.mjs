// Reuse the unchanged actual-score/MIDI extractor; no dynamics acceptance adapter.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const args=process.argv.slice(2),root=path.dirname(fileURLToPath(import.meta.url));
if(args.length<3)throw Error('modulePath QA native-preview [fidelityScope] [capture] required');
const script=path.join(root,'audit_dynamic_gp.mjs'),result=spawnSync(process.execPath,[script,...args],{encoding:'utf8',windowsHide:true});
if(result.status!==0)throw Error(result.stderr||result.stdout||'Actual native snapshot failed');
const out=path.resolve(args[2]),original=path.join(out,'dynamic-native-snapshot.json');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const snapshot=JSON.parse(fs.readFileSync(original,'utf8'));
snapshot.schema='native-accent-snapshot/1';snapshot.shared_snapshot={file:'dynamic-native-snapshot.json',sha256:hash(original)};
snapshot.accent_adapter_sha256=hash(fileURLToPath(import.meta.url));
const target=path.join(out,'accent-native-snapshot.json');if(fs.existsSync(target))throw Error('Refusing snapshot overwrite');
fs.writeFileSync(target,JSON.stringify(snapshot,null,2));console.log(JSON.stringify({status:'SNAPSHOT_WRITTEN_NOT_ACCEPTANCE',target}));
