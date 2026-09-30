const encoder=new TextEncoder();
const crcTable=Uint32Array.from({length:256},(_,n)=>{for(let i=0;i<8;i++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
function crc32(bytes){let c=0xffffffff;for(const b of bytes)c=crcTable[(c^b)&255]^(c>>>8);return (c^0xffffffff)>>>0;}
export function floatWav(pcm,sampleRate){
  const bytes=new Uint8Array(44+pcm.byteLength),v=new DataView(bytes.buffer);
  const text=(at,s)=>{for(let i=0;i<s.length;i++)bytes[at+i]=s.charCodeAt(i);};
  text(0,'RIFF');v.setUint32(4,36+pcm.byteLength,true);text(8,'WAVE');text(12,'fmt ');
  v.setUint32(16,16,true);v.setUint16(20,3,true);v.setUint16(22,1,true);
  v.setUint32(24,sampleRate,true);v.setUint32(28,sampleRate*4,true);v.setUint16(32,4,true);v.setUint16(34,32,true);
  text(36,'data');v.setUint32(40,pcm.byteLength,true);
  for(let i=0;i<pcm.length;i++)v.setFloat32(44+i*4,pcm[i],true);
  return bytes;
}
// Standard ZIP, stored entries, CRC-32. Raw Float32 WAV samples are preserved.
export function trialZip(payload,trials){
  const files=[{name:'results.json',data:encoder.encode(JSON.stringify(payload))},
    ...trials.map(t=>({name:`audio/${t.id}.wav`,data:floatWav(t.pcm,t.report.sampleRate)}))];
  const parts=[],central=[];let offset=0,centralSize=0;
  for(const f of files){const name=encoder.encode(f.name),crc=crc32(f.data);
    const h=new Uint8Array(30+name.length),v=new DataView(h.buffer);
    v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);v.setUint16(12,0x21,true);
    v.setUint32(14,crc,true);v.setUint32(18,f.data.length,true);v.setUint32(22,f.data.length,true);
    v.setUint16(26,name.length,true);h.set(name,30);parts.push(h,f.data);
    const c=new Uint8Array(46+name.length),cv=new DataView(c.buffer);
    cv.setUint32(0,0x02014b50,true);cv.setUint16(4,20,true);cv.setUint16(6,20,true);cv.setUint16(8,0x800,true);cv.setUint16(14,0x21,true);
    cv.setUint32(16,crc,true);cv.setUint32(20,f.data.length,true);cv.setUint32(24,f.data.length,true);
    cv.setUint16(28,name.length,true);cv.setUint32(42,offset,true);c.set(name,46);
    central.push(c);centralSize+=c.length;offset+=h.length+f.data.length;
  }
  const end=new Uint8Array(22),ev=new DataView(end.buffer);ev.setUint32(0,0x06054b50,true);
  ev.setUint16(8,files.length,true);ev.setUint16(10,files.length,true);
  ev.setUint32(12,centralSize,true);ev.setUint32(16,offset,true);
  return new Blob([...parts,...central,end],{type:'application/zip'});
}
